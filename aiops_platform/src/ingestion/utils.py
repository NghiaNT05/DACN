"""Utility functions for ingestion pipeline."""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

STATE_VERSION = 1
DEFAULT_COOLDOWN_SECONDS = 300
DEFAULT_LOG_TAIL_LINES = 120
DEFAULT_MAX_LOG_SIGNATURES = 3
DEFAULT_MAX_DESCRIBE_SNIPPETS = 4

LOG_SIGNAL_MARKERS = (
    "error",
    "exception",
    "fail",
    "timeout",
    "refused",
    "backoff",
    "oom",
    "unavailable",
    "denied",
    "panic",
    "crash",
)

DESCRIBE_SIGNAL_MARKERS = (
    "warning",
    "failed",
    "error",
    "back-off",
    "mountvolume",
    "unhealthy",
    "readiness probe failed",
    "liveness probe failed",
    "imagepullbackoff",
    "errimagepull",
)


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def coerce_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_iso(value: str) -> Optional[datetime]:
    """Parse ISO format timestamp string."""
    text = str(value or "").strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def new_incident_id() -> str:
    """Generate new incident ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ING-{ts}-{uuid.uuid4().hex[:8]}"


def pod_to_service_name(pod_name: str) -> str:
    """Extract service name from pod name."""
    parts = str(pod_name or "").split("-")
    if len(parts) >= 3:
        return "-".join(parts[:-2])
    return str(pod_name or "unknown")


def replicaset_to_service_name(rs_name: str) -> str:
    """Extract service name from replicaset name."""
    parts = str(rs_name or "").split("-")
    if len(parts) >= 2:
        return "-".join(parts[:-1])
    return str(rs_name or "unknown")


def severity_rank(severity: str) -> int:
    """Get numeric rank for severity (lower = more severe)."""
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return order.get(severity, 3)


def compact_text(value: Any, max_len: int = 220) -> str:
    """Compact whitespace and truncate text."""
    text = " ".join(str(value or "").split())
    return text[:max_len]


def normalize_log_signature(line: str) -> str:
    """Normalize log line for signature comparison."""
    normalized = compact_text(line, max_len=420).lower()
    normalized = re.sub(r"^\d{4}-\d{2}-\d{2}[tT ][^\s]+\s*", "", normalized)
    normalized = re.sub(r"\b[0-9a-f]{8,}\b", "<hex>", normalized)
    normalized = re.sub(r"\b\d+\b", "<n>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:180]


def normalize_kubectl_kind(kind: str) -> str:
    """Normalize kubectl resource kind."""
    kind_l = str(kind or "").strip().lower()
    mapping = {
        "pod": "pod",
        "pods": "pod",
        "deployment": "deployment",
        "deploy": "deployment",
        "replicaset": "replicaset",
        "statefulset": "statefulset",
        "daemonset": "daemonset",
        "job": "job",
        "cronjob": "cronjob",
        "service": "service",
    }
    return mapping.get(kind_l, kind_l)


def signal_family(signal: str) -> str:
    """Extract signal family from signal string."""
    text = str(signal or "")
    if "=" in text:
        return text.split("=", 1)[0].strip().lower()
    return text.strip().lower()


def event_correlation_key(event: Dict[str, Any]) -> str:
    """Generate correlation key for event."""
    metadata = event.get("metadata", {}) if isinstance(event.get("metadata", {}), dict) else {}

    parts = [
        str(metadata.get("namespace", "default")).strip().lower(),
        str(metadata.get("source_kind", "unknown")).strip().lower(),
        str(event.get("source_service", "unknown")).strip().lower(),
        str(event.get("category", "unknown")).strip().lower(),
    ]

    families = sorted(
        {
            signal_family(sig)
            for sig in event.get("observed_signals", []) or []
            if str(sig or "").strip()
        }
    )

    material = "|".join(parts + families)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"corr-{digest}"


def build_event(
    severity: str,
    category: str,
    source_service: str,
    observed_signals: List[str],
    metadata: Dict[str, Any],
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Build standardized event dictionary."""
    deduped_signals: List[str] = []
    seen = set()
    for signal in observed_signals:
        if signal in seen:
            continue
        seen.add(signal)
        deduped_signals.append(signal)

    return {
        "incident_id": new_incident_id(),
        "timestamp": timestamp or now_iso(),
        "severity": severity,
        "category": category,
        "source_service": source_service,
        "observed_signals": deduped_signals,
        "candidate_services": [source_service],
        "metadata": metadata,
    }


def validate_event(event: Dict[str, Any]) -> bool:
    """Basic validation for event structure."""
    required = ["incident_id", "timestamp", "severity", "category", "source_service", "observed_signals"]
    for key in required:
        if key not in event:
            return False
    if not isinstance(event.get("observed_signals", []), list) or not event["observed_signals"]:
        return False
    return True
