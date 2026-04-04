# TOOL TIMEOUT AND RETRY POLICY V1

## Purpose
Ensure diagnostic tool calls remain reliable and bounded.

## Timeout defaults
1. kubectl get/describe/logs/top: 20 seconds
2. rollout status checks: 45 seconds
3. external API calls: 15 seconds

## Retry policy
1. Retries allowed only for transient failures.
2. Max retries: 2.
3. Backoff: 1 second then 2 seconds.

## Failure classification
1. Transient
- timeout
- connection reset
- temporary DNS errors

2. Permanent
- command syntax error
- permission denied
- resource not found (if confirmed)

## Escalation rules
1. If all retries fail, mark step as failed and continue read-only diagnostics.
2. Do not escalate to mutating action automatically.
3. Include timeout and retry trace in report.
