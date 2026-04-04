"""Collectors package for Kubernetes resources."""

from .deployment import collect_deployment_events
from .pod import collect_pod_events
from .k8s_events import collect_k8s_event_stream

__all__ = [
    "collect_deployment_events",
    "collect_pod_events",
    "collect_k8s_event_stream",
]
