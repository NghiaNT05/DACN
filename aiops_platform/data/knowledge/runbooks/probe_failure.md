# Readiness/Liveness Probe Failure

## Symptoms
- Pod marked as not ready
- Traffic not routed to pod
- Container killed due to liveness failure
- Events show probe failures

## Types of Probes

| Probe | Purpose | Failure Action |
|-------|---------|----------------|
| Liveness | Is container alive? | Kill and restart |
| Readiness | Can container serve traffic? | Remove from service |
| Startup | Has container started? | Block other probes |

## Common Causes

### 1. Slow Startup
- Application needs more time to initialize
- Database migrations running
- Cache warming

### 2. Probe Misconfiguration
- Wrong port or path
- Too aggressive timeouts
- HTTP probe on non-HTTP endpoint

### 3. Resource Starvation
- CPU throttling delays response
- Memory pressure causes GC pauses

### 4. Dependency Issues
- Health endpoint checks downstream services
- Cascading failures

## Diagnostic Commands

```bash
# Check probe configuration
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].livenessProbe}'
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].readinessProbe}'

# Check probe events
kubectl describe pod <pod-name> -n <namespace> | grep -i probe

# Test probe endpoint manually
kubectl exec <pod-name> -n <namespace> -- curl -s localhost:<port>/<path>

# Check container logs during probe failures
kubectl logs <pod-name> -n <namespace> --timestamps | grep -E "(health|ready|probe)"
```

## Resolution Steps

1. **Increase timeouts** - Give app more time to respond
2. **Add initialDelaySeconds** - Wait for startup before probing
3. **Use startup probe** - For slow-starting containers
4. **Simplify health check** - Don't check dependencies in liveness
5. **Increase resources** - Ensure enough CPU/memory

## Recommended Configuration

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

## Related Signals
- `k8s_event_reason=Unhealthy`
- `readiness probe failed`
- `liveness probe failed`
