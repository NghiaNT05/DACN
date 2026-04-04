# SAFETY POLICY V1

## Safety levels
1. safe_read_only
- Query-only commands.
- Auto execution allowed.

2. low_risk
- Reversible mutating actions.
- Approval required.

3. high_risk
- Potentially disruptive actions.
- Block by default.

## Default command policy
### Allowed auto (safe_read_only)
- kubectl get
- kubectl describe
- kubectl logs
- kubectl top

### Approval required (low_risk)
- kubectl rollout restart
- kubectl scale (within approved bounds)

### Blocked (high_risk)
- kubectl delete
- kubectl drain
- kubectl edit in production context

## Approval metadata requirements
Any approved mutating action must record:
1. approver
2. timestamp
3. incident_id
4. command
5. justification

## Audit requirements
- Every command must store exit code and duration.
- Store stdout/stderr summary for traceability.
