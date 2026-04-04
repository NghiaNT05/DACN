# Load Generator Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `load-generator` |
| **Type** | testing |
| **Language** | Python |
| **Port** | 8089 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-load-generator` |
| **Memory Limit** | 1500Mi |
| **CPU Limit** | Not set |

## Dependencies

- `0.0.0.0`
- `http://frontend-proxy:8080`

## Environment Variables

| Variable | Value |
|----------|-------|
| `FLAGD_HOST` | `flagd` |
| `FLAGD_OFREP_PORT` | `8016` |
| `FLAGD_PORT` | `8013` |
| `LOCUST_AUTOSTART` | `true` |
| `LOCUST_BROWSER_TRAFFIC_ENABLED` | `true` |
| `LOCUST_HEADLESS` | `false` |
| `LOCUST_HOST` | `http://frontend-proxy:8080` |
| `LOCUST_SPAWN_RATE` | `1` |
| `LOCUST_USERS` | `10` |
| `LOCUST_WEB_HOST` | `0.0.0.0` |
| `LOCUST_WEB_PORT` | `8089` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4317` |
| `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` | `python` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=load-generator`
   - Check logs: `kubectl logs -l app=load-generator --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=load-generator`
   - Review traces in Jaeger
