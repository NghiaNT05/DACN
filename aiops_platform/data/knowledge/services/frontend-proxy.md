# Frontend Proxy Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `frontend-proxy` |
| **Type** | gateway |
| **Language** | Envoy Proxy |
| **Port** | 8080 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-frontend-proxy` |
| **Memory Limit** | 65Mi |
| **CPU Limit** | Not set |

## Dependencies

- `$(OTEL_COLLECTOR_NAME)`
- `frontend`
- `grafana`
- `image-provider`
- `jaeger-query`
- `load-generator`

## Environment Variables

| Variable | Value |
|----------|-------|
| `ENVOY_ADMIN_PORT` | `10000` |
| `ENVOY_PORT` | `8080` |
| `FLAGD_HOST` | `flagd` |
| `FLAGD_PORT` | `8013` |
| `FLAGD_UI_HOST` | `flagd-ui` |
| `FLAGD_UI_PORT` | `4000` |
| `FRONTEND_HOST` | `frontend` |
| `FRONTEND_PORT` | `8080` |
| `GRAFANA_HOST` | `grafana` |
| `GRAFANA_PORT` | `80` |
| `IMAGE_PROVIDER_HOST` | `image-provider` |
| `IMAGE_PROVIDER_PORT` | `8081` |
| `JAEGER_HOST` | `jaeger-query` |
| `JAEGER_UI_PORT` | `16686` |
| `LOCUST_WEB_HOST` | `load-generator` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=frontend-proxy`
   - Check logs: `kubectl logs -l app=frontend-proxy --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=frontend-proxy`
   - Review traces in Jaeger
