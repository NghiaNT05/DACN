#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aiops.config import get_settings
from aiops.rca import build_incident_report, save_report_json, build_incident_context_bundle
from aiops.health import check_datasources


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run incident RCA and write report")
    parser.add_argument("--incident", default="checkout failure spike")
    parser.add_argument("--snapshot", default=str(settings.default_snapshot))
    parser.add_argument("--cmdb", default=str(settings.default_cmdb))
    parser.add_argument("--output", default=str(settings.reports_dir / "latest_incident_report.json"))
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--loki-url", default="http://localhost:3100")
    parser.add_argument("--tempo-url", default="")
    parser.add_argument("--health-gate", action="store_true")
    parser.add_argument("--strict-health", action="store_true")
    args = parser.parse_args()

    health = None
    if args.health_gate:
        health = check_datasources(
            prometheus_url=args.prometheus_url,
            loki_url=args.loki_url,
            tempo_url=args.tempo_url or None,
        )
        if args.strict_health and not health["all_ok"]:
            print("Datasource health gate failed in strict mode.")
            print(health)
            raise SystemExit(2)

    from aiops.rag import infer_rca_with_context_bundle

    bundle, bundle_text = build_incident_context_bundle(
        snapshot_path=args.snapshot,
        cmdb_path=args.cmdb,
        datasource_health=health,
    )
    analysis, llm_text = infer_rca_with_context_bundle(args.incident, bundle_text)

    analysis["rca_source"] = "graph-rag-llm"
    analysis["prompt_version"] = "rca-graph-rag-v1"
    analysis["context_counts"] = bundle.get("counts", {})
    if health is not None:
        analysis["datasource_health"] = health

    report = build_incident_report(args.incident, analysis, llm_text, args.snapshot, args.cmdb)
    save_report_json(report, args.output)

    print("=== INCIDENT SUMMARY ===")
    print(analysis)
    print("\n=== RCA REPORT ===")
    print(llm_text)
    print(f"\nSaved report JSON to: {args.output}")


if __name__ == "__main__":
    main()
