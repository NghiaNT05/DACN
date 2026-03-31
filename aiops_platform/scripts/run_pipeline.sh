#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$BASE_DIR/../rag_env/bin/python3}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

PROM_URL="${PROM_URL:-http://localhost:9090}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
NAMESPACE="${NAMESPACE:-default}"
INCIDENT="${INCIDENT:-checkout failure spike}"
FAST_MODE="${FAST_MODE:-1}"
HEALTH_GATE="${HEALTH_GATE:-1}"
STRICT_HEALTH="${STRICT_HEALTH:-0}"
TEMPO_URL="${TEMPO_URL:-}"

cd "$BASE_DIR"

if [[ "$HEALTH_GATE" == "1" ]]; then
  echo "[0/4] Datasource health gate"
  "$PYTHON_BIN" - <<'PY'
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from aiops.health import check_datasources, build_health_context

health = check_datasources(
    prometheus_url=os.getenv('PROM_URL', 'http://localhost:9090'),
    loki_url=os.getenv('LOKI_URL', 'http://localhost:3100'),
    tempo_url=os.getenv('TEMPO_URL') or None,
)
print(build_health_context(health))

strict = os.getenv('STRICT_HEALTH', '0') == '1'
if strict and not health['all_ok']:
    raise SystemExit(2)
PY
fi

echo "[1/4] Collect telemetry"
"$PYTHON_BIN" - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from aiops.telemetry import collect_telemetry, write_jsonl
from aiops.config import get_settings
import os

s = get_settings()
records = collect_telemetry(
    prometheus_url=os.getenv('PROM_URL', 'http://localhost:9090'),
    loki_url=os.getenv('LOKI_URL', 'http://localhost:3100'),
    namespace=os.getenv('NAMESPACE', 'default'),
    loki_window_minutes=10,
    loki_limit=500,
)
output = s.telemetry_dir / 'telemetry_snapshot.jsonl'
write_jsonl(records, output)
print(f"Saved {len(records)} records to {output}")
PY

echo "[2/4] Build vector index"
if [[ "$FAST_MODE" == "1" ]]; then
  "$PYTHON_BIN" - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from aiops.ingestion import build_index
print(build_index(include_docs=False, include_cmdb=True, include_telemetry=True, reset_db=True))
PY
else
  "$PYTHON_BIN" - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from aiops.ingestion import build_index
print(build_index(include_docs=True, include_cmdb=True, include_telemetry=True, reset_db=True))
PY
fi

echo "[3/4] RCA"
CMD=("$PYTHON_BIN" scripts/run_incident_rca.py --incident "$INCIDENT" --prometheus-url "$PROM_URL" --loki-url "$LOKI_URL")
if [[ -n "$TEMPO_URL" ]]; then
  CMD+=(--tempo-url "$TEMPO_URL")
fi
if [[ "$HEALTH_GATE" == "1" ]]; then
  CMD+=(--health-gate)
fi
if [[ "$STRICT_HEALTH" == "1" ]]; then
  CMD+=(--strict-health)
fi
"${CMD[@]}"

echo "[4/4] Done"
