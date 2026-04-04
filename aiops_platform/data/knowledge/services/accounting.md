# Accounting Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `accounting` |
| **Type** | backend |
| **Language** | Go |
| **Port** | N/A |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-accounting` |
| **Memory Limit** | 120Mi |
| **CPU Limit** | Not set |

## Dependencies

- `kafka`

## Environment Variables

| Variable | Value |
|----------|-------|
| `DB_CONNECTION_STRING` | `Host=postgresql;Username=otelu;Password=otelp;D...` |
| `KAFKA_ADDR` | `kafka:9092` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=accounting`
   - Check logs: `kubectl logs -l app=accounting --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=accounting`
   - Review traces in Jaeger
