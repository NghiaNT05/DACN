"""Kubectl command execution utilities."""

import json
import subprocess
from typing import Any, Dict, List

KUBECTL_TIMEOUT_SECONDS = 25


def run_kubectl_json(args: List[str]) -> Dict[str, Any]:
    """Run kubectl command and return JSON output."""
    cmd = ["kubectl", *args, "-o", "json"]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=KUBECTL_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"kubectl command failed: {' '.join(cmd)}\n{completed.stderr.strip()}")
    payload = json.loads(completed.stdout or "{}")
    if not isinstance(payload, dict):
        raise RuntimeError("kubectl output is not a JSON object")
    return payload


def run_kubectl_text(args: List[str]) -> str:
    """Run kubectl command and return text output."""
    cmd = ["kubectl", *args]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=KUBECTL_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"kubectl command failed: {' '.join(cmd)}\n{completed.stderr.strip()}")
    return completed.stdout or ""
