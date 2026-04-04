# Product Catalog Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `product-catalog` |
| **Type** | backend |
| **Language** | Go |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-product-catalog` |
| **Memory Limit** | 20Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `GOMEMLIMIT` | `16MiB` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `PRODUCT_CATALOG_PORT` | `8080` |
| `PRODUCT_CATALOG_RELOAD_INTERVAL` | `10` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=product-catalog`
   - Check logs: `kubectl logs -l app=product-catalog --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=product-catalog`
   - Review traces in Jaeger
