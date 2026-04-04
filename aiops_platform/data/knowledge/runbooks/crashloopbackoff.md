# CrashLoopBackOff Troubleshooting

## Symptoms
- Pod status shows `CrashLoopBackOff`
- Container restarts repeatedly
- Exponential backoff delay between restarts

## Common Causes

### 1. Application Error
- Uncaught exception during startup
- Missing required environment variables
- Configuration file syntax error

### 2. Resource Limits
- OOMKilled due to memory limit
- CPU throttling preventing startup within probe timeout

### 3. Dependency Failure  
- Cannot connect to required database
- Required service not available
- Secret or ConfigMap not mounted

### 4. Image Issues
- Entrypoint/CMD misconfigured
- Missing binary or library
- Wrong architecture image

## Diagnostic Commands

```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check container logs (including previous crash)
kubectl logs <pod-name> -n <namespace> --previous

# Check resource usage
kubectl top pod <pod-name> -n <namespace>

# Check events timeline
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep <pod-name>
```

## Resolution Steps

1. **Check logs first** - Most crashes leave error messages
2. **Verify environment** - Ensure all required env vars and secrets exist
3. **Check resource limits** - Increase if OOMKilled
4. **Verify dependencies** - Ensure upstream services are healthy
5. **Test image locally** - Run `docker run` to verify image works

## Related Signals
- `restart_count > 3`
- `waiting_reason=CrashLoopBackOff`
- `terminated_reason=Error`
