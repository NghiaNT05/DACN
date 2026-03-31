import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aiops.ingestion import build_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build vector DB for AIOps RAG")
    parser.add_argument(
        "--source",
        action="append",
        choices=["docs", "cmdb", "telemetry", "runtime"],
        help="Data source to include. Can be passed multiple times.",
    )
    parser.add_argument("--fast", action="store_true", help="Quick mode: ingest CMDB + telemetry + runtime")
    parser.add_argument("--no-reset", action="store_true", help="Do not wipe existing vector DB")
    args = parser.parse_args()

    if args.fast:
        include_docs = False
        include_cmdb = True
        include_telemetry = True
        include_runtime = True
    elif args.source:
        include_docs = "docs" in args.source
        include_cmdb = "cmdb" in args.source
        include_telemetry = "telemetry" in args.source
        include_runtime = "runtime" in args.source
    else:
        include_docs = include_cmdb = include_telemetry = include_runtime = True

    result = build_index(
        include_docs=include_docs,
        include_cmdb=include_cmdb,
        include_telemetry=include_telemetry,
        include_runtime=include_runtime,
        reset_db=not args.no_reset,
    )
    print(result)
