# Postgresql Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `postgresql` |
| **Type** | database |
| **Language** | PostgreSQL |
| **Port** | 5432 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-postgresql` |
| **Memory Limit** | 100Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `POSTGRES_DB` | `otel` |
| `POSTGRES_PASSWORD` | `otel` |
| `POSTGRES_USER` | `root` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=postgresql`
   - Check logs: `kubectl logs -l app=postgresql --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=postgresql`
   - Review traces in Jaeger
