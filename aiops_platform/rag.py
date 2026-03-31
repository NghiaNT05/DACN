import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aiops.config import get_settings
from aiops.rag import ask_devops, infer_rca_with_context_bundle
from aiops.rca import build_incident_context_bundle


if __name__ == "__main__":
    settings = get_settings()

    while True:
        q = input("\nAsk DevOps (or 'rca:<incident>'): ").strip()
        if q == "exit":
            break
        if q.startswith("rca:"):
            incident_question = q.split("rca:", 1)[1].strip()
            _bundle, bundle_text = build_incident_context_bundle(
                settings.default_snapshot,
                settings.default_cmdb,
            )
            answer, _raw = infer_rca_with_context_bundle(incident_question, bundle_text)
            print("\nAI RCA:")
            print(answer)
            continue

        print("\nAI:")
        print(ask_devops(q))
