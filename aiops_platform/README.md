# DevOps Incident Commander

Real-system-first incident analysis project for Kubernetes operations.

## Current Status
1. Ingestion pipeline is implemented and runnable against live Kubernetes context.
2. Incident events include runtime status, warning events, log signatures, and describe diagnostics.
3. Incident outputs are validated against JSON schema.
4. Correlation and cooldown suppression are active across cycles.
5. Retrieval bundle generation for RAG pipeline (Phase B).
6. Knowledge corpus with runbooks, SOPs, and postmortem templates.
7. Retention policy for state/history/bundle cleanup.

## Key Paths
1. `src/ingestion/pipeline_v1.py` - Main ingestion logic
2. `src/ingestion/retrieval_bundle.py` - Bundle generation for RAG
3. `src/ingestion/retention.py` - Retention cleanup logic
4. `scripts/run_ingestion_v1.py` - Ingestion runner
5. `scripts/run_retention.py` - Retention cleanup runner
6. `data/schemas/` - JSON schemas
7. `data/incidents/` - Ingestion outputs
8. `data/retrieval/` - Retrieval bundles
9. `data/knowledge/` - Runbooks, SOPs, postmortems

## Run Ingestion
```bash
# Basic ingestion
/home/nghia/DACN/rag_env/bin/python scripts/run_ingestion_v1.py --namespace default --cycles 1

# With retrieval bundle emission
/home/nghia/DACN/rag_env/bin/python scripts/run_ingestion_v1.py --namespace default --cycles 1 --emit-bundle
```

## Run Retention Cleanup
```bash
# Dry run (preview what would be deleted)
/home/nghia/DACN/rag_env/bin/python scripts/run_retention.py --dry-run

# Actual cleanup
/home/nghia/DACN/rag_env/bin/python scripts/run_retention.py
```

## Canonical Planning Docs
1. `docs/MASTER_PLAN_DEVOPS_INCIDENT_COMMANDER.md` (single execution plan)
2. `docs/ARCHITECTURE_SPEC_V1.md`
3. `docs/KPI_SPEC_V1.md`
4. `docs/BENCHMARK_PROTOCOL_V1.md`
