# Email Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `email` |
| **Type** | backend |
| **Language** | Ruby |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-email` |
| **Memory Limit** | 100Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `EMAIL_PORT` | `8080` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=email`
   - Check logs: `kubectl logs -l app=email --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=email`
   - Review traces in Jaeger
