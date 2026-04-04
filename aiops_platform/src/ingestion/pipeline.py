"""Main ingestion pipeline - orchestrates collection, enrichment, and validation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .kubectl import run_kubectl_json
from .utils import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_LOG_TAIL_LINES,
    DEFAULT_MAX_LOG_SIGNATURES,
    DEFAULT_MAX_DESCRIBE_SNIPPETS,
    severity_rank,
    validate_event,
)
from .enrichment import (
    enrich_events_with_log_signatures,
    enrich_events_with_describe_snippets,
)
from .schema import DEFAULT_INCIDENT_SCHEMA_PATH, validate_against_schema
from .state import apply_correlation_and_cooldown
from .collectors import (
    collect_deployment_events,
    collect_pod_events,
    collect_k8s_event_stream,
)


def _collect_events_once(namespace: Optional[str] = None, include_k8s_events: bool = True) -> List[Dict[str, Any]]:
    """Collect all events from Kubernetes in one cycle."""
    scope = ["-n", namespace] if namespace else ["-A"]

    deploy_payload = run_kubectl_json(["get", "deploy", *scope])
    pod_payload = run_kubectl_json(["get", "pods", *scope])
    event_payload: Dict[str, Any] = {"items": []}
    if include_k8s_events:
        try:
            event_payload = run_kubectl_json(["get", "events", *scope])
        except RuntimeError:
            event_payload = {"items": []}

    events = []
    events.extend(collect_deployment_events(deploy_payload.get("items", []) or []))
    events.extend(collect_pod_events(pod_payload.get("items", []) or []))
    if include_k8s_events:
        events.extend(collect_k8s_event_stream(event_payload.get("items", []) or []))

    filtered = [event for event in events if validate_event(event)]

    # Dedupe same source and signal set in one collection cycle.
    seen = set()
    deduped = []
    for event in filtered:
        metadata = event.get("metadata", {}) if isinstance(event.get("metadata", {}), dict) else {}
        fp = (
            event.get("category"),
            metadata.get("namespace"),
            metadata.get("source_name"),
            tuple(sorted(event.get("observed_signals", []))),
        )
        if fp in seen:
            continue
        seen.add(fp)
        deduped.append(event)

    deduped.sort(key=lambda x: (severity_rank(str(x.get("severity", "low"))), str(x.get("source_service", ""))))
    return deduped


def run_ingestion_cycle(
    namespace: Optional[str] = None,
    state_path: Optional[Path] = None,
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    include_k8s_events: bool = True,
    include_log_signatures: bool = True,
    log_tail_lines: int = DEFAULT_LOG_TAIL_LINES,
    max_log_signatures: int = DEFAULT_MAX_LOG_SIGNATURES,
    include_describe_snippets: bool = True,
    max_describe_snippets: int = DEFAULT_MAX_DESCRIBE_SNIPPETS,
    enable_schema_validation: bool = True,
    schema_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run one ingestion cycle: collect, enrich, validate, dedupe."""
    base_events = _collect_events_once(namespace=namespace, include_k8s_events=include_k8s_events)

    enriched_events = enrich_events_with_log_signatures(
        events=base_events,
        include_log_signatures=include_log_signatures,
        log_tail_lines=log_tail_lines,
        max_log_signatures=max_log_signatures,
    )
    enriched_events = enrich_events_with_describe_snippets(
        events=enriched_events,
        include_describe_snippets=include_describe_snippets,
        max_describe_snippets=max_describe_snippets,
    )

    effective_schema_path = schema_path or DEFAULT_INCIDENT_SCHEMA_PATH
    validation_result = validate_against_schema(
        events=enriched_events,
        schema_path=effective_schema_path,
        enable_schema_validation=enable_schema_validation,
    )

    schema_valid_events = validation_result["valid_events"]
    emitted_events, suppressed_count = apply_correlation_and_cooldown(
        events=schema_valid_events,
        state_path=state_path,
        cooldown_seconds=cooldown_seconds,
    )

    return {
        "events": emitted_events,
        "base_event_count": len(base_events),
        "enriched_event_count": len(enriched_events),
        "schema_valid_event_count": len(schema_valid_events),
        "schema_invalid_event_count": int(validation_result["invalid_count"]),
        "schema_validation_enabled": bool(validation_result["enabled"]),
        "schema_path": str(validation_result["schema_path"]),
        "schema_errors_preview": list(validation_result["errors"][:5]),
        "emitted_event_count": len(emitted_events),
        "suppressed_event_count": suppressed_count,
    }


def collect_incident_events(
    namespace: Optional[str] = None,
    state_path: Optional[Path] = None,
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    include_k8s_events: bool = True,
    include_log_signatures: bool = True,
    log_tail_lines: int = DEFAULT_LOG_TAIL_LINES,
    max_log_signatures: int = DEFAULT_MAX_LOG_SIGNATURES,
    include_describe_snippets: bool = True,
    max_describe_snippets: int = DEFAULT_MAX_DESCRIBE_SNIPPETS,
    enable_schema_validation: bool = True,
    schema_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Convenience function to collect and return events only."""
    result = run_ingestion_cycle(
        namespace=namespace,
        state_path=state_path,
        cooldown_seconds=cooldown_seconds,
        include_k8s_events=include_k8s_events,
        include_log_signatures=include_log_signatures,
        log_tail_lines=log_tail_lines,
        max_log_signatures=max_log_signatures,
        include_describe_snippets=include_describe_snippets,
        max_describe_snippets=max_describe_snippets,
        enable_schema_validation=enable_schema_validation,
        schema_path=schema_path,
    )
    return result["events"]


def write_events_json(output_path: Path, events: List[Dict[str, Any]]) -> None:
    """Write events to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(events, handle, ensure_ascii=True, indent=2)
