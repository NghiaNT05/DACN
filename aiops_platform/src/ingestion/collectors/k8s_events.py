"""Kubernetes events stream collector."""

from typing import Any, Dict, List, Optional, Tuple

from ..utils import (
    build_event,
    coerce_int,
    compact_text,
    parse_iso,
    pod_to_service_name,
    replicaset_to_service_name,
)


def _extract_event_timestamp(event_item: Dict[str, Any]) -> Optional[str]:
    """Extract timestamp from K8s event."""
    candidates = [
        event_item.get("eventTime"),
        event_item.get("lastTimestamp"),
        event_item.get("firstTimestamp"),
        event_item.get("metadata", {}).get("creationTimestamp"),
        event_item.get("series", {}).get("lastObservedTime"),
    ]
    for candidate in candidates:
        parsed = parse_iso(str(candidate or ""))
        if parsed is not None:
            return parsed.isoformat()
    return None


def _event_category_and_severity(event_type: str, reason: str, message: str) -> Tuple[str, str]:
    """Determine category and severity from event details."""
    event_type_l = str(event_type or "").strip().lower()
    reason_l = str(reason or "").strip().lower()
    message_l = str(message or "").strip().lower()

    category = "dependency_failure"
    severity = "medium" if event_type_l == "warning" else "low"

    if reason_l in {
        "failed",
        "unhealthy",
        "backoff",
        "failedcreate",
        "failedsync",
        "failedpoststarthook",
    }:
        category = "rollout_failure"
        severity = "high"

    if reason_l in {
        "failedmount",
        "failedattachvolume",
        "createcontainerconfigerror",
        "createcontainererror",
        "errimagepull",
        "imagepullbackoff",
        "invalidimagename",
    }:
        category = "config_drift"
        severity = "high"

    if reason_l in {"faileddiskscheduling", "failedscheduling"}:
        category = "resource_pressure"
        severity = "medium"

    if "oom" in message_l or "out of memory" in message_l:
        category = "resource_pressure"
        severity = "high"

    if reason_l == "backoff" and "restarting failed container" in message_l:
        category = "rollout_failure"
        severity = "critical"

    return category, severity


def _event_source_service(involved_kind: str, involved_name: str) -> str:
    """Extract source service from involved object."""
    kind_l = str(involved_kind or "").strip().lower()
    name = str(involved_name or "unknown")

    if kind_l == "pod":
        return pod_to_service_name(name)
    if kind_l == "replicaset":
        return replicaset_to_service_name(name)
    if kind_l in {"deployment", "service", "daemonset", "statefulset", "job", "cronjob"}:
        return name
    return name


def collect_k8s_event_stream(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect incident events from K8s event stream."""
    events: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}
        namespace = str(metadata.get("namespace", "default"))
        event_name = str(metadata.get("name", "unknown"))

        involving = item.get("regarding", {})
        if not isinstance(involving, dict) or not involving:
            involving = item.get("involvedObject", {})
        if not isinstance(involving, dict):
            involving = {}

        involved_kind = str(involving.get("kind", "Unknown"))
        involved_name = str(involving.get("name", "unknown"))

        event_type = str(item.get("type", "Normal"))
        reason = str(item.get("reason", "Unknown"))
        message = compact_text(item.get("note") or item.get("message") or "")

        # Keep warning events as incident candidates and skip normal noise.
        if event_type.strip().lower() != "warning":
            continue

        category, severity = _event_category_and_severity(event_type=event_type, reason=reason, message=message)
        source_service = _event_source_service(involved_kind=involved_kind, involved_name=involved_name)

        count_value = item.get("count")
        if count_value is None and isinstance(item.get("series", {}), dict):
            count_value = item.get("series", {}).get("count")
        event_count = max(1, coerce_int(count_value, 1))

        observed_signals = [
            f"k8s_event_reason={reason}",
            f"k8s_event_object_kind={involved_kind}",
            f"k8s_event_type={event_type}",
        ]
        if event_count > 1:
            observed_signals.append(f"k8s_event_count={event_count}")

        events.append(
            build_event(
                severity=severity,
                category=category,
                source_service=source_service,
                observed_signals=observed_signals,
                metadata={
                    "namespace": namespace,
                    "source_kind": "Event",
                    "source_name": involved_name,
                    "event_name": event_name,
                    "event_type": event_type,
                    "event_reason": reason,
                    "event_message": message,
                    "involved_kind": involved_kind,
                    "involved_name": involved_name,
                    "event_count": event_count,
                },
                timestamp=_extract_event_timestamp(item),
            )
        )

    return events
