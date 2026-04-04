# DOCS REALITY AUDIT (2026-04-01)

## Purpose
Audit documentation against the real implementation state and remove stale planning noise.

## Method
1. Compare docs claims with code in `src/ingestion/` and `scripts/run_ingestion_v1.py`.
2. Compare docs claims with runtime artifacts in `data/incidents/` and `data/schemas/`.
3. Rewrite or delete docs that conflict with runtime truth.

## Results

### Rewritten
1. `docs/MASTER_PLAN_DEVOPS_INCIDENT_COMMANDER.md`
- reason: contained outdated assumptions and schema field mismatch.
- action: replaced with a single reality-locked execution plan.

2. `docs/ARCHITECTURE_SPEC_V1.md`
- reason: did not clearly separate implemented vs planned layers.
- action: added as-built status and code mapping.

3. `README.md`
- reason: still described zero-state workspace.
- action: updated to current system status and canonical docs map.

### Deleted
1. `docs/WEEK1_TASK_BOARD.md`
- reason: historical board, no longer source of truth.

2. `docs/WEEK2_PROGRESS_V1.md`
- reason: rolling progress notes became stale and conflicted with live state.

### Kept (still valid)
1. `docs/KPI_SPEC_V1.md`
2. `docs/BENCHMARK_PROTOCOL_V1.md`
3. `docs/RISK_REGISTER_V1.md`
4. `docs/SAFETY_POLICY_V1.md`
5. `docs/TOOL_TIMEOUT_RETRY_POLICY_V1.md`
6. `docs/EVIDENCE_QUALITY_GATE_V1.md`
7. `docs/SCHEMA_EXAMPLES_V1.md`

## Canonical rule from now on
1. `docs/MASTER_PLAN_DEVOPS_INCIDENT_COMMANDER.md` is the single execution plan.
2. Runtime truth in code/artifacts overrides any stale doc text.
3. Historical status boards must not be reintroduced as primary planning docs.