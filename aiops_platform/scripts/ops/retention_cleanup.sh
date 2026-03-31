#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="${DATA_DIR:-$BASE_DIR/../aiops_data}"
KEEP_DAYS_TELEMETRY="${KEEP_DAYS_TELEMETRY:-7}"
KEEP_DAYS_REPORTS="${KEEP_DAYS_REPORTS:-30}"

echo "Cleaning telemetry files older than ${KEEP_DAYS_TELEMETRY} days in $DATA_DIR/telemetry"
find "$DATA_DIR/telemetry" -type f -name "*.jsonl" -mtime +"$KEEP_DAYS_TELEMETRY" -print -delete || true

echo "Cleaning reports older than ${KEEP_DAYS_REPORTS} days in $DATA_DIR/reports"
find "$DATA_DIR/reports" -type f -name "*.json" -mtime +"$KEEP_DAYS_REPORTS" -print -delete || true

echo "Retention cleanup completed"
