# OpenSearch Startup Probe Failure

## Incident Summary
- **Date**: 2026-04-02
- **Duration**: ~30 seconds during pod startup
- **Severity**: Low (expected behavior)
- **Services Affected**: opensearch-0

## What Happened

During minikube restart, opensearch-0 pod showed Warning event:
```
Startup probe failed: dial tcp 10.244.0.81:9200: connect: connection refused
```

### Timeline
1. 17:24:30 - Pod scheduled and started
2. 17:24:35 - Startup probe begins (5s delay)
3. 17:24:35 to 17:25:05 - Multiple probe failures (expected)
4. 17:25:10 - OpenSearch ready, probes passing

## Root Cause

**Expected Behavior**: OpenSearch takes 30-60 seconds to initialize:
1. JVM startup (~10s)
2. Index recovery (~20s)
3. Cluster formation (~10s)

The startup probe is configured with:
- `initialDelaySeconds: 5`
- `periodSeconds: 10`
- `failureThreshold: 30`

This allows up to 5 + (10 × 30) = 305 seconds for startup.

## Why This Is Not a Problem

1. **Startup probe vs Readiness probe**: Startup probe failures don't cause pod restart until failureThreshold exceeded
2. **No traffic impact**: Pod doesn't receive traffic until startup probe passes
3. **Self-healing**: Once OpenSearch is ready, probes pass automatically

## Lessons Learned

### What Went Well
- Kubernetes probe configuration is appropriate
- No manual intervention needed
- Service recovered automatically

### What Could Be Improved
- Consider increasing `initialDelaySeconds` to reduce log noise
- Add init container to wait for dependencies

## Action Items

| Action | Owner | Status |
|--------|-------|--------|
| Document expected startup time | Platform Team | Done |
| Consider adjusting initialDelaySeconds | Platform Team | Backlog |
| Add startup time to monitoring | SRE Team | Backlog |

## Related Incidents
- None (first documentation)

## Detection
- Kubernetes Warning events
- Ingestion pipeline captured the event

## Metrics
- Time to ready: ~35 seconds
- Probe failures before success: 3
- User impact: None (startup only)
