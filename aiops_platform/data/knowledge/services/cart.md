# Cart Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `cart` |
| **Type** | backend |
| **Language** | .NET (C#) |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-cart` |
| **Memory Limit** | 160Mi |
| **CPU Limit** | Not set |

## Dependencies

- `valkey-cart`

## Environment Variables

| Variable | Value |
|----------|-------|
| `ASPNETCORE_URLS` | `http://*:$(CART_PORT)` |
| `CART_PORT` | `8080` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `VALKEY_ADDR` | `valkey-cart:6379` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=cart`
   - Check logs: `kubectl logs -l app=cart --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=cart`
   - Review traces in Jaeger
