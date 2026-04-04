# Quote Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `quote` |
| **Type** | backend |
| **Language** | PHP |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-quote` |
| **Memory Limit** | 40Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |
| `QUOTE_PORT` | `8080` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=quote`
   - Check logs: `kubectl logs -l app=quote --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=quote`
   - Review traces in Jaeger
