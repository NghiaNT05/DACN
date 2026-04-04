# Checkout Service Troubleshooting

## Service Info
- **Name**: checkout
- **Namespace**: default
- **Image**: ghcr.io/open-telemetry/demo:2.1.3-checkout
- **Language**: Go
- **Dependencies**: cart, payment, shipping, email, kafka, currency, product-catalog

## Symptoms

### Checkout Failing
- "Order failed" error on frontend
- 500 errors in browser console
- Orders not appearing in accounting

### Slow Checkout
- Checkout taking > 10 seconds
- Timeout errors
- Partial order completion

## Common Causes

### 1. Payment Service Down
Checkout depends on payment service for processing.
```bash
kubectl get pod -l opentelemetry.io/name=payment -n default
kubectl logs -l opentelemetry.io/name=payment -n default --tail=50
```

### 2. Kafka Unavailable
Order events sent to Kafka for accounting/fraud-detection.
```bash
kubectl get pod -l opentelemetry.io/name=kafka -n default
kubectl logs -l opentelemetry.io/name=kafka -n default --tail=50
```

### 3. Downstream Service Timeout
```bash
# Check all checkout dependencies
for svc in cart payment shipping email currency product-catalog; do
  echo "=== $svc ==="
  kubectl get pod -l opentelemetry.io/name=$svc -n default
done
```

### 4. Currency Conversion Failure
```bash
kubectl logs -l opentelemetry.io/name=currency -n default --tail=50
```

## Diagnostic Commands

```bash
# Checkout pod details
kubectl describe pod -l opentelemetry.io/name=checkout -n default

# Checkout logs with error filter
kubectl logs -l opentelemetry.io/name=checkout -n default --tail=200 | grep -i error

# Check gRPC connectivity
kubectl exec -it deploy/checkout -n default -- grpc_health_probe -addr=:8080

# Trace a checkout request in Jaeger
kubectl port-forward svc/jaeger-query 16686:16686 -n default
# Open http://localhost:16686 and search for checkout traces
```

## Resolution Steps

### If Payment is down
```bash
kubectl rollout restart deployment/payment -n default
# Wait for ready
kubectl rollout status deployment/payment -n default
```

### If Kafka is down
```bash
kubectl rollout restart deployment/kafka -n default
# Note: May take 1-2 minutes for Kafka to be ready
kubectl logs -l opentelemetry.io/name=kafka -n default -f
```

### If multiple services down (after cluster restart)
```bash
# Restart in dependency order
kubectl rollout restart deployment/valkey-cart deployment/postgresql -n default
sleep 30
kubectl rollout restart deployment/kafka -n default
sleep 60
kubectl rollout restart deployment/cart deployment/payment deployment/shipping -n default
sleep 30
kubectl rollout restart deployment/checkout -n default
```

## Related Signals
- `k8s_event_reason=Unhealthy` on checkout
- `k8s_event_reason=BackOff` on payment
- `connection_refused` to kafka:9092
- `deadline_exceeded` in checkout logs

## Upstream/Downstream Impact
- **Upstream**: frontend checkout button fails
- **Downstream**: 
  - accounting won't receive order
  - fraud-detection won't analyze
  - email won't send confirmation
