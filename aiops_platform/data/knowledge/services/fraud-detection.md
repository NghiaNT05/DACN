# Fraud Detection Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `fraud-detection` |
| **Type** | backend |
| **Language** | Kotlin |
| **Port** | N/A |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-fraud-detection` |
| **Memory Limit** | 300Mi |
| **CPU Limit** | Not set |

## Dependencies

- `kafka`

## Environment Variables

| Variable | Value |
|----------|-------|
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `KAFKA_ADDR` | `kafka:9092` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=fraud-detection`
   - Check logs: `kubectl logs -l app=fraud-detection --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=fraud-detection`
   - Review traces in Jaeger
