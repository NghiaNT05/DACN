# AIOps RAG System (Production-Style Layout)

## Directory layout

- `src/aiops/config.py`: centralized runtime settings.
- `src/aiops/telemetry/`: Prometheus/Loki collection adapters.
- `src/aiops/ingestion/`: vector indexing pipeline.
- `src/aiops/rca/`: anomaly detection, scoring, report generation.
- `src/aiops/rag/`: chatbot and RCA LLM orchestration with relevance guardrails.
- `src/aiops/observers/`: live Kubernetes system context (clusters, pods, CPU/RAM).
- `scripts/`: executable entrypoints for pipeline/chatbot/RCA.
- `deploy/kubernetes/`: production deployment manifests (e.g., scheduled telemetry collector).
- `docs/architecture/`: architecture and hardening blueprint.

## Backward compatibility

Legacy entrypoints remain usable:

- `ingest.py`
- `rag.py`
- `run_rca_demo.py`
- `run_e2e_demo.sh`

They are wrappers mapped to the standardized `src/aiops` modules.

## Quick run

```bash
cd /home/nghia/DACN/aiops_platform
chmod +x scripts/run_pipeline.sh scripts/chatbot.py scripts/run_incident_rca.py run_e2e_demo.sh
FAST_MODE=1 ./run_e2e_demo.sh
```

Health-gated run (recommended):

```bash
HEALTH_GATE=1 STRICT_HEALTH=0 FAST_MODE=1 ./run_e2e_demo.sh
```

## Chatbot mode

```bash
cd /home/nghia/DACN/aiops_platform
/home/nghia/DACN/rag_env/bin/python3 scripts/chatbot.py
```

Example queries:

- `How many clusters are active?`
- `Show RAM and CPU status.`
- `How many pods are running by namespace?`
- `rca: checkout failures increased after payment timeout`

## RCA mode

- `llm-context` (only mode): aggregate telemetry + CMDB + health context and let LLM infer RCA with structured JSON output.

Example (LLM-context):

```bash
cd /home/nghia/DACN/aiops_platform
/home/nghia/DACN/rag_env/bin/python3 scripts/run_incident_rca.py \
	--health-gate \
	--strict-health \
	--incident "Checkout failures after payment outage"
```

## RCA report artifact

- JSON report path: `../aiops_data/reports/latest_incident_report.json`
- JSON schema: `cmdb/incident_report.schema.json` (v2.0, LLM-context-only)

## Production target notes

See `docs/architecture/PRODUCTION_BLUEPRINT.md` for full hardening plan:

- Continuous telemetry ingestion
- Health-gated RCA with degraded status signaling
- RBAC and secrets management
- Context and prompt optimization for LLM RCA quality

Retention automation scaffold is available at:

- `deploy/kubernetes/hardening/retention-cleanup-cronjob.yaml`

## Retention cleanup

```bash
cd /home/nghia/DACN/aiops_platform
chmod +x scripts/ops/retention_cleanup.sh
./scripts/ops/retention_cleanup.sh
```
