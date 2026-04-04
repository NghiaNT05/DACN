# Valkey Cart Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `valkey-cart` |
| **Type** | cache |
| **Language** | Redis/Valkey |
| **Port** | 6379 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `valkey/valkey:8.1.3-alpine` |
| **Memory Limit** | 20Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=valkey-cart`
   - Check logs: `kubectl logs -l app=valkey-cart --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=valkey-cart`
   - Review traces in Jaeger
