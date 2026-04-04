# OpenTelemetry Demo - System Overview

## Architecture Summary

This document describes the OpenTelemetry Demo application running on Kubernetes (Minikube).

| Metric | Value |
|--------|-------|
| **Total Services** | 21 |
| **Namespace** | default |
| **Platform** | Minikube |
| **Version** | 2.1.3 |

## Service Categories

### Frontend (2 services)
| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 8080 | Web UI (Next.js) |
| `frontend-proxy` | 8080 | Envoy reverse proxy |

### Backend Services (12 services)
| Service | Port | Language | Memory Limit |
|---------|------|----------|--------------|
| `checkout` | 8080 | Go | 20Mi |
| `cart` | 8080 | .NET | 160Mi |
| `payment` | 8080 | Node.js | 120Mi |
| `shipping` | 8080 | Rust | 20Mi |
| `currency` | 8080 | C++ | 20Mi |
| `email` | 8080 | Ruby | 100Mi |
| `product-catalog` | 8080 | Go | 20Mi |
| `recommendation` | 8080 | Python | 500Mi |
| `ad` | 8080 | Java | 300Mi |
| `quote` | 8080 | PHP | 40Mi |
| `accounting` | N/A | Go | 120Mi |
| `fraud-detection` | N/A | Kotlin | 300Mi |

### Data Stores (3 services)
| Service | Port | Type |
|---------|------|------|
| `valkey-cart` | 6379 | Redis-compatible cache |
| `postgresql` | 5432 | Relational database |
| `opensearch` | 9200 | Search/Analytics |

### Message Queue (1 service)
| Service | Port | Description |
|---------|------|-------------|
| `kafka` | 9092 | Event streaming |

### Observability (2 services)
| Service | Port | Description |
|---------|------|-------------|
| `jaeger` | 16686 | Distributed tracing |
| `flagd` | 8013 | Feature flags |

### Testing (1 service)
| Service | Port | Description |
|---------|------|-------------|
| `load-generator` | 8089 | Locust load testing |

## Critical Paths

### Checkout Flow (Critical)
```
frontend → checkout → cart → valkey-cart
                   → payment
                   → shipping → quote
                   → email
                   → kafka → accounting
                          → fraud-detection
```

### Product Browse Flow
```
frontend → product-catalog
        → recommendation → product-catalog
        → currency
        → ad
```

### Cart Flow
```
frontend → cart → valkey-cart (Redis)
```

## Resource Summary

| Category | Total Memory Limit |
|----------|-------------------|
| Backend Services | ~1.5 GB |
| Data Stores | ~720 MB |
| Observability | ~475 MB |
| Frontend | ~315 MB |
| **Total** | **~3 GB** |

## Network Topology

All services communicate via ClusterIP services within the Kubernetes cluster.

- **gRPC**: checkout, cart, currency, product-catalog, shipping, ad
- **HTTP**: email, recommendation, frontend
- **Kafka Protocol**: kafka (9092)
- **Redis Protocol**: valkey-cart (6379)
- **PostgreSQL**: postgresql (5432)

## Monitoring Endpoints

| Service | Health Check |
|---------|--------------|
| Most services | gRPC health check on main port |
| Jaeger | HTTP `/` on 16686 |
| Kafka | TCP 9092 |
| OpenSearch | HTTP `/` on 9200 |

## Related Documentation

- [Service Specs](../services/) - Detailed specs for each service
- [Runbooks](../runbooks/) - Troubleshooting guides
- [Postmortems](../postmortems/) - Incident reports
