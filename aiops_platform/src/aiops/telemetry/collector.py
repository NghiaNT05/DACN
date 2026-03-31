import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen


def http_json(url: str):
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def query_prometheus(prometheus_url: str, query: str):
    payload = http_json(f"{prometheus_url.rstrip('/')}/api/v1/query?query={quote_plus(query)}")
    if payload.get("status") != "success":
        return []
    return payload.get("data", {}).get("result", [])


def query_loki_range(loki_url: str, query: str, start_ns: int, end_ns: int, limit: int):
    url = (
        f"{loki_url.rstrip('/')}/loki/api/v1/query_range"
        f"?query={quote_plus(query)}&start={start_ns}&end={end_ns}&limit={limit}&direction=BACKWARD"
    )
    payload = http_json(url)
    if payload.get("status") != "success":
        return []
    return payload.get("data", {}).get("result", [])


def build_prom_queries(namespace: str):
    return {
        "pod_cpu_5m": (
            "sum(rate(container_cpu_usage_seconds_total"
            f"{{namespace=\"{namespace}\",container!=\"\",pod!=\"\"}}[5m])) by (pod)"
        ),
        "pod_memory_workingset": (
            "sum(container_memory_working_set_bytes"
            f"{{namespace=\"{namespace}\",container!=\"\",pod!=\"\"}}) by (pod)"
        ),
        "pod_restarts": (
            "sum(kube_pod_container_status_restarts_total"
            f"{{namespace=\"{namespace}\"}}) by (pod)"
        ),
        "service_latency_p95_ms": (
            "histogram_quantile(0.95, "
            "sum(rate(istio_request_duration_milliseconds_bucket"
            f"{{reporter=\"destination\",destination_workload_namespace=\"{namespace}\"}}[5m])) by (le, destination_workload))"
        ),
        "service_error_rate": (
            "sum(rate(istio_requests_total"
            f"{{destination_workload_namespace=\"{namespace}\",response_code=~\"5..\"}}[5m])) by (destination_workload)"
            " / clamp_min(sum(rate(istio_requests_total"
            f"{{destination_workload_namespace=\"{namespace}\"}}[5m])) by (destination_workload), 0.001)"
        ),
        "service_latency_p95_ms_http": (
            "1000 * histogram_quantile(0.95, "
            "sum(rate(http_server_requests_seconds_bucket"
            f"{{namespace=\"{namespace}\"}}[5m])) by (le, service, app, job))"
        ),
        "service_error_rate_http": (
            "sum(rate(http_server_requests_seconds_count"
            f"{{namespace=\"{namespace}\",status=~\"5..\"}}[5m])) by (service, app, job)"
            " / clamp_min(sum(rate(http_server_requests_seconds_count"
            f"{{namespace=\"{namespace}\"}}[5m])) by (service, app, job), 0.001)"
        ),
    }


def collect_telemetry(prometheus_url: str, loki_url: str, namespace: str, loki_window_minutes: int, loki_limit: int):
    docs = []
    now = datetime.now(timezone.utc)

    for metric_name, query in build_prom_queries(namespace).items():
        try:
            results = query_prometheus(prometheus_url, query)
        except Exception as exc:
            docs.append({
                "type": "telemetry_error",
                "source": "prometheus",
                "timestamp": now.isoformat(),
                "metric_name": metric_name,
                "content": f"Failed to fetch metric {metric_name}: {exc}",
                "metadata": {"query": query},
            })
            continue

        for row in results:
            docs.append({
                "type": "metric",
                "source": "prometheus",
                "timestamp": now.isoformat(),
                "metric_name": metric_name,
                "content": json.dumps(row, ensure_ascii=True),
                "metadata": {"query": query},
            })

    end_ns = int(now.timestamp() * 1_000_000_000)
    start_ns = int((now - timedelta(minutes=loki_window_minutes)).timestamp() * 1_000_000_000)
    loki_query = f'{{namespace="{namespace}"}} |= "error"'

    try:
        streams = query_loki_range(loki_url, loki_query, start_ns, end_ns, loki_limit)
    except Exception as exc:
        docs.append({
            "type": "telemetry_error",
            "source": "loki",
            "timestamp": now.isoformat(),
            "content": f"Failed to fetch logs: {exc}",
            "metadata": {"query": loki_query},
        })
        return docs

    for stream in streams:
        labels = stream.get("stream", {})
        for ts_ns, line in stream.get("values", []):
            ts = datetime.fromtimestamp(int(ts_ns) / 1_000_000_000, tz=timezone.utc).isoformat()
            docs.append({
                "type": "log",
                "source": "loki",
                "timestamp": ts,
                "content": line,
                "metadata": labels,
            })

    return docs


def write_jsonl(records, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
