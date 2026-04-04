# Resource Pressure Troubleshooting

## Symptoms
- Pods pending due to insufficient resources
- Node shows memory/CPU pressure
- Evictions occurring
- Scheduling failures

## Types of Resource Pressure

| Condition | Meaning | Impact |
|-----------|---------|--------|
| MemoryPressure | Node low on memory | Evictions triggered |
| DiskPressure | Node low on disk | Evictions, image GC |
| PIDPressure | Too many processes | Fork failures |

## Common Causes

### 1. Overcommitment
- Sum of requests exceeds node capacity
- Too many pods scheduled

### 2. Resource Leaks
- Container memory leak
- Log files filling disk
- Orphaned volumes

### 3. Noisy Neighbor
- One pod consuming disproportionate resources
- No limits set

### 4. Insufficient Cluster Capacity
- Need more nodes
- Wrong instance type

## Diagnostic Commands

```bash
# Check node conditions
kubectl describe node <node-name> | grep -A10 "Conditions"

# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods -n <namespace> --sort-by=memory

# Find resource hogs
kubectl top pods -A --sort-by=cpu | head -20

# Check pending pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check requests vs limits
kubectl describe node <node-name> | grep -A20 "Allocated resources"
```

## Resolution Steps

1. **Identify pressure source** - Which resource is constrained?
2. **Find top consumers** - Use kubectl top to identify hogs
3. **Set appropriate limits** - Prevent runaway consumption
4. **Add more nodes** - If legitimate demand exceeds capacity
5. **Enable pod priority** - Ensure critical workloads get resources

## Prevention

```yaml
# Set resource requests and limits
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

```yaml
# Use PodDisruptionBudget
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

## Related Signals
- `FailedScheduling`
- `Evicted`
- `OutOfcpu`
- `OutOfmemory`
