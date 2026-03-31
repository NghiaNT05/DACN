import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aiops.config import get_settings

try:
    from jsonschema import validate as jsonschema_validate
except ImportError:  # pragma: no cover
    jsonschema_validate = None


def _to_strength(score):
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0.0
    if value >= 0.85:
        return "high"
    if value >= 0.6:
        return "medium"
    return "low"


def _present_candidate_roots(candidates, preferred_root=None, allow_unknown=False):
    if not isinstance(candidates, list):
        return []

    normalized = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        service = str(item.get("service", "unknown")).strip() or "unknown"
        if service == "unknown" and not allow_unknown:
            continue
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
        evidence = [str(x).strip() for x in evidence if str(x).strip()][:3]
        normalized.append(
            {
                "service": service,
                "_score": item.get("score", 0.0),
                "evidence": evidence,
            }
        )

    normalized.sort(key=lambda x: float(x.get("_score", 0.0)), reverse=True)
    if preferred_root:
        for idx, item in enumerate(normalized):
            if item.get("service") == preferred_root:
                if idx != 0:
                    normalized.insert(0, normalized.pop(idx))
                break

    out = []
    for idx, item in enumerate(normalized[:3], start=1):
        out.append(
            {
                "service": item["service"],
                "rank": idx,
                "evidence_strength": _to_strength(item.get("_score", 0.0)),
                "evidence": item["evidence"],
            }
        )
    return out


def build_incident_report(incident_question, analysis, rca_text, snapshot_path, cmdb_path):
    settings = get_settings()
    root_cause = analysis.get("root_cause", "unknown")
    report_candidates = _present_candidate_roots(analysis.get("candidate_roots", []), preferred_root=root_cause)
    graph_summary = analysis.get("graph_summary", {})
    graph_summary_for_report = dict(graph_summary) if isinstance(graph_summary, dict) else {}
    graph_summary_for_report["candidate_roots"] = _present_candidate_roots(
        graph_summary_for_report.get("candidate_roots", []),
        preferred_root=root_cause,
    )

    report = {
        "report_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "incident_question": incident_question,
        "rca_source": analysis.get("rca_source", "graph-rag-llm"),
        "rca_result": {
            "status": analysis.get("status", "unknown"),
            "root_cause": analysis.get("root_cause", "unknown"),
            "confidence": analysis.get("confidence", 0.0),
            "candidate_roots": report_candidates,
            "reasoning": analysis.get("reasoning", ""),
            "impacted_services": analysis.get("impacted_services", []),
            "evidence": analysis.get("evidence", []),
            "anomalies": analysis.get("anomalies", []),
            "suggested_actions": analysis.get("suggested_actions", []),
        },
        "llm_raw_output": analysis.get("validated_llm_output", rca_text),
        "audit": {
            "run_id": str(uuid.uuid4()),
            "model": settings.ollama_model,
            "embedding_model": settings.embedding_model,
            "prompt_version": analysis.get("prompt_version", "rca-graph-rag-v1"),
            "context_counts": analysis.get("context_counts", {}),
            "rag_quality": analysis.get("rag_quality", {}),
            "graph_summary": graph_summary_for_report,
            "retrieval_summary": analysis.get("retrieval_summary", {}),
        },
        "artifacts": {
            "snapshot_path": str(snapshot_path),
            "cmdb_path": str(cmdb_path),
        },
    }

    if "datasource_health" in analysis:
        report["datasource_health"] = analysis["datasource_health"]

    return report


def _validate_report_schema(report):
    if jsonschema_validate is None:
        raise RuntimeError("jsonschema package is required to validate incident report schema.")

    settings = get_settings()
    schema_path = settings.cmdb_dir / "incident_report.schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    jsonschema_validate(instance=report, schema=schema)


def save_report_json(report, output_path):
    _validate_report_schema(report)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=True, indent=2)
