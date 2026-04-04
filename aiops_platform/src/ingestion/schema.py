"""Schema validation for incident events."""

import json
from pathlib import Path
from typing import Any, Dict, List

from .utils import validate_event

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

DEFAULT_INCIDENT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "data" / "schemas" / "incident_event.schema.json"


def load_schema_validator(schema_path: Path):
    """Load JSON schema validator."""
    if Draft202012Validator is None:
        return None

    try:
        schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(schema_payload, dict):
        return None

    try:
        return Draft202012Validator(schema_payload)
    except Exception:
        return None


def validate_against_schema(
    events: List[Dict[str, Any]],
    schema_path: Path,
    enable_schema_validation: bool,
) -> Dict[str, Any]:
    """Validate events against JSON schema."""
    if not enable_schema_validation:
        return {
            "enabled": False,
            "valid_events": events,
            "invalid_count": 0,
            "errors": [],
            "schema_path": str(schema_path),
        }

    validator = load_schema_validator(schema_path)
    if validator is None:
        fallback_valid = [event for event in events if validate_event(event)]
        invalid_count = len(events) - len(fallback_valid)
        return {
            "enabled": False,
            "valid_events": fallback_valid,
            "invalid_count": invalid_count,
            "errors": ["jsonschema validator unavailable; fallback validation used"],
            "schema_path": str(schema_path),
        }

    valid_events: List[Dict[str, Any]] = []
    errors: List[str] = []

    for index, event in enumerate(events):
        issue_list = sorted(validator.iter_errors(event), key=lambda e: list(e.path))
        if not issue_list:
            valid_events.append(event)
            continue

        incident_id = str(event.get("incident_id", f"index-{index}"))
        first_issue = issue_list[0]
        field_path = ".".join([str(part) for part in first_issue.absolute_path]) or "root"
        errors.append(f"incident={incident_id}; field={field_path}; message={first_issue.message}")

    return {
        "enabled": True,
        "valid_events": valid_events,
        "invalid_count": len(events) - len(valid_events),
        "errors": errors,
        "schema_path": str(schema_path),
    }
