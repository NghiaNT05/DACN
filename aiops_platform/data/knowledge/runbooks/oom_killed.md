# OOMKilled Troubleshooting

## Symptoms
- Container terminated with reason `OOMKilled`
- Exit code 137
- Memory usage spikes before crash

## Common Causes

### 1. Memory Leak
- Application gradually consumes more memory
- Unbounded cache growth
- Connection pool not releasing resources

### 2. Insufficient Limits
- Memory limit too low for workload
- Spike in traffic causes memory spike

### 3. JVM Heap Misconfiguration
- Heap size larger than container limit
- Native memory not accounted for

### 4. Large Request Processing
- Single request loading large dataset
- Image/file processing without streaming

## Diagnostic Commands

```bash
# Check OOM events
kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Last State"

# Check memory limits
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].resources}'

# Monitor memory usage
kubectl top pod <pod-name> -n <namespace> --containers

# Check node memory pressure
kubectl describe node <node-name> | grep -A5 "Conditions"
```

## Resolution Steps

1. **Analyze memory pattern** - Is it gradual leak or sudden spike?
2. **Increase limits** - If workload legitimately needs more memory
3. **Add memory profiling** - Find leak source in application
4. **Tune JVM** - Set `-Xmx` to 70-80% of container limit
5. **Implement pagination** - Don't load large datasets at once

## Prevention

- Set memory requests = limits for guaranteed QoS
- Add memory monitoring alerts
- Use HPA with meOpenSearch Startup	mory metric
- Implement circuit breakers for memory-heavy operations

## Related Signals
- `terminated_reason=OOMKilled`
- `exit_code=137`
- `memory_pressure=true`
