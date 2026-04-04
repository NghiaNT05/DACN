# Service Connection Failure

## Symptoms
- Pods report connection refused/timeout to other services
- Intermittent 5xx errors
- DNS resolution failures
- Network policies blocking traffic

## Common Causes

### 1. Service Misconfiguration
- Wrong port number
- Selector doesn't match pod labels
- Service in wrong namespace

### 2. Pod Not Ready
- Target pods failing readiness probes
- No endpoints available
- Deployment scaled to 0

### 3. Network Policy
- Ingress/egress rules blocking traffic
- Default deny policy

### 4. DNS Issues
- CoreDNS not healthy
- DNS cache stale
- Wrong service name

## Diagnostic Commands

```bash
# Check service endpoints
kubectl get endpoints <service-name> -n <namespace>

# Check service details
kubectl describe service <service-name> -n <namespace>

# Verify DNS resolution
kubectl run -it --rm debug --image=busybox -- nslookup <service-name>.<namespace>.svc.cluster.local

# Test connectivity
kubectl run -it --rm debug --image=busybox -- wget -qO- http://<service-name>:<port>

# Check network policies
kubectl get networkpolicies -n <namespace>

# Check pod labels match service selector
kubectl get pods -n <namespace> --show-labels | grep <app-label>
```

## Resolution Steps

1. **Verify endpoints exist** - Empty endpoints = no ready pods
2. **Check service selector** - Must match pod labels exactly
3. **Test DNS** - Ensure name resolves correctly
4. **Review network policies** - Allow required traffic
5. **Check target pod health** - Fix readiness issues

## Common Fixes

```yaml
# Ensure labels match
# Service selector
selector:
  app: myservice
  
# Pod labels (must match)
metadata:
  labels:
    app: myservice
```

```yaml
# Allow ingress from specific namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
spec:
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: frontend
```

## Related Signals
- `connection refused`
- `no endpoints available`
- `lookup failed`
- `i/o timeout`
