import json
from urllib.request import urlopen


def _http_json(url, timeout=5):
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _check_prometheus(prom_url):
    try:
        payload = _http_json(f"{prom_url.rstrip('/')}/api/v1/query?query=up")
        ok = payload.get("status") == "success"
        return {"name": "prometheus", "ok": ok, "detail": "query up success" if ok else "query failed"}
    except Exception as exc:
        return {"name": "prometheus", "ok": False, "detail": str(exc)}


def _check_loki(loki_url):
    try:
        payload = _http_json(f"{loki_url.rstrip('/')}/loki/api/v1/labels")
        ok = payload.get("status") == "success"
        return {"name": "loki", "ok": ok, "detail": "labels query success" if ok else "labels query failed"}
    except Exception as exc:
        return {"name": "loki", "ok": False, "detail": str(exc)}


def _check_tempo(tempo_url):
    try:
        with urlopen(f"{tempo_url.rstrip('/')}/ready", timeout=5) as response:
            ok = response.status == 200
            return {"name": "tempo", "ok": ok, "detail": f"http {response.status}"}
    except Exception as exc:
        return {"name": "tempo", "ok": False, "detail": str(exc)}


def check_datasources(prometheus_url, loki_url, tempo_url=None):
    checks = [_check_prometheus(prometheus_url), _check_loki(loki_url)]
    if tempo_url:
        checks.append(_check_tempo(tempo_url))

    all_ok = all(item["ok"] for item in checks)
    return {
        "all_ok": all_ok,
        "checks": checks,
        "ok_count": sum(1 for item in checks if item["ok"]),
        "total_count": len(checks),
    }


def build_health_context(health):
    lines = [
        "DATASOURCE_HEALTH:",
        f"all_ok: {health['all_ok']}",
        f"ok_count: {health['ok_count']}/{health['total_count']}",
    ]
    for item in health["checks"]:
        lines.append(f"- {item['name']}: ok={item['ok']} detail={item['detail']}")
    return "\n".join(lines)
