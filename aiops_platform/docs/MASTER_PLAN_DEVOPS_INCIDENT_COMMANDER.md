# MASTER PLAN - REAL SYSTEM FINAL (2026-04-01)

## 1. Objective
Build a defensible DevOps Incident Commander MVP around the real Kubernetes environment, with strict evidence grounding and safety controls.

## 2. Reality Baseline (As-Built)
This section is derived from running code, not assumptions.

### 2.1 Implemented now
1. Ingestion pipeline is operational in live cluster context.
2. Incident events are produced from:
- Deployment runtime status
- Pod runtime status
- Kubernetes Warning Events stream
3. Enrichment is in place:
- pod log signatures (from `kubectl logs`)
- diagnostics snippets (from `kubectl describe`)
4. Validation and hygiene are in place:
- schema gate against `data/schemas/incident_event.schema.json`
- in-cycle dedupe
- cross-cycle correlation key
- cooldown suppression state
5. Periodic execution is in place:
- finite cycles or continuous loop
- interval control
- history snapshot archive option

### 2.2 Source of truth in code
1. `src/ingestion/pipeline_v1.py`
2. `scripts/run_ingestion_v1.py`
3. `data/schemas/incident_event.schema.json`
4. `data/incidents/ingestion_snapshot_v1.json`
5. `data/incidents/ingestion_state_v1.json`

### 2.3 Not implemented yet
1. Retrieval-ready text bundle generation after each cycle.
2. Vector DB indexing and semantic top-k retrieval.
3. Graph store and GraphRAG retrieval.
4. RCA reasoning engine and action-plan generation runtime.
5. End-to-end benchmark runner across A/B/C/D baselines.

## 3. Scope Freeze (Must follow 100%)
Only follow this sequence. Do not open new feature tracks outside this order.

### Phase A - Ingestion hardening (DONE)
Exit criteria:
1. ingest pipeline runs without syntax/runtime errors.
2. schema-valid events are emitted.
3. cooldown suppresses repeated incidents.
4. event enrichment fields are populated when data exists.

### Phase B - Retrieval preparation (NEXT)
Deliverables:
1. Build post-ingest retrieval bundle file per cycle.
2. Define canonical chunk units for runbooks, SOPs, historical incidents.
3. Add retention policy for ingestion state/history.

Exit criteria:
1. each incident has retrieval context text emitted.
2. artifacts are versioned and reproducible.
3. stale state/history is pruned by policy.

### Phase C - Vector RAG baseline
Deliverables:
1. embedding + vector index pipeline.
2. semantic top-k API over text corpus.
3. retrieval quality diagnostics (hit sources, scores, coverage).

Exit criteria:
1. repeatable top-k retrieval for same query.
2. retrieval outputs are traceable to source chunks.

### Phase D - GraphRAG baseline
Deliverables:
1. service dependency graph schema + ingestion.
2. graph neighborhood retrieval around incident service(s).
3. fusion layer (vector + graph + recency weights).

Exit criteria:
1. graph evidence is attached per RCA candidate.
2. fusion output is deterministic under fixed inputs.

### Phase E - Reasoning and safety execution
Deliverables:
1. RCA report generator aligned with `rca_report.schema.json`.
2. Action-plan generator aligned with `action_plan.schema.json`.
3. Safety policy enforcement and command audit trail.

Exit criteria:
1. structured RCA + action outputs validate against schema.
2. read-only commands can execute with logs and duration.
3. mutating actions require approval metadata.

### Phase F - Evaluation and defense package
Deliverables:
1. benchmark runner for A/B/C/D.
2. KPI summary table and failure analysis.
3. reproducible scripts and final demo flow.

Exit criteria:
1. benchmark artifacts generated reproducibly.
2. KPI deltas are evidence-backed.
3. final demo runs from clean instructions.

## 4. Execution Rules
1. No planning-only claims without runnable artifact.
2. Every completed item must include:
- code path
- command to run
- output artifact path
3. If a document conflicts with runtime truth, runtime truth wins and doc must be updated immediately.
4. Do not keep stale status boards once replaced by this plan.

## 5. Immediate Next Work Package (Start now)
1. Implement retrieval bundle emitter after each ingest cycle.
2. Define `data/knowledge/` structure for runbook/SOP/postmortem corpus.
3. Add retention cleanup for `ingestion_state_v1.json` and `data/incidents/history/`.
4. Add tests for:
- schema validation gate
- log signature extraction
- describe snippet extraction
- cooldown behavior

## 6. Definition of Done (Project-level)
1. Incident -> Retrieve -> RCA -> Action flow runs end-to-end on real cluster data.
2. Outputs are schema-valid and auditable.
3. Safety policy is enforced by runtime, not only documented.
4. Benchmark results are reproducible and comparable across baselines.
