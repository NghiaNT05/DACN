# Kafka Service Troubleshooting

## Service Info
- **Name**: kafka
- **Namespace**: default
- **Image**: ghcr.io/open-telemetry/demo:2.1.3-kafka
- **Port**: 9092
- **Consumers**: accounting, fraud-detection

## Symptoms

### Kafka Not Ready
- Pod stuck in CrashLoopBackOff
- Consumers not receiving messages
- Producer connection refused

### Message Lag
- Orders delayed in accounting
- Fraud detection behind
- High consumer lag

## Common Causes

### 1. Storage Issues
```bash
# Check PVC if using persistent storage
kubectl get pvc -n default | grep kafka

# Check disk usage
kubectl exec -it deploy/kafka -n default -- df -h
```

### 2. Memory Pressure
```bash
kubectl top pod -l opentelemetry.io/name=kafka -n default

# Check JVM heap
kubectl logs -l opentelemetry.io/name=kafka -n default | grep -i "heap\|memory\|oom"
```

### 3. Network Partition
```bash
# Test connectivity from producer (checkout)
kubectl exec -it deploy/checkout -n default -- nc -zv kafka 9092
```

### 4. Zookeeper Issues (if using ZK mode)
```bash
kubectl logs -l opentelemetry.io/name=kafka -n default | grep -i zookeeper
```

## Diagnostic Commands

```bash
# Kafka pod status
kubectl describe pod -l opentelemetry.io/name=kafka -n default

# Kafka logs
kubectl logs -l opentelemetry.io/name=kafka -n default --tail=100

# Check topics
kubectl exec -it deploy/kafka -n default -- kafka-topics.sh --list --bootstrap-server localhost:9092

# Check consumer groups
kubectl exec -it deploy/kafka -n default -- kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# Check lag
kubectl exec -it deploy/kafka -n default -- kafka-consumer-groups.sh --describe --all-groups --bootstrap-server localhost:9092
```

## Resolution Steps

### If Kafka won't start
```bash
# Delete and recreate pod
kubectl delete pod -l opentelemetry.io/name=kafka -n default
# Wait for new pod
kubectl get pod -l opentelemetry.io/name=kafka -n default -w
```

### If messages stuck
```bash
# Restart consumers
kubectl rollout restart deployment/accounting deployment/fraud-detection -n default
```

### If out of disk
```bash
# Check retention and clean up
kubectl exec -it deploy/kafka -n default -- kafka-configs.sh --alter --entity-type topics --entity-name orders --add-config retention.ms=3600000 --bootstrap-server localhost:9092
```

### Reset consumer offset (data loss warning!)
```bash
kubectl exec -it deploy/kafka -n default -- kafka-consumer-groups.sh --reset-offsets --to-latest --all-topics --group accounting-group --execute --bootstrap-server localhost:9092
```

## Related Signals
- `waiting_reason=CrashLoopBackOff` on kafka
- `connection_refused` to kafka:9092
- `k8s_event_reason=Unhealthy`
- `broker_not_available` in producer logs

## Upstream/Downstream Impact
- **Upstream**: checkout completes but events lost
- **Downstream**:
  - accounting: orders not recorded
  - fraud-detection: no fraud analysis
  - Data inconsistency between services
