# ARCHITECTURE SPEC V1

## 1. Scope
This document defines the architecture for DevOps Incident Commander MVP.

## 1.1 Reality lock
This spec distinguishes:
1. as-built components (implemented now)
2. target components (planned next)

Any implementation claim must map to an existing code path.

## 2. Problem statement
Given an alert or an operator question, the system must:
1. Diagnose probable root causes.
2. Provide verifiable evidence.
3. Propose safe remediation steps.
4. Execute read-only checks automatically.
5. Require approval for mutating actions.

## 3. Architecture overview
Core architecture uses Hybrid RAG + GraphRAG + Agent Tooling.

## 3.1 Current implementation status (2026-04-01)
1. Implemented:
- Ingestion pipeline from Kubernetes runtime and warning events
- Enrichment with logs and describe diagnostics
- Incident schema validation gate
- Correlation key + cooldown suppression state
- Periodic ingestion runner
2. Not implemented:
- Vector retrieval runtime
- Graph retrieval runtime
- RCA reasoning runtime
- Action-plan runtime
- Benchmark harness runtime

### 3.1 Main components
1. ChatOps API
- Receives alert payloads and natural language queries.

2. Triage Service
- Assigns severity and identifies primary service candidates.

3. Hybrid Retriever
- Vector retrieval from runbooks/docs.
- Graph retrieval from runtime dependency graph.
- Score fusion with recency.

4. Reasoning Engine
- Produces root-cause top-k with confidence.
- Produces evidence chain and action plan.

5. Agent Tool Executor
- Executes read-only diagnostics.
- Supports mutating actions only after approval.

6. Safety Gate
- Risk scoring.
- Policy enforcement.
- Approval requirement for non-read-only actions.

7. Reporting Service
- Produces structured incident report.

8. Evaluation Harness
- Runs baseline and computes KPI.

### 3.2 Data stores
1. Vector Store
- Embedded chunks of docs and runbooks.

2. Graph Store
- Nodes: Service, Pod, Deployment, ConfigMap, Secret, Alert, Incident.
- Edges: depends_on, changed_by, failed_in, affects, remediated_by.

3. Snapshot Store
- Time-ordered telemetry snapshots for recency analysis.

4. Report Store
- RCA reports and execution audit logs.

## 3.3 As-built data stores
1. Snapshot artifacts in `data/incidents/`:
- `ingestion_snapshot_v1.json`
- `ingestion_state_v1.json`
- optional per-cycle history files
2. JSON schemas in `data/schemas/`:
- incident_event
- rca_report
- action_plan

## 4. Primary execution flows
### 4.1 Alert-driven flow
1. Receive alert.
2. Ingestion produces normalized incident events.
3. Correlation/cooldown suppresses repeated noise.
4. Retrieval and reasoning layers (planned) consume incident artifacts.
5. Action planning and safety execution (planned).
6. Build structured report (planned).

### 4.2 Chat query flow
1. Receive operator question.
2. Map question to incident context.
3. Hybrid retrieval.
4. Generate diagnosis and recommended checks.
5. Optional action request goes through approval gate.

## 5. Non-functional requirements
1. Observability
- Every decision step must be logged with timestamp and evidence IDs.

2. Reliability
- Tool timeout handling required.
- Retries for transient tool errors.

3. Safety
- Destructive actions are blocked by default.
- Mutating actions require explicit approval.

4. Reproducibility
- Benchmark runs must produce versioned result files.

## 6. Week 1 architecture decisions
1. Runtime target: Minikube.
2. Application under observation: OpenTelemetry Demo.
3. Baselines: A LLM only, B Vector RAG, C Vector+Graph, D Vector+Graph+Agent.
4. MVP uses read-only auto checks only.

## 6.1 Current code mapping
1. `src/ingestion/pipeline_v1.py`: ingest + enrich + validate + correlate.
2. `scripts/run_ingestion_v1.py`: periodic cycle runner.
3. `data/schemas/*.schema.json`: output contracts.

## 7. Out of scope for MVP
1. Fully autonomous self-healing without approval.
2. Multi-cluster federation.
3. Advanced rollout strategies.
