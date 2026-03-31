import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    docs_dir: Path
    cmdb_dir: Path
    telemetry_dir: Path
    vector_db_dir: Path
    reports_dir: Path
    default_snapshot: Path
    default_cmdb: Path
    embedding_model: str
    ollama_model: str


def get_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    telemetry_dir = base_dir.parent / "aiops_data" / "telemetry"
    reports_dir = base_dir.parent / "aiops_data" / "reports"
    return Settings(
        base_dir=base_dir,
        docs_dir=base_dir / "docs",
        cmdb_dir=base_dir / "cmdb",
        telemetry_dir=telemetry_dir,
        vector_db_dir=base_dir / "vector_db",
        reports_dir=reports_dir,
        default_snapshot=telemetry_dir / "telemetry_snapshot.jsonl",
        default_cmdb=base_dir / "cmdb" / "services.json",
        embedding_model=os.getenv("AIOPS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        ollama_model=os.getenv("AIOPS_OLLAMA_MODEL", "gemma3:12b"),
    )
