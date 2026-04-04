"""Retrieval bundle generation for RAG pipeline.

Converts incident events into text bundles suitable for embedding and retrieval.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_BUNDLE_DIR = Path(__file__).resolve().parents[2] / "data" / "retrieval"
BUNDLE_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_list(items: List[str], prefix: str = "- ") -> str:
    if not items:
        return "(none)"
    return "\n".join(f"{prefix}{item}" for item in items)


def _extract_metadata_field(metadata: Dict[str, Any], field: str) -> str:
    value = metadata.get(field)
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value)


def incident_to_text(event: Dict[str, Any]) -> str:
    """Convert a single incident event to retrieval-ready text block."""
    metadata = event.get("metadata", {}) or {}
    
    lines = [
        "=" * 60,
        f"INCIDENT_ID: {event.get('incident_id', 'unknown')}",
        f"TIMESTAMP: {event.get('timestamp', 'unknown')}",
        f"SEVERITY: {event.get('severity', 'unknown')}",
        f"CATEGORY: {event.get('category', 'unknown')}",
        f"SOURCE_SERVICE: {event.get('source_service', 'unknown')}",
        f"NAMESPACE: {metadata.get('namespace', 'default')}",
        "",
        "OBSERVED_SIGNALS:",
        _format_list(event.get("observed_signals", [])),
        "",
        "CANDIDATE_SERVICES:",
        _format_list(event.get("candidate_services", [])),
    ]
    
    # Add log signatures if present
    log_signatures = metadata.get("log_signatures", [])
    if log_signatures:
        lines.extend([
            "",
            "LOG_SIGNATURES:",
            _format_list(log_signatures),
        ])
    
    # Add describe snippets if present
    describe_snippets = metadata.get("describe_snippets", [])
    if describe_snippets:
        lines.extend([
            "",
            "DESCRIBE_DIAGNOSTICS:",
            _format_list(describe_snippets),
        ])
    
    # Add correlation info if present
    correlation_key = metadata.get("correlation_key")
    if correlation_key:
        lines.extend([
            "",
            f"CORRELATION_KEY: {correlation_key}",
            f"OCCURRENCE_COUNT: {metadata.get('correlation_count', 1)}",
            f"FIRST_SEEN: {metadata.get('first_seen_at', 'unknown')}",
        ])
    
    # Add event-specific metadata for k8s events
    event_reason = metadata.get("event_reason")
    if event_reason:
        lines.extend([
            "",
            f"K8S_EVENT_REASON: {event_reason}",
            f"K8S_EVENT_MESSAGE: {metadata.get('event_message', '')}",
            f"K8S_INVOLVED_KIND: {metadata.get('involved_kind', '')}",
            f"K8S_INVOLVED_NAME: {metadata.get('involved_name', '')}",
        ])
    
    lines.append("=" * 60)
    return "\n".join(lines)


def generate_bundle_text(events: List[Dict[str, Any]], cycle_id: Optional[str] = None) -> str:
    """Generate full retrieval bundle text from list of incidents."""
    header_lines = [
        "# INCIDENT RETRIEVAL BUNDLE",
        f"# Generated: {_now_iso()}",
        f"# Version: {BUNDLE_VERSION}",
        f"# Cycle: {cycle_id or 'single'}",
        f"# Incident Count: {len(events)}",
        "",
        "# This bundle is designed for chunking and embedding into a vector store.",
        "# Each incident block is delimited by '=' lines for easy parsing.",
        "",
    ]
    
    if not events:
        header_lines.append("# (No incidents in this cycle)")
        return "\n".join(header_lines)
    
    # Group by severity for better context
    severity_order = ["critical", "high", "medium", "low"]
    events_by_severity: Dict[str, List[Dict[str, Any]]] = {s: [] for s in severity_order}
    
    for event in events:
        severity = event.get("severity", "low")
        if severity in events_by_severity:
            events_by_severity[severity].append(event)
        else:
            events_by_severity["low"].append(event)
    
    body_lines = []
    for severity in severity_order:
        severity_events = events_by_severity[severity]
        if not severity_events:
            continue
        
        body_lines.extend([
            "",
            f"## {severity.upper()} SEVERITY INCIDENTS ({len(severity_events)})",
            "",
        ])
        
        for event in severity_events:
            body_lines.append(incident_to_text(event))
            body_lines.append("")
    
    return "\n".join(header_lines + body_lines)


def write_bundle(
    events: List[Dict[str, Any]],
    output_dir: Optional[Path] = None,
    cycle_id: Optional[str] = None,
    filename_prefix: str = "bundle",
) -> Path:
    """Write retrieval bundle to file.
    
    Returns the path to the written bundle file.
    """
    output_dir = output_dir or DEFAULT_BUNDLE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cycle_suffix = f"_{cycle_id}" if cycle_id else ""
    filename = f"{filename_prefix}{cycle_suffix}_{timestamp}.txt"
    
    bundle_path = output_dir / filename
    bundle_text = generate_bundle_text(events, cycle_id=cycle_id)
    bundle_path.write_text(bundle_text, encoding="utf-8")
    
    return bundle_path


def write_bundle_json(
    events: List[Dict[str, Any]],
    output_dir: Optional[Path] = None,
    cycle_id: Optional[str] = None,
    filename_prefix: str = "bundle",
) -> Path:
    """Write retrieval bundle as JSON with text field per incident.
    
    This format is useful for structured loading into vector DBs.
    """
    output_dir = output_dir or DEFAULT_BUNDLE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cycle_suffix = f"_{cycle_id}" if cycle_id else ""
    filename = f"{filename_prefix}{cycle_suffix}_{timestamp}.json"
    
    bundle_items = []
    for event in events:
        bundle_items.append({
            "incident_id": event.get("incident_id"),
            "timestamp": event.get("timestamp"),
            "severity": event.get("severity"),
            "category": event.get("category"),
            "source_service": event.get("source_service"),
            "namespace": (event.get("metadata") or {}).get("namespace", "default"),
            "text": incident_to_text(event),
            "metadata": event.get("metadata", {}),
        })
    
    bundle_data = {
        "version": BUNDLE_VERSION,
        "generated_at": _now_iso(),
        "cycle_id": cycle_id,
        "incident_count": len(events),
        "items": bundle_items,
    }
    
    bundle_path = output_dir / filename
    bundle_path.write_text(json.dumps(bundle_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return bundle_path


def load_bundle_json(bundle_path: Path) -> Dict[str, Any]:
    """Load a JSON bundle file."""
    return json.loads(bundle_path.read_text(encoding="utf-8"))
