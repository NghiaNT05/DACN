# Ad Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `ad` |
| **Type** | backend |
| **Language** | Java |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-ad` |
| **Memory Limit** | 300Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `AD_PORT` | `8080` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=ad`
   - Check logs: `kubectl logs -l app=ad --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=ad`
   - Review traces in Jaeger
