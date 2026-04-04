#!/usr/bin/env python3
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_LOG_TAIL_LINES,
    DEFAULT_MAX_LOG_SIGNATURES,
    DEFAULT_MAX_DESCRIBE_SNIPPETS,
    run_ingestion_cycle,
    write_events_json,
    write_bundle,
    write_bundle_json,
)


def _severity_counts(events):
    return {
        "critical": sum(1 for e in events if e.get("severity") == "critical"),
        "high": sum(1 for e in events if e.get("severity") == "high"),
        "medium": sum(1 for e in events if e.get("severity") == "medium"),
        "low": sum(1 for e in events if e.get("severity") == "low"),
    }


def _run_single_cycle(
    *,
    namespace,
    output_path: Path,
    state_path,
    cooldown_seconds: int,
    include_k8s_events: bool,
    include_log_signatures: bool,
    log_tail_lines: int,
    max_log_signatures: int,
    include_describe_snippets: bool,
    max_describe_snippets: int,
    enable_schema_validation: bool,
    schema_path: Path,
    archive_dir,
    cycle_index: int,
    emit_bundle: bool,
    bundle_dir: Path,
):
    cycle_result = run_ingestion_cycle(
        namespace=namespace,
        state_path=state_path,
        cooldown_seconds=cooldown_seconds,
        include_k8s_events=include_k8s_events,
        include_log_signatures=include_log_signatures,
        log_tail_lines=log_tail_lines,
        max_log_signatures=max_log_signatures,
        include_describe_snippets=include_describe_snippets,
        max_describe_snippets=max_describe_snippets,
        enable_schema_validation=enable_schema_validation,
        schema_path=schema_path,
    )
    events = cycle_result["events"]

    write_events_json(output_path, events)

    archive_output = None
    if archive_dir is not None:
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_output = archive_dir / f"ingestion_cycle_{cycle_index:04d}_{ts}.json"
        write_events_json(archive_output, events)

    # Emit retrieval bundle if enabled
    bundle_txt_path = None
    bundle_json_path = None
    if emit_bundle and events:
        cycle_id = f"cycle_{cycle_index:04d}"
        bundle_txt_path = write_bundle(events, output_dir=bundle_dir, cycle_id=cycle_id)
        bundle_json_path = write_bundle_json(events, output_dir=bundle_dir, cycle_id=cycle_id)

    return {
        "status": "ok",
        "cycle": cycle_index,
        "namespace": namespace or "all",
        "base_event_count": cycle_result["base_event_count"],
        "enriched_event_count": cycle_result["enriched_event_count"],
        "schema_valid_event_count": cycle_result["schema_valid_event_count"],
        "schema_invalid_event_count": cycle_result["schema_invalid_event_count"],
        "schema_validation_enabled": cycle_result["schema_validation_enabled"],
        "schema_path": cycle_result["schema_path"],
        "schema_errors_preview": cycle_result["schema_errors_preview"],
        "event_count": cycle_result["emitted_event_count"],
        "suppressed_count": cycle_result["suppressed_event_count"],
        "output": str(output_path),
        "archive_output": str(archive_output) if archive_output is not None else "",
        "bundle_txt": str(bundle_txt_path) if bundle_txt_path else "",
        "bundle_json": str(bundle_json_path) if bundle_json_path else "",
        "cooldown_seconds": cooldown_seconds,
        "k8s_events_enabled": include_k8s_events,
        "log_signatures_enabled": include_log_signatures,
        "log_tail_lines": log_tail_lines,
        "max_log_signatures": max_log_signatures,
        "describe_snippets_enabled": include_describe_snippets,
        "max_describe_snippets": max_describe_snippets,
        "severity_counts": _severity_counts(events),
        "preview": events[:5],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect incident-like events from live Kubernetes runtime")
    parser.add_argument("--namespace", default="", help="Namespace scope. Empty means all namespaces")
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "incidents" / "ingestion_snapshot_v1.json"),
        help="Output path for collected incident events",
    )
    parser.add_argument(
        "--state",
        default=str(ROOT / "data" / "incidents" / "ingestion_state_v1.json"),
        help="State file for cross-cycle correlation and cooldown",
    )
    parser.add_argument(
        "--disable-correlation",
        action="store_true",
        help="Disable correlation/cooldown state handling",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=int,
        default=DEFAULT_COOLDOWN_SECONDS,
        help="Suppress repeated correlated incidents within this cooldown window",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of ingest cycles to run. Use 0 for infinite loop until Ctrl+C",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Delay between cycles when --cycles != 1",
    )
    parser.add_argument(
        "--archive-dir",
        default="",
        help="Optional directory to persist per-cycle snapshots",
    )
    parser.add_argument(
        "--disable-k8s-events",
        action="store_true",
        help="Disable ingestion from Kubernetes Events stream",
    )
    parser.add_argument(
        "--disable-log-signatures",
        action="store_true",
        help="Disable pod log-signature enrichment",
    )
    parser.add_argument(
        "--log-tail-lines",
        type=int,
        default=DEFAULT_LOG_TAIL_LINES,
        help="Tail lines used when extracting log signatures from pod logs",
    )
    parser.add_argument(
        "--max-log-signatures",
        type=int,
        default=DEFAULT_MAX_LOG_SIGNATURES,
        help="Maximum log signatures attached to one incident",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "data" / "schemas" / "incident_event.schema.json"),
        help="Schema file used to validate incident events",
    )
    parser.add_argument(
        "--disable-schema-validation",
        action="store_true",
        help="Disable JSON schema validation gate before writing output",
    )
    parser.add_argument(
        "--disable-describe-snippets",
        action="store_true",
        help="Disable describe-based diagnostics enrichment",
    )
    parser.add_argument(
        "--max-describe-snippets",
        type=int,
        default=DEFAULT_MAX_DESCRIBE_SNIPPETS,
        help="Maximum diagnostics snippets extracted from kubectl describe",
    )
    parser.add_argument(
        "--emit-bundle",
        action="store_true",
        help="Emit retrieval bundle files after each cycle",
    )
    parser.add_argument(
        "--bundle-dir",
        default=str(ROOT / "data" / "retrieval"),
        help="Directory for retrieval bundle output",
    )
    args = parser.parse_args()

    namespace = args.namespace.strip() or None
    output_path = Path(args.output)
    state_path = None
    if not args.disable_correlation:
        state_path = Path(args.state)

    cooldown_seconds = max(0, int(args.cooldown_seconds))
    include_k8s_events = not bool(args.disable_k8s_events)
    include_log_signatures = not bool(args.disable_log_signatures)
    log_tail_lines = max(20, int(args.log_tail_lines))
    max_log_signatures = max(1, int(args.max_log_signatures))
    include_describe_snippets = not bool(args.disable_describe_snippets)
    max_describe_snippets = max(1, int(args.max_describe_snippets))
    enable_schema_validation = not bool(args.disable_schema_validation)
    schema_path = Path(args.schema)
    total_cycles = max(0, int(args.cycles))
    interval_seconds = max(1, int(args.interval_seconds))
    archive_dir = Path(args.archive_dir) if args.archive_dir.strip() else None
    emit_bundle = bool(args.emit_bundle)
    bundle_dir = Path(args.bundle_dir)

    cycle_index = 0
    interrupted = False
    aggregate_base = 0
    aggregate_emitted = 0
    aggregate_suppressed = 0

    try:
        while True:
            cycle_index += 1
            summary = _run_single_cycle(
                namespace=namespace,
                output_path=output_path,
                state_path=state_path,
                cooldown_seconds=cooldown_seconds,
                include_k8s_events=include_k8s_events,
                include_log_signatures=include_log_signatures,
                log_tail_lines=log_tail_lines,
                max_log_signatures=max_log_signatures,
                include_describe_snippets=include_describe_snippets,
                max_describe_snippets=max_describe_snippets,
                enable_schema_validation=enable_schema_validation,
                schema_path=schema_path,
                archive_dir=archive_dir,
                cycle_index=cycle_index,
                emit_bundle=emit_bundle,
                bundle_dir=bundle_dir,
            )
            aggregate_base += int(summary["base_event_count"])
            aggregate_emitted += int(summary["event_count"])
            aggregate_suppressed += int(summary["suppressed_count"])

            print(json.dumps(summary, ensure_ascii=True, indent=2))

            if total_cycles > 0 and cycle_index >= total_cycles:
                break

            if total_cycles == 1:
                break

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        interrupted = True

    if cycle_index > 1 or total_cycles == 0 or interrupted:
        final_summary = {
            "status": "stopped" if interrupted else "ok",
            "namespace": namespace or "all",
            "cycles_run": cycle_index,
            "base_event_count_total": aggregate_base,
            "event_count_total": aggregate_emitted,
            "suppressed_count_total": aggregate_suppressed,
            "output": str(output_path),
            "correlation_enabled": state_path is not None,
            "cooldown_seconds": cooldown_seconds,
            "k8s_events_enabled": include_k8s_events,
            "log_signatures_enabled": include_log_signatures,
            "describe_snippets_enabled": include_describe_snippets,
            "schema_validation_enabled": enable_schema_validation,
            "schema_path": str(schema_path),
            "interval_seconds": interval_seconds,
        }
        print(json.dumps(final_summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
