# Metrics Server Readiness Failure

## Incident Summary
- **Date**: 2026-04-02
- **Duration**: Intermittent during cluster restart
- **Severity**: Medium
- **Services Affected**: metrics-server (kube-system)

## What Happened

After minikube restart, metrics-server showed Warning:
```
Readiness probe failed: HTTP probe failed with statuscode: 500
```

### Timeline
1. 17:24:00 - Minikube started
2. 17:24:15 - metrics-server pod started
3. 17:24:20 - Readiness probe failed (500)
4. 17:24:38 - Warning event logged
5. 17:25:00 - metrics-server became ready

## Root Cause

Metrics server starts before kubelet metrics API is fully available:
1. metrics-server queries kubelet on each node
2. During startup, kubelet metrics endpoint returns 500
3. metrics-server readiness fails until all kubelets ready

## Impact

### During Incident
- `kubectl top` commands fail
- HPA (Horizontal Pod Autoscaler) cannot make scaling decisions
- No metrics in Prometheus/Grafana

### After Recovery
- All metrics collection resumed
- No data loss (metrics are point-in-time)

## Resolution

**Automatic recovery** - no manual intervention needed.

If persists longer than 5 minutes:
```bash
kubectl rollout restart deployment/metrics-server -n kube-system
```

## Lessons Learned

### What Went Well
- System self-healed
- Clear error message

### What Could Be Improved
- Add dependency check before metrics-server starts
- Consider using Prometheus Adapter as alternative

## Action Items

| Action | Owner | Status |
|--------|-------|--------|
| Document startup dependency | Platform Team | Done |
| Evaluate Prometheus Adapter | SRE Team | Backlog |
| Add alert for prolonged metrics failure | SRE Team | Backlog |

## Preventive Measures

1. **For HPA users**: Set `behavior.scaleDown.stabilizationWindowSeconds` to handle brief metrics gaps
2. **For monitoring**: Use Prometheus for long-term metrics, metrics-server for kubectl/HPA only

## Related Incidents
- Typical after any cluster restart
- Not related to application issues

## Detection
- Kubernetes Warning events
- `kubectl top nodes` returns error
