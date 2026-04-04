# Jaeger Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `jaeger` |
| **Type** | observability |
| **Language** | Go (Tracing) |
| **Port** | 5775 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `jaegertracing/all-in-one:1.53.0` |
| **Memory Limit** | 400Mi |
| **CPU Limit** | Not set |

## Dependencies

- `0.0.0.0:4317`
- `0.0.0.0:4318`
- `:9411`

## Environment Variables

| Variable | Value |
|----------|-------|
| `COLLECTOR_OTLP_ENABLED` | `true` |
| `COLLECTOR_OTLP_GRPC_HOST_PORT` | `0.0.0.0:4317` |
| `COLLECTOR_OTLP_HTTP_HOST_PORT` | `0.0.0.0:4318` |
| `COLLECTOR_ZIPKIN_HOST_PORT` | `:9411` |
| `JAEGER_DISABLED` | `false` |
| `METRICS_STORAGE_TYPE` | `prometheus` |
| `SPAN_STORAGE_TYPE` | `memory` |

## Health Checks

- **Liveness**: HTTP GET `/:14269`
- **Readiness**: HTTP GET `/:14269`

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=jaeger`
   - Check logs: `kubectl logs -l app=jaeger --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=jaeger`
   - Review traces in Jaeger
