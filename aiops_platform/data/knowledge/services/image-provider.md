# Image Provider Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `image-provider` |
| **Type** | backend |
| **Language** | Unknown |
| **Port** | 8081 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-image-provider` |
| **Memory Limit** | 50Mi |
| **CPU Limit** | Not set |

## Dependencies

- `$(OTEL_COLLECTOR_NAME)`

## Environment Variables

| Variable | Value |
|----------|-------|
| `IMAGE_PROVIDER_PORT` | `8081` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=image-provider`
   - Check logs: `kubectl logs -l app=image-provider --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=image-provider`
   - Review traces in Jaeger
