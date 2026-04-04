"""Event enrichment with logs and describe snippets."""

from typing import Any, Dict, List, Optional, Tuple

from .kubectl import run_kubectl_text
from .utils import (
    DESCRIBE_SIGNAL_MARKERS,
    LOG_SIGNAL_MARKERS,
    DEFAULT_LOG_TAIL_LINES,
    DEFAULT_MAX_LOG_SIGNATURES,
    DEFAULT_MAX_DESCRIBE_SNIPPETS,
    coerce_int,
    compact_text,
    normalize_log_signature,
    normalize_kubectl_kind,
)


def extract_log_signatures(log_text: str, max_signatures: int) -> List[str]:
    """Extract error signatures from log text."""
    signature_counts: Dict[str, int] = {}
    max_signatures = max(1, coerce_int(max_signatures, DEFAULT_MAX_LOG_SIGNATURES))

    for raw_line in str(log_text or "").splitlines():
        compact = compact_text(raw_line, max_len=420)
        if not compact:
            continue

        lowered = compact.lower()
        if not any(marker in lowered for marker in LOG_SIGNAL_MARKERS):
            continue

        signature = normalize_log_signature(compact)
        if len(signature) < 8:
            continue

        signature_counts[signature] = signature_counts.get(signature, 0) + 1

    ranked = sorted(signature_counts.items(), key=lambda x: (-x[1], x[0]))
    return [row[0] for row in ranked[:max_signatures]]


def extract_describe_snippets(describe_text: str, max_lines: int) -> List[str]:
    """Extract warning snippets from describe output."""
    max_lines = max(1, coerce_int(max_lines, DEFAULT_MAX_DESCRIBE_SNIPPETS))
    snippets: List[str] = []
    seen = set()

    for line in str(describe_text or "").splitlines():
        compact = compact_text(line, max_len=220)
        if not compact:
            continue

        lowered = compact.lower()
        if not any(marker in lowered for marker in DESCRIBE_SIGNAL_MARKERS):
            continue

        normalized = normalize_log_signature(compact)
        if normalized in seen:
            continue
        seen.add(normalized)
        snippets.append(compact)

        if len(snippets) >= max_lines:
            break

    return snippets


def collect_describe_snippets(
    namespace: str,
    source_kind: str,
    source_name: str,
    max_describe_snippets: int,
) -> List[str]:
    """Collect describe snippets for a resource."""
    if not namespace or not source_name:
        return []

    kubectl_kind = normalize_kubectl_kind(source_kind)
    if kubectl_kind not in {
        "pod",
        "deployment",
        "replicaset",
        "statefulset",
        "daemonset",
        "job",
        "cronjob",
    }:
        return []

    try:
        describe_output = run_kubectl_text(["describe", kubectl_kind, source_name, "-n", namespace])
    except RuntimeError:
        return []

    return extract_describe_snippets(describe_text=describe_output, max_lines=max_describe_snippets)


def collect_pod_log_signatures(
    namespace: str,
    pod_name: str,
    log_tail_lines: int,
    max_log_signatures: int,
) -> List[str]:
    """Collect log signatures from pod logs."""
    safe_tail = max(20, coerce_int(log_tail_lines, DEFAULT_LOG_TAIL_LINES))
    if not namespace or not pod_name:
        return []

    try:
        log_text = run_kubectl_text(
            [
                "logs",
                pod_name,
                "-n",
                namespace,
                f"--tail={safe_tail}",
                "--all-containers=true",
            ]
        )
    except RuntimeError:
        return []

    return extract_log_signatures(log_text=log_text, max_signatures=max_log_signatures)


def event_related_pod_name(metadata: Dict[str, Any]) -> Optional[str]:
    """Get related pod name from event metadata."""
    source_kind = str(metadata.get("source_kind", "")).strip().lower()
    source_name = str(metadata.get("source_name", "")).strip()

    if source_kind == "pod" and source_name:
        return source_name

    if source_kind == "event":
        involved_kind = str(metadata.get("involved_kind", "")).strip().lower()
        involved_name = str(metadata.get("involved_name", "")).strip()
        if involved_kind == "pod" and involved_name:
            return involved_name

    return None


