# Frontend Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `frontend` |
| **Type** | frontend |
| **Language** | TypeScript/Next.js |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-frontend` |
| **Memory Limit** | 250Mi |
| **CPU Limit** | Not set |

## Dependencies

- `$(OTEL_COLLECTOR_NAME)`
- `ad`
- `cart`
- `checkout`
- `currency`
- `product-catalog`
- `recommendation`
- `shipping`

## Environment Variables

| Variable | Value |
|----------|-------|
| `AD_ADDR` | `ad:8080` |
| `CART_ADDR` | `cart:8080` |
| `CHECKOUT_ADDR` | `checkout:8080` |
| `CURRENCY_ADDR` | `currency:8080` |
| `ENV_PLATFORM` | `kubernetes` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `FRONTEND_ADDR` | `:8080` |
| `FRONTEND_PORT` | `8080` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `PORT` | `$(FRONTEND_PORT)` |
| `PRODUCT_CATALOG_ADDR` | `product-catalog:8080` |
| `PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://localhost:8080/otlp-http/v1/traces` |
| `RECOMMENDATION_ADDR` | `recommendation:8080` |
| `SHIPPING_ADDR` | `http://shipping:8080` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=frontend`
   - Check logs: `kubectl logs -l app=frontend --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=frontend`
   - Review traces in Jaeger
