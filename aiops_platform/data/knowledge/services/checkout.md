# Checkout Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `checkout` |
| **Type** | backend |
| **Language** | Go |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-checkout` |
| **Memory Limit** | 20Mi |
| **CPU Limit** | Not set |

## Dependencies

- `cart`
- `currency`
- `email`
- `kafka`
- `payment`
- `product-catalog`
- `shipping`

## Environment Variables

| Variable | Value |
|----------|-------|
| `CART_ADDR` | `cart:8080` |
| `CHECKOUT_PORT` | `8080` |
| `CURRENCY_ADDR` | `currency:8080` |
| `EMAIL_ADDR` | `http://email:8080` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `GOMEMLIMIT` | `16MiB` |
| `KAFKA_ADDR` | `kafka:9092` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `PAYMENT_ADDR` | `payment:8080` |
| `PRODUCT_CATALOG_ADDR` | `product-catalog:8080` |
| `SHIPPING_ADDR` | `http://shipping:8080` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=checkout`
   - Check logs: `kubectl logs -l app=checkout --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=checkout`
   - Review traces in Jaeger
