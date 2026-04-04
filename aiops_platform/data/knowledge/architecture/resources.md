# Resource Allocation Guide

## Current Resource Configuration

Data extracted from Kubernetes deployments on Minikube.

## Memory Limits by Service

| Service | Memory Limit | Category | Notes |
|---------|--------------|----------|-------|
| `load-generator` | 1500Mi | Testing | Highest - runs Locust |
| `kafka` | 600Mi | Queue | JVM-based, needs heap |
| `recommendation` | 500Mi | Backend | Python ML workload |
| `jaeger` | 400Mi | Observability | Trace storage |
| `ad` | 300Mi | Backend | Java service |
| `fraud-detection` | 300Mi | Backend | Kotlin/JVM |
| `frontend` | 250Mi | Frontend | Next.js SSR |
| `cart` | 160Mi | Backend | .NET runtime |
| `payment` | 120Mi | Backend | Node.js |
| `accounting` | 120Mi | Backend | Go, event processing |
| `email` | 100Mi | Backend | Ruby |
| `opensearch` | 100Mi | Database | Minimal config |
| `postgresql` | 100Mi | Database | Minimal config |
| `flagd` | 75Mi | Backend | Feature flags |
| `frontend-proxy` | 65Mi | Gateway | Envoy proxy |
| `image-provider` | 50Mi | Backend | Static images |
| `quote` | 40Mi | Backend | PHP |
| `checkout` | 20Mi | Backend | Go, lightweight |
| `currency` | 20Mi | Backend | C++, minimal |
| `product-catalog` | 20Mi | Backend | Go, minimal |
| `shipping` | 20Mi | Backend | Rust, efficient |
| `valkey-cart` | 20Mi | Cache | In-memory store |

## Resource Categories

### High Memory Services (>200Mi)
```

 Service         │ Memory  │ Reason                      │
clear
 load-generator  │ 1500Mi  │ Simulates many users        │
 kafka           │ 600Mi   │ JVM + message buffering     │
 recommendation  │ 500Mi   │ ML model in memory          │
 jaeger          │ 400Mi   │ Trace storage               │
 ad              │ 300Mi   │ Java runtime overhead       │
 fraud-detection │ 300Mi   │ Kotlin/JVM overhead         │
 frontend        │ 250Mi   │ Next.js SSR + React         │

```

### Low Memory Services (<50Mi)
```

 Service         │ Memory  │ Language                    │
clear
 checkout        │ 20Mi    │ Go - compiled, efficient    │
 currency        │ 20Mi    │ C++ - native code           │
 product-catalog │ 20Mi    │ Go - simple CRUD            │
 shipping        │ 20Mi    │ Rust - zero overhead        │
 valkey-cart     │ 20Mi    │ Redis - optimized           │
 quote           │ 40Mi    │ PHP - lightweight           │

```

## OOM Risk Assessment

### High Risk (tight memory)
| Service | Limit | Risk Factor |
|---------|-------|-------------|
| `checkout` | 20Mi | Very tight for Go with GC |
| `currency` | 20Mi | Should be OK (C++) |
| `valkey-cart` | 20Mi | Risk if cache grows |

### Recommendation
```yaml
# checkout - increase to handle traffic spikes
resources:
  limits:
    memory: "50Mi"  # from 20Mi

# valkey-cart - increase for cache growth
resources:
  limits:
    memory: "100Mi"  # from 20Mi
```

## CPU Configuration

Currently **no CPU limits** are set on any service.

### Implications:
- Services can burst to use all available CPU
- No throttling during high load
- Risk of noisy neighbor problems

### Recommended CPU Limits:
| Category | Recommended CPU |
|----------|-----------------|
| High compute (ML) | 500m - 1000m |
| Medium (Java/JVM) | 200m - 500m |
| Low (Go/Rust) | 50m - 200m |
| Cache/DB | 100m - 300m |

## Scaling Considerations

### Horizontal Scaling Candidates
| Service | Current | Can Scale? | Notes |
|---------|---------|------------|-------|
| `frontend` | 1 | ✅ Yes | Stateless |
| `checkout` | 1 | ✅ Yes | Stateless |
| `cart` | 1 | ✅ Yes | State in Redis |
| `recommendation` | 1 | ✅ Yes | Stateless |
| `kafka` | 1 | ⚠️ Complex | Needs partition config |
| `valkey-cart` | 1 | ❌ No | Single instance cache |
| `postgresql` | 1 | ❌ No | Needs replication |

### Vertical Scaling (Memory Increase)
| Service | Current | Recommended | Reason |
|---------|---------|-------------|--------|
| `checkout` | 20Mi | 50Mi | Handle burst traffic |
| `recommendation` | 500Mi | 750Mi | Larger models |
| `kafka` | 600Mi | 1Gi | More partitions |

## Monitoring Commands

```bash
# Real-time resource usage
kubectl top pods

# Check OOM kills
kubectl get events --field-selector reason=OOMKilled

# Check resource requests vs limits
kubectl describe nodes | grep -A 5 "Allocated resources"

# Per-service memory usage
kubectl top pod -l app=<service-name>
```
