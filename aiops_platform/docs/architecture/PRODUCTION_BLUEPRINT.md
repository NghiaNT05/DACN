# Production Blueprint (AIOps + RAG)

## Target architecture

1. Runtime services emit logs/metrics/traces continuously.
2. OpenTelemetry Collector receives OTLP streams.
3. Loki/Prometheus/Tempo persist observability data.
4. CMDB stores service topology, dependencies, and thresholds.
5. Telemetry ingestion service creates normalized event records.
6. Vector indexing service updates knowledge base incrementally.
7. Context bundle synthesizer compacts anomaly signals and dependency hints.
8. Chatbot and RCA APIs serve user queries.

## Production hardening checklist

1. Data ingestion
- Replace manual snapshot only mode with scheduled ingestion (CronJob) and optional streaming workers.
- Persist raw telemetry events before indexing.

2. Reliability
- Add health checks for Loki/Prometheus/Tempo and fail-open logic.
- Add retry/backoff and dead-letter queue for ingestion failures.

3. Security
- Use Kubernetes Secrets for tokens and endpoints.
- Enforce RBAC for read-only observability access.

4. Governance
- Add retention policy for raw events, snapshots, and report artifacts.
- Log user queries and RCA outputs for auditability.

5. RCA response quality
- Enforce strict structured JSON output with schema validation.
- Keep prompt and context budget tuned to reduce irrelevant evidence.

## Implemented assets for the 5 priority upgrades

1. Continuous ingestion scaffolding
- `deploy/kubernetes/telemetry-collector-cronjob.yaml`
- `deploy/kubernetes/telemetry-indexer-cronjob.yaml`

2. Deep context synthesis
- `src/aiops/rca/context_bundle.py` compacts metric anomalies, top error signatures, and dependency hints for LLM RCA.

3. Health-gated RCA
- `src/aiops/health/datasource_health.py`
- `scripts/run_pipeline.sh` supports `HEALTH_GATE=1` and `STRICT_HEALTH=1`.
- `scripts/run_incident_rca.py` supports `--health-gate` and `--strict-health`.

4. Structured RCA contract
- `cmdb/incident_report.schema.json` defines LLM-context report contract (v2.0).
- `src/aiops/rag/assistant.py` normalizes and validates LLM JSON outputs.

5. Security and retention hardening
- `deploy/kubernetes/hardening/rbac-readonly-observability.yaml`
- `deploy/kubernetes/hardening/secret-template.yaml`
- `scripts/ops/retention_cleanup.sh`
- `deploy/kubernetes/hardening/retention-cleanup-cronjob.yaml`

## Service boundaries

- `src/aiops/telemetry`: data collection adapters
- `src/aiops/ingestion`: vector index build/update
- `src/aiops/rca`: context bundling + report shaping
- `src/aiops/rag`: LLM response orchestration + relevance guardrails
- `src/aiops/observers`: live system status context for chatbot queries
