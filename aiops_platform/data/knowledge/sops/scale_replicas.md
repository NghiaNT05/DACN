# SOP: Scale Deployment Replicas

## Purpose
Adjust the number of pod replicas to handle load changes or recover from capacity issues.

## Prerequisites
- kubectl access to cluster
- Appropriate RBAC permissions
- Understanding of resource capacity

## Risk Level
**LOW_RISK** - Reversible, but may impact capacity

## Procedure

### 1. Pre-checks
```bash
# Current replica count
kubectl get deployment <name> -n <namespace> -o jsonpath='{.spec.replicas}'

# Current pod status
kubectl get pods -n <namespace> -l app=<app-label>

# Check HPA if exists (may override manual scaling)
kubectl get hpa -n <namespace>

# Check available node capacity
kubectl describe nodes | grep -A5 "Allocated resources"
```

### 2. Execute Scale
```bash
# Scale to desired replicas
kubectl scale deployment/<name> -n <namespace> --replicas=<count>

# Alternative: patch deployment
kubectl patch deployment <name> -n <namespace> -p '{"spec":{"replicas":<count>}}'
```

### 3. Monitor Scaling
```bash
# Watch pods come up
kubectl get pods -n <namespace> -l app=<app-label> -w

# Check for scheduling issues
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i schedule
```

### 4. Verify Success
```bash
# Confirm replica count
kubectl get deployment <name> -n <namespace>

# Check all pods ready
kubectl get pods -n <namespace> -l app=<app-label> | grep -c Running
```

## Boundaries
- Maximum replicas: Check with team (usually ≤ 20 for standard apps)
- Minimum replicas: Usually ≥ 2 for production
- If HPA exists, scaling may be overridden

## Approval Requirements
- Scale up within limits: **YES** (low_risk)
- Scale down: **YES** (may impact availability)
- Scale to 0: **BLOCKED** (high_risk in production)

## Post-Action
- Monitor pod resource usage
- Check service latency metrics
- Document change in incident timeline
