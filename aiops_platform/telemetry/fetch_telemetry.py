import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aiops.config import get_settings
from aiops.telemetry import collect_telemetry, write_jsonl


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Fetch Prometheus and Loki telemetry snapshots for RAG ingestion")
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--loki-url", default="http://localhost:3100")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--loki-window-minutes", type=int, default=20)
    parser.add_argument("--loki-limit", type=int, default=400)
    parser.add_argument("--output", default=str(settings.default_snapshot))
    args = parser.parse_args()

    records = collect_telemetry(
        prometheus_url=args.prometheus_url,
        loki_url=args.loki_url,
        namespace=args.namespace,
        loki_window_minutes=args.loki_window_minutes,
        loki_limit=args.loki_limit,
    )

    output_path = Path(args.output).resolve()
    write_jsonl(records, output_path)
    print(f"Saved {len(records)} records to {output_path}")


if __name__ == "__main__":
    main()
