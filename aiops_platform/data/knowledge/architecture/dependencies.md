# Service Dependencies Map

## Overview

This document maps all service dependencies extracted from Kubernetes environment variables.

## Dependency Graph

```

                              FRONTEND LAYER                                  │
     ┌─────────────────┐                                   │  ┌──
  │ load-generator│────►│ frontend-proxy  │                                   │
  └──────────────┘     └────────┬────────┘                                   │
                                │                                             │
                       ┌────────▼────────┐                                   │
                       │    frontend     │                                   │
                                   │                       └────────┬──
clear
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
      ┌─────────────────┐      ┌────────────────┐
     cart      │      │    checkout     │      │ recommendation │
      └───────┬────────┘      └────────┬──────
        │                       │                       │
        ▼                       │                       ▼
               │              ┌────────────────┐
  valkey-cart  │               │              │ product-catalog│
   (Redis)     │               │              └────────────────┘
               │
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
           │        │           │           │           
        ▼           ▼           ▼           ▼           ▼
 ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───
 payment  │ │ shipping │ │  email   │ │ currency │ │  kafka   │
 └────┬─────┘ └──────────┘ └──────────┘ └─
                  │                                      │
                  ▼                                      │
            ┌──────────┐                    ┌────────────┴────────────┐
            │  quote   │                    │                         │
            └──────────┘                    ▼                         ▼
        ┌─────────────────┐                                    ┌──
                                    │  accounting  │        │ fraud-detection │
                                    └──────────────┘        └─────────────────┘
```

## Dependency Matrix

### Frontend Dependencies
| Service | Depends On |
|---------|------------|
| `frontend` | cart, checkout, currency, product-catalog, recommendation, shipping, ad, flagd |
| `frontend-proxy` | frontend |
| `load-generator` | frontend-proxy |

### Checkout Flow Dependencies
| Service | Depends On |
|---------|------------|
| `checkout` | cart, currency, email, kafka, payment, product-catalog, shipping, flagd |
| `cart` | valkey-cart, flagd |
| `payment` | flagd |
| `shipping` | quote, flagd |

### Event Processing Dependencies
| Service | Depends On |
|---------|------------|
| `accounting` | kafka |
| `fraud-detection` | kafka |

### Feature Flag Dependencies
| Service | Depends On |
|---------|------------|
| `ad` | flagd |
| `recommendation` | product-catalog, flagd |

## Upstream/Downstream Analysis

### Critical Services (Many Dependents)

| Service | Upstream Count | Downstream Count | Impact Level |
|---------|----------------|------------------|--------------|
| `flagd` | 0 | 7 | **CRITICAL** |
| `cart` | 1 | 2 | HIGH |
| `kafka` | 1 | 2 | HIGH |
| `product-catalog` | 0 | 3 | HIGH |
| `currency` | 0 | 2 | MEDIUM |

### Leaf Services (No Dependents)

| Service | Role |
|---------|------|
| `accounting` | Event consumer |
| `fraud-detection` | Event consumer |
| `quote` | Quote calculation |
| `email` | Notification |

## Failure Impact Analysis

### If `kafka` fails:
- `checkout` cannot publish order events
- `accounting` stops processing
- `fraud-detection` stops processing
- **Impact**: Orders processed but not recorded

### If `valkey-cart` fails:
- `cart` cannot persist data
- Users lose cart items
- **Impact**: Cart functionality broken

### If `flagd` fails:
- Feature flags return defaults
- 7 services affected
- **Impact**: Features may behave unexpectedly

### If `checkout` fails:
- Users cannot complete orders
- **Impact**: Revenue loss, critical business impact

## Connection Protocols

| Protocol | Services |
|----------|----------|
| **gRPC** | checkout, cart, currency, product-catalog, shipping, ad, recommendation |
| **HTTP** | email, frontend, frontend-proxy |
| **Kafka** | kafka → accounting, fraud-detection |
| **Redis** | cart → valkey-cart |
| **PostgreSQL** | (not directly used by app services) |
