# Recommendation Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `recommendation` |
| **Type** | backend |
| **Language** | Python |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-recommendation` |
| **Memory Limit** | 500Mi |
| **CPU Limit** | Not set |

## Dependencies

- `product-catalog`

## Environment Variables

| Variable | Value |
|----------|-------|
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `PRODUCT_CATALOG_ADDR` | `product-catalog:8080` |
| `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` | `python` |
| `RECOMMENDATION_PORT` | `8080` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=recommendation`
   - Check logs: `kubectl logs -l app=recommendation --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=recommendation`
   - Review traces in Jaeger
