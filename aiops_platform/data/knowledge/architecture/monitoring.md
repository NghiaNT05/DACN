# Observability & Monitoring Guide

## Instrumentation Overview

All services in the OpenTelemetry Demo are instrumented with:
- **Traces**: Distributed tracing via OpenTelemetry SDK
- **Metrics**: Application and runtime metrics
- **Logs**: Structured logging (varies by service)

## Tracing Infrastructure

### Jaeger Configuration
| Setting | Value |
|---------|-------|
| **UI Port** | 16686 |
| **Collector Port** | 4317 (gRPC), 4318 (HTTP) |
| **Query Port** | 16685 |
| **Storage** | In-memory (default) |
| **Memory Limit** | 400Mi |

### Access Jaeger UI
```bash
# Port forward to Jaeger
kubectl port-forward svc/otel-demo-jaeger-query 16686:16686

# Open: http://localhost:16686
```

### Common Trace Queries

**Find slow checkout operations:**
```
service=checkout operation=checkout duration>1000ms
```

**Find failed payment attempts:**
```
service=payment status=error
```

**Track order flow:**
```
service=checkout OR service=payment OR service=shipping
```

## OTLP Endpoint Configuration

All services export telemetry to:
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-demo-otelcol:4317
```

### Instrumented Services

| Service | SDK | Auto-instrumented? |
|---------|-----|-------------------|
| `checkout` | Go | Yes (OTLP) |
| `cart` | .NET | Yes (OTLP) |
| `payment` | Node.js | Yes (OTLP) |
| `shipping` | Rust | Yes (OTLP) |
| `recommendation` | Python | Yes (OTLP) |
| `frontend` | JavaScript | Yes (OTLP) |
| `ad` | Java | Yes (OTLP) |
| `email` | Ruby | Yes (OTLP) |
| `currency` | C++ | Yes (OTLP) |
| `fraud-detection` | Kotlin | Yes (OTLP) |
| `accounting` | Go | Yes (OTLP) |

## Feature Flags (flagd)

### Configuration
| Setting | Value |
|---------|-------|
| **Port** | 8013 |
| **Protocol** | gRPC |
| **Memory** | 75Mi |

### Active Feature Flags
```json
{
  "cartServiceFailure": false,
  "recommendationServiceCacheFailure": false,
  "adServiceManualGc": false,
  "adServiceHighCpu": false,
  "paymentServiceFailure": false,
  "kafkaQueueProblems": false
}
```

### Inject Failures for Testing
```bash
# Enable cart failure
curl -X PUT http://flagd:8013/flags/cartServiceFailure -d '{"state": "ENABLED"}'

# Enable payment failure
curl -X PUT http://flagd:8013/flags/paymentServiceFailure -d '{"state": "ENABLED"}'
```

## Health Checks

### gRPC Health Check (Most Services)
```bash
grpcurl -plaintext <service>:8080 grpc.health.v1.Health/Check
```

### HTTP Health Endpoints
| Service | Endpoint |
|---------|----------|
| `jaeger` | `GET /` on 16686 |
| `opensearch` | `GET /` on 9200 |
| `frontend` | `GET /` on 8080 |

### Kubernetes Probes
Most services use:
```yaml
livenessProbe:
  grpc:
    port: 8080
  periodSeconds: 10
readinessProbe:
  grpc:
    port: 8080
  periodSeconds: 5
```

## Alerting Recommendations

### Critical Alerts
| Condition | Threshold | Action |
|-----------|-----------|--------|
| checkout error rate | > 5% | Page on-call |
| payment latency | p99 > 2s | Page on-call |
| kafka lag | > 1000 | Investigate |
| OOM events | any | Investigate |

### Warning Alerts
| Condition | Threshold | Action |
|-----------|-----------|--------|
| recommendation latency | p99 > 500ms | Ticket |
| cart error rate | > 1% | Ticket |
| CPU > 80% | sustained 5m | Review scaling |

## Log Aggregation

### Log Locations
```bash
# Kubernetes pod logs
kubectl logs -l app=<service-name> --tail=100

# All pods in namespace
kubectl logs --all-containers=true -l app.kubernetes.io/instance=otel-demo
```

### Common Log Patterns

**Checkout errors:**
```bash
kubectl logs -l app=checkout | grep -i "error\|fail\|exception"
```

**Payment issues:**
```bash
kubectl logs -l app=payment | grep -i "decline\|timeout\|error"
```

**Kafka connectivity:**
```bash
kubectl logs -l app=accounting | grep -i "kafka\|broker\|disconnect"
```

## Debugging Commands

```bash
# Check all pod status
kubectl get pods -o wide

# Describe failing pod
kubectl describe pod <pod-name>

# Check events for errors
kubectl get events --sort-by='.lastTimestamp' | tail -20

# Resource usage
kubectl top pods --sort-by=memory

# Network connectivity test
kubectl exec -it <pod> -- nc -zv <target-service> <port>

# DNS resolution test
kubectl exec -it <pod> -- nslookup <service-name>
```
