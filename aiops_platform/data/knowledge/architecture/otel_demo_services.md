# OpenTelemetry Demo - Service Architecture

## Overview
This document describes the microservices architecture of the OpenTelemetry Demo e-commerce application running on Kubernetes (Minikube).

## Services Inventory

### Frontend Layer
| Service | Port | Description |
|---------|------|-------------|
| frontend | 8080 | Next.js web application |
| frontend-proxy | 8080 | Envoy proxy for routing |

### Business Services
| Service | Language | Description |
|---------|----------|-------------|
| cart | .NET | Shopping cart management |
| checkout | Go | Order checkout processing |
| payment | Node.js | Payment processing |
| currency | C++ | Currency conversion |
| shipping | Rust | Shipping cost calculation |
| email | Ruby | Email notifications |
| quote | PHP | Quote generation |
| product-catalog | Go | Product listing |
| recommendation | Python | Product recommendations |
| ad | Java | Advertisement service |
| accounting | Go | Order accounting |
| fraud-detection | Kotlin | Fraud analysis |

### Infrastructure Services
| Service | Description |
|---------|-------------|
| kafka | Message broker for async events |
| postgresql | Database for accounting |
| valkey-cart | Redis-compatible cache for cart |
| opensearch | Log aggregation and search |
| jaeger | Distributed tracing |
| flagd | Feature flags management |

## Service Dependencies

```
                    ┌─────────────┐
                    │  frontend   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌──────────┐     ┌────────────┐
    │  cart   │      │ checkout │     │  product   │
    │         │      │          │     │  catalog   │
    └────┬────┘      └────┬─────┘     └────────────┘
         │                │
         ▼                ├───────────────┬──────────┐
    ┌─────────┐          ▼               ▼          ▼
    │ valkey  │    ┌──────────┐   ┌──────────┐ ┌─────────┐
    │  cart   │    │ payment  │   │ shipping │ │  email  │
    └─────────┘    └────┬─────┘   └──────────┘ └─────────┘
                        │
                        ▼
                   ┌─────────┐
                   │  kafka  │
                   └────┬────┘
              ┌─────────┴─────────┐
              ▼                   ▼
        ┌────────────┐    ┌───────────────┐
        │ accounting │    │fraud-detection│
        └─────┬──────┘    └───────────────┘
              ▼
        ┌────────────┐
        │ postgresql │
        └────────────┘
```

## Critical Paths

### Checkout Flow (High Priority)
1. frontend → checkout → payment → kafka
2. kafka → accounting → postgresql
3. kafka → fraud-detection

### Cart Flow (Medium Priority)
1. frontend → cart → valkey-cart

### Product Flow (Low Priority)
1. frontend → product-catalog
2. frontend → recommendation

## Resource Requirements

| Service | CPU Request | Memory Limit |
|---------|-------------|--------------|
| opensearch | 1 core | 1100Mi |
| kafka | 500m | 512Mi |
| postgresql | 250m | 256Mi |
| frontend | 100m | 256Mi |
| Other services | 50m | 128Mi |

## Related Runbooks
- [Cart Service Issues](../runbooks/otel_cart_issues.md)
- [Checkout Failures](../runbooks/otel_checkout_failures.md)
- [Kafka Connection Problems](../runbooks/otel_kafka_issues.md)
