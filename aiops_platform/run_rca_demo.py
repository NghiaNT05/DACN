#!/usr/bin/env python3
import runpy
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "scripts" / "run_incident_rca.py"
runpy.run_path(str(SCRIPT), run_name="__main__")
