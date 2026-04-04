"""State management and cooldown logic."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .utils import (
    STATE_VERSION,
    DEFAULT_COOLDOWN_SECONDS,
    now_iso,
    coerce_int,
    parse_iso,
    severity_rank,
    event_correlation_key,
)


def default_state() -> Dict[str, Any]:
    """Create default state structure."""
    return {
        "version": STATE_VERSION,
        "updated_at": now_iso(),
        "entries": {},
    }


def load_state(state_path: Path) -> Dict[str, Any]:
    """Load state from file."""
    if not state_path.exists():
        return default_state()

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state()

    if not isinstance(payload, dict):
        return default_state()

    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        payload["entries"] = {}

    payload["version"] = STATE_VERSION
    if "updated_at" not in payload:
        payload["updated_at"] = now_iso()
    return payload


def write_state(state_path: Path, state: Dict[str, Any]) -> None:
    """Write state to file."""
    state["version"] = STATE_VERSION
    state["updated_at"] = now_iso()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def apply_correlation_and_cooldown(
    events: List[Dict[str, Any]],
    state_path: Optional[Path],
    cooldown_seconds: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Apply correlation tracking and cooldown suppression."""
    if state_path is None:
        return events, 0

    cooldown_seconds = max(0, coerce_int(cooldown_seconds, DEFAULT_COOLDOWN_SECONDS))
    state = load_state(state_path)
    entries = state.get("entries", {}) if isinstance(state.get("entries", {}), dict) else {}
    state["entries"] = entries

    now_dt = datetime.now(timezone.utc)
    now_iso_str = now_dt.isoformat()

    emitted: List[Dict[str, Any]] = []
    suppressed_count = 0

    for event in events:
        metadata = event.get("metadata", {}) if isinstance(event.get("metadata", {}), dict) else {}
        event["metadata"] = metadata

        correlation_key = event_correlation_key(event)
        entry = entries.get(correlation_key, {})
        if not isinstance(entry, dict):
            entry = {}

        occurrence_count = coerce_int(entry.get("occurrence_count"), 0) + 1
        first_seen_at = str(entry.get("first_seen_at", now_iso_str))

        previous_emitted_at = parse_iso(str(entry.get("last_emitted_at", "")))
        previous_severity = str(entry.get("last_severity", "low"))
        current_severity = str(event.get("severity", "low"))
        severity_escalation = severity_rank(current_severity) < severity_rank(previous_severity)

        within_cooldown = False
        if previous_emitted_at is not None and cooldown_seconds > 0:
            elapsed_seconds = (now_dt - previous_emitted_at).total_seconds()
            within_cooldown = elapsed_seconds < cooldown_seconds

        should_emit = (not within_cooldown) or severity_escalation

        entry["namespace"] = str(metadata.get("namespace", "default"))
        entry["source_service"] = str(event.get("source_service", "unknown"))
        entry["category"] = str(event.get("category", "unknown"))
        entry["first_seen_at"] = first_seen_at
        entry["last_seen_at"] = now_iso_str
        entry["last_severity"] = current_severity
        entry["occurrence_count"] = occurrence_count
        entry["last_signals"] = list(event.get("observed_signals", []) or [])
        entry["suppressed_count"] = coerce_int(entry.get("suppressed_count"), 0)

        if should_emit:
            entry["last_emitted_at"] = now_iso_str
            metadata["correlation_key"] = correlation_key
            metadata["correlation_count"] = occurrence_count
            metadata["first_seen_at"] = first_seen_at
            metadata["last_seen_at"] = now_iso_str
            metadata["cooldown_seconds"] = cooldown_seconds
            metadata["cooldown_suppressed"] = False
            metadata["severity_escalation"] = severity_escalation
            emitted.append(event)
        else:
            entry["suppressed_count"] += 1
            suppressed_count += 1

        entries[correlation_key] = entry

    write_state(state_path, state)
    return emitted, suppressed_count
