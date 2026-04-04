# ImagePullBackOff Troubleshooting

## Symptoms
- Pod status shows `ImagePullBackOff` or `ErrImagePull`
- Container never starts
- Events show image pull failures

## Common Causes

### 1. Image Not Found
- Typo in image name or tag
- Image deleted from registry
- Tag doesn't exist (e.g., `latest` removed)

### 2. Authentication Failed
- Missing imagePullSecrets
- Expired credentials
- Wrong registry URL

### 3. Network Issues
- Registry unreachable
- Proxy not configured
- DNS resolution failure

### 4. Rate Limiting
- Docker Hub pull limit exceeded
- Registry throttling requests

## Diagnostic Commands

```bash
# Check pull error details
kubectl describe pod <pod-name> -n <namespace> | grep -A10 "Events"

# Verify image exists
docker pull <image:tag>

# Check imagePullSecrets
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.imagePullSecrets}'

# Verify secret exists
kubectl get secret <secret-name> -n <namespace>

# Test registry authentication
kubectl create secret docker-registry test-secret \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<pass> \
  --dry-run=client -o yaml
```

## Resolution Steps

1. **Verify image name** - Check for typos, correct tag
2. **Check registry access** - Can you pull manually?
3. **Create/update imagePullSecrets** - Ensure credentials are valid
4. **Check network policies** - Allow egress to registry
5. **Use private registry mirror** - Avoid rate limits

## Common Fixes

```yaml
# Add imagePullSecrets to deployment
spec:
  template:
    spec:
      imagePullSecrets:
        - name: registry-credentials
```

```bash
# Create registry secret
kubectl create secret docker-registry registry-credentials \
  --docker-server=<registry-url> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n <namespace>
```

## Related Signals
- `waiting_reason=ImagePullBackOff`
- `waiting_reason=ErrImagePull`
- `k8s_event_reason=Failed`
