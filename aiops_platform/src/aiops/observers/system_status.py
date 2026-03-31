import subprocess
from collections import Counter
import json


def _run_cmd(command, timeout=8):
    try:
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()
    except Exception:
        return ""


def collect_system_status():
    clusters_raw = _run_cmd("kubectl config get-clusters")
    current_context = _run_cmd("kubectl config current-context")
    nodes_raw = _run_cmd("kubectl get nodes --no-headers")
    pods_raw = _run_cmd("kubectl get pod -A --no-headers")
    top_nodes_raw = _run_cmd("kubectl top nodes --no-headers")
    host_mem_raw = _run_cmd("free -m")

    clusters = []
    for line in clusters_raw.splitlines():
        line = line.strip()
        if line and not line.startswith("NAME"):
            clusters.append(line)

    ns_counter = Counter()
    running_pods = 0
    total_pods = 0
    for line in pods_raw.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        total_pods += 1
        ns_counter[parts[0]] += 1
        if parts[3].lower() == "running":
            running_pods += 1

    return {
        "clusters": clusters,
        "cluster_count": len(clusters),
        "current_context": current_context or "unknown",
        "node_count": len([line for line in nodes_raw.splitlines() if line.strip()]),
        "total_pods": total_pods,
        "running_pods": running_pods,
        "pods_by_namespace": dict(ns_counter),
        "node_top": top_nodes_raw,
        "host_memory": host_mem_raw,
    }


def collect_workload_signals(namespace="default"):
    deployments_raw = _run_cmd(f"kubectl get deployment -n {namespace} -o json", timeout=10)
    pods_raw = _run_cmd(f"kubectl get pod -n {namespace} -o json", timeout=10)

    deployments = []
    scaled_to_zero = []
    unhealthy = []

    if deployments_raw:
        try:
            data = json.loads(deployments_raw)
            for item in data.get("items", []):
                name = item.get("metadata", {}).get("name", "unknown")
                spec_replicas = int(item.get("spec", {}).get("replicas", 0) or 0)
                status = item.get("status", {})
                ready = int(status.get("readyReplicas", 0) or 0)
                available = int(status.get("availableReplicas", 0) or 0)
                unavailable = int(status.get("unavailableReplicas", 0) or 0)
                deployments.append(
                    {
                        "name": name,
                        "desired": spec_replicas,
                        "ready": ready,
                        "available": available,
                        "unavailable": unavailable,
                    }
                )
                if spec_replicas == 0:
                    scaled_to_zero.append(name)
                elif ready < spec_replicas:
                    unhealthy.append(name)
        except json.JSONDecodeError:
            pass

    crashloop_pods = []
    if pods_raw:
        try:
            data = json.loads(pods_raw)
            for item in data.get("items", []):
                pod_name = item.get("metadata", {}).get("name", "unknown")
                for cs in item.get("status", {}).get("containerStatuses", []):
                    waiting = cs.get("state", {}).get("waiting", {})
                    reason = waiting.get("reason", "")
                    if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                        crashloop_pods.append({"pod": pod_name, "reason": reason})
                        break
        except json.JSONDecodeError:
            pass

    return {
        "namespace": namespace,
        "deployments": deployments,
        "scaled_to_zero": sorted(scaled_to_zero),
        "unhealthy_deployments": sorted(set(unhealthy)),
        "crashloop_pods": crashloop_pods,
    }


def build_system_context_text():
    status = collect_system_status()
    lines = [
        "LIVE_SYSTEM_CONTEXT:",
        f"cluster_count: {status['cluster_count']}",
        f"clusters: {', '.join(status['clusters']) if status['clusters'] else 'unknown'}",
        f"current_context: {status['current_context']}",
        f"node_count: {status['node_count']}",
        f"total_pods: {status['total_pods']}",
        f"running_pods: {status['running_pods']}",
        f"pods_by_namespace: {status['pods_by_namespace']}",
        "node_top:",
        status["node_top"] or "unavailable",
        "host_memory:",
        status["host_memory"] or "unavailable",
    ]
    return "\n".join(lines)