def event_describe_target(metadata: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Get describe target (kind, name) from event metadata."""
    source_kind = str(metadata.get("source_kind", "")).strip()
    source_name = str(metadata.get("source_name", "")).strip()

    if source_kind and source_name and source_kind.lower() != "event":
        return source_kind, source_name

    if source_kind.lower() == "event":
        involved_kind = str(metadata.get("involved_kind", "")).strip()
        involved_name = str(metadata.get("involved_name", "")).strip()
        if involved_kind and involved_name:
            return involved_kind, involved_name

    return None, None


def primary_log_keyword(signatures: List[str]) -> str:
    """Get primary keyword from log signatures."""
    if not signatures:
        return "unknown"

    top = signatures[0].lower()
    for marker in LOG_SIGNAL_MARKERS:
        if marker in top:
            return marker
    return "unknown"


def enrich_events_with_log_signatures(
    events: List[Dict[str, Any]],
    include_log_signatures: bool,
    log_tail_lines: int,
    max_log_signatures: int,
) -> List[Dict[str, Any]]:
    """Enrich events with pod log signatures."""
    if not include_log_signatures:
        return events

    signature_cache: Dict[Tuple[str, str], List[str]] = {}

    for event in events:
        metadata = event.get("metadata", {}) if isinstance(event.get("metadata", {}), dict) else {}
        event["metadata"] = metadata

        namespace = str(metadata.get("namespace", "default"))
        pod_name = event_related_pod_name(metadata)
        if not pod_name:
            continue

        cache_key = (namespace, pod_name)
        if cache_key not in signature_cache:
            signature_cache[cache_key] = collect_pod_log_signatures(
                namespace=namespace,
                pod_name=pod_name,
                log_tail_lines=log_tail_lines,
                max_log_signatures=max_log_signatures,
            )

        signatures = signature_cache.get(cache_key, [])
        if not signatures:
            continue

        metadata["log_signatures"] = signatures
        metadata["log_signature_source"] = "kubectl logs"
        metadata["log_tail_lines"] = max(20, coerce_int(log_tail_lines, DEFAULT_LOG_TAIL_LINES))

        observed_signals = event.get("observed_signals", []) if isinstance(event.get("observed_signals", []), list) else []
        observed_signals.append(f"log_signature_count={len(signatures)}")
        observed_signals.append(f"log_primary_keyword={primary_log_keyword(signatures)}")
        event["observed_signals"] = observed_signals

    return events


def enrich_events_with_describe_snippets(
    events: List[Dict[str, Any]],
    include_describe_snippets: bool,
    max_describe_snippets: int,
) -> List[Dict[str, Any]]:
    """Enrich events with kubectl describe snippets."""
    if not include_describe_snippets:
        return events

    describe_cache: Dict[Tuple[str, str, str], List[str]] = {}

    for event in events:
        metadata = event.get("metadata", {}) if isinstance(event.get("metadata", {}), dict) else {}
        event["metadata"] = metadata

        namespace = str(metadata.get("namespace", "default"))
        target_kind, target_name = event_describe_target(metadata)
        if not target_kind or not target_name:
            continue

        cache_key = (namespace, target_kind.lower(), target_name)
        if cache_key not in describe_cache:
            describe_cache[cache_key] = collect_describe_snippets(
                namespace=namespace,
                source_kind=target_kind,
                source_name=target_name,
                max_describe_snippets=max_describe_snippets,
            )

        snippets = describe_cache.get(cache_key, [])
        if not snippets:
            continue

        metadata["describe_snippets"] = snippets
        metadata["describe_source_kind"] = str(target_kind)
        metadata["describe_source_name"] = str(target_name)

        observed_signals = event.get("observed_signals", []) if isinstance(event.get("observed_signals", []), list) else []
        observed_signals.append(f"describe_signal_count={len(snippets)}")
        event["observed_signals"] = observed_signals

    return events
