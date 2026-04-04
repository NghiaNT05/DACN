# SOP: Restart Deployment

## Purpose
Safely restart all pods in a deployment to apply configuration changes or recover from issues.

## Prerequisites
- kubectl access to cluster
- Appropriate RBAC permissions
- Understanding of impact to service availability

## Risk Level
**LOW_RISK** - Reversible, rolling restart maintains availability

## Procedure

### 1. Pre-checks
```bash
# Verify deployment exists and current state
kubectl get deployment <name> -n <namespace>

# Check current replica count
kubectl get deployment <name> -n <namespace> -o jsonpath='{.spec.replicas}'

# Check rollout history
kubectl rollout history deployment/<name> -n <namespace>
```

### 2. Execute Restart
```bash
# Trigger rolling restart
kubectl rollout restart deployment/<name> -n <namespace>
```

### 3. Monitor Rollout
```bash
# Watch rollout progress
kubectl rollout status deployment/<name> -n <namespace>

# Check pod status
kubectl get pods -n <namespace> -l app=<app-label> -w
```

### 4. Verify Success
```bash
# Confirm all pods running
kubectl get pods -n <namespace> -l app=<app-label>

# Check no errors in new pods
kubectl logs deployment/<name> -n <namespace> --tail=50
```

### 5. Rollback if Needed
```bash
# If issues occur, rollback
kubectl rollout undo deployment/<name> -n <namespace>
```

## Approval Requirements
- Requires approval: **YES** (low_risk mutating action)
- Approver: On-call engineer or team lead
- Document: incident_id, justification

## Post-Action
- Monitor service metrics for 15 minutes
- Update incident timeline
- Close or escalate based on outcome
