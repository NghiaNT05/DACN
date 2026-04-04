#!/usr/bin/env python3
"""CLI runner for retention cleanup."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.retention import (
    DEFAULT_STATE_RETENTION_DAYS,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_BUNDLE_RETENTION_DAYS,
    run_full_retention,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run retention cleanup for ingestion state, history, and bundles"
    )
    parser.add_argument(
        "--state-path",
        default=str(ROOT / "data" / "incidents" / "ingestion_state_v1.json"),
        help="Path to ingestion state file",
    )
    parser.add_argument(
        "--history-dir",
        default=str(ROOT / "data" / "incidents" / "history"),
        help="Path to history directory",
    )
    parser.add_argument(
        "--bundle-dir",
        default=str(ROOT / "data" / "retrieval"),
        help="Path to retrieval bundle directory",
    )
    parser.add_argument(
        "--state-retention-days",
        type=int,
        default=DEFAULT_STATE_RETENTION_DAYS,
        help=f"Days to retain state entries (default: {DEFAULT_STATE_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--history-retention-days",
        type=int,
        default=DEFAULT_HISTORY_RETENTION_DAYS,
        help=f"Days to retain history files (default: {DEFAULT_HISTORY_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--bundle-retention-days",
        type=int,
        default=DEFAULT_BUNDLE_RETENTION_DAYS,
        help=f"Days to retain bundle files (default: {DEFAULT_BUNDLE_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    
    args = parser.parse_args()
    
    results = run_full_retention(
        state_path=Path(args.state_path),
        history_dir=Path(args.history_dir),
        bundle_dir=Path(args.bundle_dir),
        state_retention_days=args.state_retention_days,
        history_retention_days=args.history_retention_days,
        bundle_retention_days=args.bundle_retention_days,
        dry_run=args.dry_run,
    )
    
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
