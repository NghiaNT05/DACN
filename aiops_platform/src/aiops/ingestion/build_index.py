import os
import shutil
import json
import re
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from aiops.config import get_settings
from aiops.observers import collect_workload_signals


os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


def _load_docs(source_paths):
    allowed_ext = (".yml", ".yaml", ".json", ".jsonl", ".md", ".txt", ".tf", ".dockerfile", "Dockerfile")
    docs = []

    for source_path in source_paths:
        source_path = Path(source_path)
        if not source_path.exists():
            continue
        for file_path in source_path.rglob("*"):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if not (suffix in allowed_ext or file_path.name == "Dockerfile"):
                continue
            if file_path.name == "incident_report.schema.json":
                # Schema docs often pollute retrieval with format instructions, not RCA evidence.
                continue
            try:
                loaded = TextLoader(str(file_path), autodetect_encoding=True).load()
                for doc in loaded:
                    doc.metadata["source_type"] = source_path.name
                docs.extend(loaded)
            except Exception:
                continue
    return docs


def _load_known_services(settings):
    try:
        with settings.default_cmdb.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return [str(s.get("name")) for s in payload.get("services", []) if s.get("name")]
    except Exception:
        return []


def _extract_service_hint(text, known_services):
    lowered = text.lower()

    for pattern in (
        r'"app"\s*:\s*"([a-z0-9\-]+)"',
        r"\\\"app\\\"\\s*:\\s*\\\"([a-z0-9\-]+)\\\"",
        r'"service"\s*:\s*"([a-z0-9\-]+)"',
        r"\\\"service\\\"\\s*:\\s*\\\"([a-z0-9\-]+)\\\"",
        r'"destination_service_name"\s*:\s*"([a-z0-9\-]+)"',
    ):
        m = re.search(pattern, lowered)
        if m:
            return m.group(1)

    for svc in known_services:
        svc_low = svc.lower()
        if svc_low in lowered or re.search(rf"\b{re.escape(svc_low)}(?:-[a-z0-9-]+)?\b", lowered):
            return svc

    return ""


def _enrich_chunk_metadata(chunks, known_services):
    for chunk in chunks:
        metadata = chunk.metadata or {}
        source = str(metadata.get("source", ""))
        text = chunk.page_content[:4000]

        service_hint = _extract_service_hint(text, known_services)
        if service_hint:
            metadata["service"] = service_hint
            metadata.setdefault("app", service_hint)

        if source.endswith("services.json"):
            metadata["source_type"] = "cmdb"
        elif source.endswith(".jsonl") and metadata.get("source_type") == "telemetry":
            metadata["source_type"] = "telemetry"

        chunk.metadata = metadata

    return chunks


def _build_cmdb_derived_docs(settings):
    docs = []
    try:
        with settings.default_cmdb.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return docs

    services = payload.get("services", [])
    for svc in services:
        name = str(svc.get("name", "")).strip()
        if not name:
            continue
        deps = svc.get("dependencies", [])
        thresholds = svc.get("thresholds", {})
        text = (
            f"service={name}\n"
            f"type={svc.get('type', 'unknown')}\n"
            f"dependencies={deps}\n"
            f"thresholds={thresholds}\n"
            "task=use this for dependency impact and RCA candidate ranking"
        )
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(settings.default_cmdb),
                    "source_type": "cmdb",
                    "service": name,
                    "app": name,
                    "doc_kind": "cmdb-derived",
                },
            )
        )
    return docs


def _build_runtime_docs(namespace="default"):
    docs = []
    runtime = collect_workload_signals(namespace=namespace)

    summary_text = (
        f"namespace={runtime.get('namespace')}\n"
        f"scaled_to_zero={runtime.get('scaled_to_zero', [])}\n"
        f"unhealthy_deployments={runtime.get('unhealthy_deployments', [])}\n"
        f"crashloop_pods={runtime.get('crashloop_pods', [])}\n"
        "task=use this for runtime health RCA evidence"
    )
    docs.append(
        Document(
            page_content=summary_text,
            metadata={
                "source": f"runtime://{namespace}/summary",
                "source_type": "runtime",
                "doc_kind": "runtime-summary",
            },
        )
    )

    for dep in runtime.get("deployments", []):
        name = str(dep.get("name", "")).strip()
        if not name:
            continue
        text = (
            f"service={name}\n"
            f"desired={dep.get('desired', 0)}\n"
            f"ready={dep.get('ready', 0)}\n"
            f"available={dep.get('available', 0)}\n"
            f"unavailable={dep.get('unavailable', 0)}\n"
            "task=use this to detect unhealthy deployment for RCA"
        )
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": f"runtime://{namespace}/deployment/{name}",
                    "source_type": "runtime",
                    "service": name,
                    "app": name,
                    "doc_kind": "runtime-deployment",
                },
            )
        )

    return docs


def build_index(include_docs=True, include_cmdb=True, include_telemetry=True, include_runtime=True, reset_db=True):
    settings = get_settings()
    known_services = _load_known_services(settings)
    sources = []
    if include_docs:
        sources.append(settings.docs_dir)
    if include_cmdb:
        sources.append(settings.cmdb_dir)
    if include_telemetry:
        sources.append(settings.telemetry_dir)

    docs = _load_docs(sources)
    if include_cmdb:
        docs.extend(_build_cmdb_derived_docs(settings))
    if include_runtime:
        docs.extend(_build_runtime_docs(namespace="default"))

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    chunks = _enrich_chunk_metadata(chunks, known_services)

    if reset_db and settings.vector_db_dir.exists():
        shutil.rmtree(settings.vector_db_dir)

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
    )

    Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=str(settings.vector_db_dir),
    )

    source_labels = [str(p) for p in sources]
    if include_runtime:
        source_labels.append("runtime://default")

    return {"documents": len(docs), "chunks": len(chunks), "sources": source_labels}
