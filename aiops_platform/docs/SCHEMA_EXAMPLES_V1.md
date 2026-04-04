# SCHEMA EXAMPLES V1

## Purpose
Provide concrete examples to validate schema contracts.

## Example 1: Incident Event
```json
{
  "incident_id": "INC-0001",
  "timestamp": "2026-04-01T00:10:00Z",
  "severity": "high",
  "category": "dependency_failure",
  "source_service": "frontend",
  "observed_signals": ["http_5xx_spike", "rpc_timeout"],
  "candidate_services": ["frontend", "checkoutservice"],
  "metadata": {
    "namespace": "default"
  }
}
```

## Example 2: RCA Report
```json
{
  "incident_id": "INC-0001",
  "status": "ok",
  "root_cause_top_k": [
    {"service": "checkoutservice", "rank": 1, "score": 0.86},
    {"service": "frontend", "rank": 2, "score": 0.67}
  ],
  "evidence": [
    {"source": "loki://frontend", "content": "rpc timeout to checkoutservice", "relevance": 0.92},
    {"source": "graph://depends_on", "content": "frontend depends_on checkoutservice", "relevance": 0.88}
  ],
  "recommended_actions": [
    "kubectl get pods -n default",
    "kubectl logs deploy/checkoutservice -n default --tail=200"
  ],
  "confidence": 0.82,
  "quality_gate": {
    "mode": "hybrid"
  }
}
```

## Example 3: Action Plan
```json
{
  "incident_id": "INC-0001",
  "actions": [
    {
      "step": 1,
      "command": "kubectl get deploy -n default",
      "safety_level": "safe_read_only",
      "requires_approval": false,
      "reason": "Collect deployment status"
    },
    {
      "step": 2,
      "command": "kubectl rollout restart deploy/checkoutservice -n default",
      "safety_level": "low_risk",
      "requires_approval": true,
      "reason": "Restart suspected unhealthy service"
    }
  ]
}
```
