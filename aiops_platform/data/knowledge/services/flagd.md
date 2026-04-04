# Flagd Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `flagd` |
| **Type** | backend |
| **Language** | Go (Feature Flags) |
| **Port** | 8013 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-feature/flagd:v0.12.8` |
| **Memory Limit** | 75Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `FLAGD_METRICS_EXPORTER` | `otel` |
| `FLAGD_OTEL_COLLECTOR_URI` | `$(OTEL_COLLECTOR_NAME):4317` |
| `GOMEMLIMIT` | `60MiB` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=flagd`
   - Check logs: `kubectl logs -l app=flagd --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=flagd`
   - Review traces in Jaeger
