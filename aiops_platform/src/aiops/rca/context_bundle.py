import json
from collections import Counter, defaultdict
from pathlib import Path

from aiops.observers import collect_workload_signals


def _load_snapshot(snapshot_path):
    path = Path(snapshot_path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_cmdb(cmdb_path):
    with Path(cmdb_path).open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("services", [])


def _compact_log_line(line):
    line = line.replace("\n", " ").strip()
    if len(line) > 420:
        return line[:420] + "..."
    return line


def _parse_metric_row(content):
    try:
        row = json.loads(content)
    except json.JSONDecodeError:
        return None, None

    metric = row.get("metric", {})
    value = row.get("value", [])
    if len(value) < 2:
        return metric, None

    try:
        return metric, float(value[1])
    except (TypeError, ValueError):
        return metric, None


def _extract_service(metric):
    if not isinstance(metric, dict):
        return "unknown"
    for key in (
        "destination_workload",
        "destination_service_name",
        "k8s_service_name",
        "service_name",
        "service",
        "app_kubernetes_io_name",
        "app",
        "pod",
        "job",
    ):
        value = metric.get(key)
        if value:
            return str(value)
    return "unknown"


def _metric_threshold_name(metric_name):
    mapping = {
        "pod_cpu_5m": "cpu",
        "pod_restarts": "pod_restarts",
        "service_latency_p95_ms": "latency_p95_ms",
        "service_latency_p95_ms_http": "latency_p95_ms",
        "service_error_rate": "error_rate",
        "service_error_rate_http": "error_rate",
    }
    return mapping.get(metric_name)


def _is_error_log(content):
    text = content.lower()
    markers = ("error", "fail", "failed", "timeout", "refused", "exception", "unavailable")
    return any(marker in text for marker in markers)


def build_incident_context_bundle(snapshot_path, cmdb_path, datasource_health=None, max_logs=15, max_metrics=20):
    rows = _load_snapshot(snapshot_path)
    services = _load_cmdb(cmdb_path)
    services_by_name = {svc.get("name"): svc for svc in services if svc.get("name")}

    metric_rows = [r for r in rows if r.get("type") == "metric"][:max_metrics]
    log_rows = [r for r in rows if r.get("type") == "log"]
    error_rows = [r for r in rows if r.get("type") == "telemetry_error"]

    cmdb_lines = []
    for svc in services:
        cmdb_lines.append(
            f"- {svc.get('name')}: deps={svc.get('dependencies', [])}, thresholds={svc.get('thresholds', {})}"
        )

    metric_anomalies = defaultdict(list)
    for row in metric_rows:
        metric_name = row.get("metric_name", "unknown_metric")
        metric, value = _parse_metric_row(str(row.get("content", "")))
        if value is None:
            continue

        service = _extract_service(metric)
        threshold_name = _metric_threshold_name(metric_name)
        if service not in services_by_name or threshold_name is None:
            continue

        thresholds = services_by_name[service].get("thresholds", {})
        threshold = thresholds.get(threshold_name)
        if threshold is None:
            continue

        if value > threshold:
            metric_anomalies[service].append(
                {
                    "metric": metric_name,
                    "value": round(value, 4),
                    "threshold": threshold,
                    "timestamp": row.get("timestamp", ""),
                }
            )

    metric_lines = []
    for service, anomalies in sorted(metric_anomalies.items()):
        joined = ", ".join(
            [
                f"{item['metric']}={item['value']} (threshold={item['threshold']}, ts={item['timestamp']})"
                for item in anomalies[:5]
            ]
        )
        metric_lines.append(f"- {service}: {joined}")

    error_count = Counter()
    log_samples = defaultdict(list)
    for row in log_rows:
        content = str(row.get("content", ""))
        if not _is_error_log(content):
            continue

        md = row.get("metadata", {})
        svc = md.get("app", md.get("pod", "unknown"))
        if svc.startswith("checkoutservice"):
            svc = "checkoutservice"
        if svc.startswith("paymentservice"):
            svc = "paymentservice"

        error_count[svc] += 1
        if len(log_samples[svc]) < 3:
            sample = _compact_log_line(content)
            if sample not in log_samples[svc]:
                log_samples[svc].append(sample)

    top_services = error_count.most_common(max_logs)
    log_lines = []
    for svc, count in top_services:
        samples = " | ".join(log_samples.get(svc, []))
        log_lines.append(f"- {svc}: error_count={count}; samples={samples}")

    error_lines = []
    for row in error_rows:
        error_lines.append(
            f"- source={row.get('source')} metric={row.get('metric_name', 'n/a')} detail={_compact_log_line(str(row.get('content', '')))}"
        )

    health_text = "none"
    if datasource_health is not None:
        health_text = json.dumps(datasource_health, ensure_ascii=True)

    dependency_hints = []
    for service in sorted(metric_anomalies.keys()):
        deps = services_by_name.get(service, {}).get("dependencies", [])
        if deps:
            dependency_hints.append(f"- {service} depends_on={deps}")

    runtime = collect_workload_signals(namespace="default")
    runtime_service_names = sorted(
        {
            str(dep.get("name"))
            for dep in runtime.get("deployments", [])
            if dep.get("name")
        }
    )
    allowed_services = sorted(set(services_by_name.keys()) | set(runtime_service_names))
    deployment_lines = []
    for dep in runtime.get("deployments", []):
        deployment_lines.append(
            f"- {dep.get('name')}: desired={dep.get('desired')} ready={dep.get('ready')} available={dep.get('available')} unavailable={dep.get('unavailable')}"
        )

    scaled_to_zero_lines = [f"- {svc}" for svc in runtime.get("scaled_to_zero", [])]
    unhealthy_lines = [f"- {svc}" for svc in runtime.get("unhealthy_deployments", [])]
    crashloop_lines = [
        f"- {item.get('pod')}: reason={item.get('reason')}" for item in runtime.get("crashloop_pods", [])
    ]

    runtime_by_service = {}
    for dep in runtime.get("deployments", []):
        name = dep.get("name")
        if name:
            runtime_by_service[name] = {
                "desired": dep.get("desired", 0),
                "ready": dep.get("ready", 0),
                "available": dep.get("available", 0),
                "unavailable": dep.get("unavailable", 0),
            }

    log_pressure = {svc: count for svc, count in error_count.items()}
    metric_anomaly_count = {svc: len(items) for svc, items in metric_anomalies.items()}

    facts = {}
    for svc in allowed_services:
        facts[svc] = {
            "service_type": services_by_name.get(svc, {}).get("type", "unknown"),
            "runtime": runtime_by_service.get(
                svc,
                {"desired": None, "ready": None, "available": None, "unavailable": None},
            ),
            "log_error_count": log_pressure.get(svc, 0),
            "metric_anomaly_count": metric_anomaly_count.get(svc, 0),
            "dependencies": services_by_name.get(svc, {}).get("dependencies", []),
            "is_scaled_to_zero": svc in runtime.get("scaled_to_zero", []),
            "is_unhealthy": svc in runtime.get("unhealthy_deployments", []),
        }

    facts_json = json.dumps(facts, ensure_ascii=True, separators=(",", ":"))

    bundle = {
        "snapshot_path": str(snapshot_path),
        "cmdb_path": str(cmdb_path),
        "allowed_services": allowed_services,
        "counts": {
            "total_rows": len(rows),
            "metrics": len(metric_rows),
            "logs": len(log_rows),
            "telemetry_errors": len(error_rows),
        },
        "datasource_health": datasource_health,
        "cmdb_summary": cmdb_lines,
        "metric_summary": metric_lines,
        "log_summary": log_lines,
        "error_summary": error_lines,
        "dependency_hints": dependency_hints,
        "runtime_signals": runtime,
        "rca_facts": facts,
    }

    text = (
        "INCIDENT_CONTEXT_BUNDLE:\n"
        f"snapshot_path: {snapshot_path}\n"
        f"cmdb_path: {cmdb_path}\n"
        f"allowed_services: {allowed_services}\n"
        f"counts: {bundle['counts']}\n"
        f"datasource_health: {health_text}\n\n"
        "CMDB_SUMMARY:\n"
        + ("\n".join(cmdb_lines) if cmdb_lines else "none")
        + "\n\nMETRIC_ANOMALIES:\n"
        + ("\n".join(metric_lines) if metric_lines else "none")
        + "\n\nTOP_ERROR_LOG_SIGNATURES:\n"
        + ("\n".join(log_lines) if log_lines else "none")
        + "\n\nDEPENDENCY_HINTS:\n"
        + ("\n".join(dependency_hints) if dependency_hints else "none")
        + "\n\nK8S_DEPLOYMENT_STATE:\n"
        + ("\n".join(deployment_lines) if deployment_lines else "none")
        + "\n\nSCALED_TO_ZERO_SERVICES:\n"
        + ("\n".join(scaled_to_zero_lines) if scaled_to_zero_lines else "none")
        + "\n\nUNHEALTHY_DEPLOYMENTS:\n"
        + ("\n".join(unhealthy_lines) if unhealthy_lines else "none")
        + "\n\nCRASHLOOP_PODS:\n"
        + ("\n".join(crashloop_lines) if crashloop_lines else "none")
        + "\n\nRCA_FACTS_JSON:\n"
        + facts_json
        + "\n\nTELEMETRY_ERRORS:\n"
        + ("\n".join(error_lines) if error_lines else "none")
    )

    return bundle, text
