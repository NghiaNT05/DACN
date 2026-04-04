"""Deployment status collector."""

from typing import Any, Dict, List

from ..utils import build_event


def collect_deployment_events(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect incident events from deployment status."""
    events: List[Dict[str, Any]] = []
    for item in items:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}
        spec = item.get("spec", {}) if isinstance(item.get("spec", {}), dict) else {}
        status = item.get("status", {}) if isinstance(item.get("status", {}), dict) else {}

        service = str(metadata.get("name", "unknown"))
        namespace = str(metadata.get("namespace", "default"))
        desired = int(spec.get("replicas", 1) or 0)
        ready = int(status.get("readyReplicas", 0) or 0)
        unavailable = int(status.get("unavailableReplicas", 0) or 0)

        observed_signals: List[str] = []
        if ready < desired:
            observed_signals.append(f"deploy_not_ready={ready}/{desired}")
        if unavailable > 0:
            observed_signals.append(f"unavailable_replicas={unavailable}")

        for cond in status.get("conditions", []) or []:
            if not isinstance(cond, dict):
                continue
            cond_type = str(cond.get("type", ""))
            cond_status = str(cond.get("status", ""))
            if cond_type in {"Available", "Progressing"} and cond_status != "True":
                observed_signals.append(f"condition_{cond_type.lower()}={cond_status}")

        if not observed_signals:
            continue

        severity = "high" if ready == 0 else "medium"
        events.append(
            build_event(
                severity=severity,
                category="rollout_failure",
                source_service=service,
                observed_signals=observed_signals,
                metadata={
                    "namespace": namespace,
                    "source_kind": "Deployment",
                    "source_name": service,
                },
            )
        )

    return events
