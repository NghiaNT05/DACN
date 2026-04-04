# Cart Service Troubleshooting

## Service Info
- **Name**: cart
- **Namespace**: default
- **Image**: ghcr.io/open-telemetry/demo:2.1.3-cart
- **Language**: .NET
- **Dependencies**: valkey-cart (Redis)

## Symptoms

### Cart Not Persisting
- Items disappear after adding
- Cart empty on page refresh
- gRPC errors in checkout

### Connection Timeouts
- Slow cart operations
- Frontend showing loading spinner
- 504 Gateway Timeout

## Common Causes

### 1. Valkey-Cart Down
```bash
# Check valkey-cart status
kubectl get pod -l opentelemetry.io/name=valkey-cart -n default

# Check valkey logs
kubectl logs -l opentelemetry.io/name=valkey-cart -n default --tail=50
```

### 2. Network Policy Blocking
```bash
# Test connectivity from cart to valkey
kubectl exec -it deploy/cart -n default -- nc -zv valkey-cart 6379
```

### 3. Memory Pressure on Valkey
```bash
# Check memory usage
kubectl top pod -l opentelemetry.io/name=valkey-cart -n default

# Check Redis INFO
kubectl exec -it deploy/valkey-cart -n default -- redis-cli INFO memory
```

## Diagnostic Commands

```bash
# Cart pod status
kubectl describe pod -l opentelemetry.io/name=cart -n default

# Cart logs
kubectl logs -l opentelemetry.io/name=cart -n default --tail=100

# Check endpoints
kubectl get endpoints cart -n default

# Test gRPC health
kubectl exec -it deploy/cart -n default -- grpc_health_probe -addr=:8080
```

## Resolution Steps

### If Valkey-Cart is down
```bash
kubectl rollout restart deployment/valkey-cart -n default
```

### If Cart pod is unhealthy
```bash
kubectl rollout restart deployment/cart -n default
```

### If memory issue
```bash
# Scale up or increase limits
kubectl patch deployment valkey-cart -n default -p '{"spec":{"template":{"spec":{"containers":[{"name":"valkey-cart","resources":{"limits":{"memory":"512Mi"}}}]}}}}'
```

## Related Signals
- `waiting_reason=CrashLoopBackOff` on cart pod
- `k8s_event_reason=Unhealthy` 
- `connection_refused` in cart logs
- `timeout` errors from frontend

## Upstream/Downstream Impact
- **Upstream**: frontend cannot add items to cart
- **Downstream**: checkout will fail if cart empty
