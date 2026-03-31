#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aiops.rag import ask_devops, infer_rca_with_context_bundle
from aiops.config import get_settings
from aiops.rca import build_incident_context_bundle


def main():
    settings = get_settings()
    while True:
        question = input("\nAsk DevOps (or rca:<incident>, exit): ").strip()
        if question == "exit":
            break
        if question.startswith("rca:"):
            incident_query = question.split("rca:", 1)[1].strip()
            _bundle, bundle_text = build_incident_context_bundle(
                settings.default_snapshot,
                settings.default_cmdb,
            )
            analysis, _raw_text = infer_rca_with_context_bundle(incident_query, bundle_text)
            print("\nAI RCA:")
            print(json.dumps(analysis, ensure_ascii=True, indent=2))
            continue
        print("\nAI:")
        print(ask_devops(question))


if __name__ == "__main__":
    main()
