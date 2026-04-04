# Kafka Service

## Overview

| Property | Value |
|----------|-------|
| **Service Name** | `kafka` |
| **Type** | message-queue |
| **Language** | Java (Kafka) |
| **Port** | 9092 |
| **Replicas** | 1 |

## Container

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/open-telemetry/demo:2.1.3-kafka` |
| **Memory Limit** | 600Mi |
| **CPU Limit** | Not set |

## Dependencies

- No external dependencies

## Environment Variables

| Variable | Value |
|----------|-------|
| `KAFKA_ADVERTISED_LISTENERS` | `PLAINTEXT://kafka:9092` |
| `KAFKA_CONTROLLER_LISTENER_NAMES` | `CONTROLLER` |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | `1@kafka:9093` |
| `KAFKA_HEAP_OPTS` | `-Xmx400M -Xms400M` |
| `KAFKA_LISTENERS` | `PLAINTEXT://:9092,CONTROLLER://:9093` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://$(OTEL_COLLECTOR_NAME):4318` |

## Troubleshooting

### Common Issues

1. **Service Unavailable**
   - Check pod status: `kubectl get pod -l app=kafka`
   - Check logs: `kubectl logs -l app=kafka --tail=100`

2. **Connection Errors**
   - Verify dependencies are running
   - Check network policies
   - Test connectivity: `kubectl exec -it <pod> -- curl <dependency>:<port>/health`

3. **High Latency**
   - Check resource usage: `kubectl top pod -l app=kafka`
   - Review traces in Jaeger
