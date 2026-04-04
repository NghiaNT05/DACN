"""Pod status collector."""

from typing import Any, Dict, List

from ..utils import build_event, pod_to_service_name


def collect_pod_events(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect incident events from pod status."""
    events: List[Dict[str, Any]] = []
    for item in items:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}
        status = item.get("status", {}) if isinstance(item.get("status", {}), dict) else {}

        pod_name = str(metadata.get("name", "unknown"))
        namespace = str(metadata.get("namespace", "default"))
        phase = str(status.get("phase", "Unknown"))

        if phase in {"Running", "Succeeded"}:
            continue

        service = pod_to_service_name(pod_name)
        observed_signals: List[str] = [f"pod_phase={phase}"]
        category = "dependency_failure"
        severity = "medium"

        for cstatus in status.get("containerStatuses", []) or []:
            if not isinstance(cstatus, dict):
                continue
            restart_count = int(cstatus.get("restartCount", 0) or 0)
            if restart_count > 0:
                observed_signals.append(f"restart_count={restart_count}")

            waiting = cstatus.get("state", {}).get("waiting", {})
            if isinstance(waiting, dict) and waiting:
                reason = str(waiting.get("reason", "Unknown"))
                observed_signals.append(f"waiting_reason={reason}")

                if reason in {"CrashLoopBackOff", "RunContainerError"}:
                    severity = "critical"
                    category = "rollout_failure"
                elif reason in {"ImagePullBackOff", "ErrImagePull", "ContainerCreating"}:
                    severity = "high"
                    category = "rollout_failure"
                elif reason in {"CreateContainerConfigError", "CreateContainerError"}:
                    severity = "high"
                    category = "config_drift"

            terminated = cstatus.get("state", {}).get("terminated", {})
            if isinstance(terminated, dict) and terminated:
                reason = str(terminated.get("reason", ""))
                if reason:
                    observed_signals.append(f"terminated_reason={reason}")
                if reason == "OOMKilled":
                    severity = "high"
                    category = "resource_pressure"

        if phase == "Failed":
            severity = "critical"

        events.append(
            build_event(
                severity=severity,
                category=category,
                source_service=service,
                observed_signals=observed_signals,
                metadata={
                    "namespace": namespace,
                    "source_kind": "Pod",
                    "source_name": pod_name,
                },
            )
        )

    return events
