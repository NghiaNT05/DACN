# SOP: Collect Diagnostic Information

## Purpose
Gather comprehensive diagnostic data for incident analysis without making changes.

## Prerequisites
- kubectl access to cluster
- Read permissions on target namespace

## Risk Level
**SAFE_READ_ONLY** - No changes made, auto-execution allowed

## Procedure

### 1. Pod Status Collection
```bash
# Get all pods in namespace
kubectl get pods -n <namespace> -o wide

# Get pod details
kubectl describe pod <pod-name> -n <namespace>

# Get pod YAML
kubectl get pod <pod-name> -n <namespace> -o yaml
```

### 2. Log Collection
```bash
# Current container logs
kubectl logs <pod-name> -n <namespace> --tail=500

# Previous container logs (if crashed)
kubectl logs <pod-name> -n <namespace> --previous --tail=500

# All containers in pod
kubectl logs <pod-name> -n <namespace> --all-containers=true --tail=200
```

### 3. Event Collection
```bash
# Recent events in namespace
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Events for specific pod
kubectl get events -n <namespace> --field-selector involvedObject.name=<pod-name>
```

### 4. Resource Usage
```bash
# Pod resource usage
kubectl top pods -n <namespace>

# Node resource usage
kubectl top nodes

# Detailed resource allocation
kubectl describe node <node-name> | grep -A20 "Allocated resources"
```

### 5. Service & Networking
```bash
# Service endpoints
kubectl get endpoints -n <namespace>

# Service details
kubectl describe service <service-name> -n <namespace>

# Network policies
kubectl get networkpolicies -n <namespace>
```

### 6. Configuration
```bash
# ConfigMaps
kubectl get configmaps -n <namespace>

# Secrets (names only, not values)
kubectl get secrets -n <namespace>

# Environment variables in pod
kubectl exec <pod-name> -n <namespace> -- env
```

## Output Format
Collect all outputs and attach to incident record with timestamp.

## Approval Requirements
- **NO** - All commands are read-only
