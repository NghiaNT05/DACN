# Shipping Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `shipping` |
| **Type** | backend |
| **Language** | Go |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-shipping` |
| **Memory Limit** | 20Mi |
| **CPU Limit** | Not set |

## Dependencies

- `quote`

## Environment Variables

| Variable | Value |
|----------|-------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `QUOTE_ADDR` | `http://quote:8080` |
| `SHIPPING_PORT` | `8080` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=shipping`
   - Check logs: `kubectl logs -l app=shipping --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=shipping`
   - Review traces in Jaeger
