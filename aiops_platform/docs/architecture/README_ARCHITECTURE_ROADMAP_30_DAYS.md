# AIOps Architecture Plan and 30-Day Execution Roadmap

## 1) Muc tieu tai lieu
Tai lieu nay tong hop 3 phan:
- Kien truc muc tieu se trien khai tiep theo (to-be architecture)
- Nhung gi da hoan thanh den hien tai (as-is state)
- Lo trinh 30 ngay tiep theo de chuyen tu semi-auto sang full automation

## 2) Trang thai hien tai da lam duoc

### 2.1 Data and Observability ingestion
- Da co luong lay telemetry tu Prometheus va Loki.
- Da chuan hoa du lieu thanh cac ban ghi metric, log, telemetry_error.
- Da ghi ra JSONL de lam dau vao cho RAG va RCA.

Tai lieu va code lien quan:
- [src/aiops/telemetry/collector.py](src/aiops/telemetry/collector.py)
- [telemetry/fetch_telemetry.py](telemetry/fetch_telemetry.py)
- [scripts/run_pipeline.sh](scripts/run_pipeline.sh)

### 2.2 RCA pipeline
- Da co E2E pipeline gom health gate, collect telemetry, build index, RCA.
- Da co graph-rag-llm flow va report schema version 2.0.
- Da co output report JSON gom root cause, confidence, evidence, suggested actions, audit.

Tai lieu va code lien quan:
- [scripts/run_incident_rca.py](scripts/run_incident_rca.py)
- [src/aiops/rca/context_bundle.py](src/aiops/rca/context_bundle.py)
- [src/aiops/rag/assistant.py](src/aiops/rag/assistant.py)
- [src/aiops/rca/reporting.py](src/aiops/rca/reporting.py)
- [cmdb/incident_report.schema.json](cmdb/incident_report.schema.json)

### 2.3 Governance and reliability
- Da co datasource health gate (Prometheus/Loki).
- Da co che do strict health khi can bat buoc datasource healthy.
- Da co schema validation cho report RCA.

Tai lieu va code lien quan:
- [src/aiops/health/datasource_health.py](src/aiops/health/datasource_health.py)
- [scripts/run_pipeline.sh](scripts/run_pipeline.sh)
- [docs/architecture/PRODUCTION_BLUEPRINT.md](docs/architecture/PRODUCTION_BLUEPRINT.md)

### 2.4 Benchmark and quality checking
- Da chay bo benchmark nhieu incident de do do on dinh root cause.
- Da co bang tong hop accuracy va hallucination level.

Artifact lien quan:
- [../aiops_data/reports/stability_runs/stability_summary_final.json](../aiops_data/reports/stability_runs/stability_summary_final.json)
- [../aiops_data/reports/latest_incident_report.json](../aiops_data/reports/latest_incident_report.json)

## 3) Khoang trong con thieu de dat production-grade

1. Chua co detector tao incident event tu alert mot cach tu dong.
2. Chua co trigger orchestration tu dong kick RCA sau khi co incident.
3. Chua co co che scheduling chuan cho ingestion + incremental indexing.
4. Chua co quality gate online de ngan report confidence cao nhung sai.
5. Chua co dashboard SLA cho RCA quality (accuracy, MTTR impact, false positive).

## 4) Kien truc muc tieu (to-be)

### 4.1 Layer A - Observability plane
- App services phat metrics, logs, traces lien tuc.
- Prometheus, Loki, Tempo luu tru va truy van.

### 4.2 Layer B - Incident detection plane
- Rule-based alerts + anomaly detection.
- Tao incident event gom: service scope, symptom, severity, time window, correlation key.

### 4.3 Layer C - RCA orchestration plane
- Incident event trigger workflow.
- Workflow goi telemetry collector theo dung time window.
- Workflow goi index update (uu tien incremental).
- Workflow goi RCA engine va report generator.

### 4.4 Layer D - Intelligence plane
- Retrieval context (telemetry + cmdb + runtime)
- Graph candidate ranking + causal paths
- LLM inference + deterministic governance
- Confidence calibration + policy checks

### 4.5 Layer E - Delivery and feedback plane
- Gui ket qua den Slack/Jira/PagerDuty.
- Human confirm root cause dung/sai.
- Feed back vao quality tuning va ranking policies.

## 5) Lo trinh 30 ngay tiep theo

## Week 1 - Auto incident detection and event contract
Muc tieu:
- Co incident detector chay dinh ky va phat event theo contract thong nhat.

Cong viec:
1. Dinh nghia incident event schema.
2. Tao detector script (rule-based) doc metrics logs va tao event.
3. Luu event vao thu muc queue hoac topic (ban dau co the file queue).
4. Them unit checks cho event format va dedup theo correlation key.

Deliverables:
- Incident event schema tai docs.
- Detector script va sample incident events.
- README huong dan test detector.

## Week 2 - Trigger RCA automation
Muc tieu:
- Co runner tu dong nhan incident event va chay RCA khong can thao tac tay.

Cong viec:
1. Tao orchestration script theo event -> collect -> index -> RCA -> report.
2. Them lock/timeout/retry de tranh treo process.
3. Gan run_id va trace id xuyen suot chuoi xu ly.
4. Co che fail-safe: datasource khong on thi chuyen degraded mode co danh dau.

Deliverables:
- Auto RCA runner script.
- Log va audit cho tung buoc.
- Huong dan van hanh khi co incident event.

## Week 3 - Quality gates and anti-hallucination hardening
Muc tieu:
- Giam truong hop confidence cao nhung root cause sai.

Cong viec:
1. Them quality gate truoc khi chot root cause.
2. Buoc consistency check giua retrieval evidence, graph roots, final root.
3. Neu evidence khong hoi tu thi ep status insufficient_data.
4. Them benchmark run command de test daily tren bo scenarios.

Deliverables:
- Quality gate module.
- Bao cao benchmark daily.
- Policy document cho confidence calibration.

## Week 4 - Productionization and handover
Muc tieu:
- Chay on dinh theo cron/event va co dashboard theo doi chat luong.

Cong viec:
1. Tao lich chay collector/indexer (CronJob hoac scheduler).
2. Tich hop output den kenh van hanh (Slack/Jira).
3. Tao dashboard KPI cho RCA quality va pipeline reliability.
4. Viet runbook su co va tai lieu handover.

Deliverables:
- Scheduler manifests/scripts.
- Dashboard KPI + alerting cho pipeline.
- Runbook va go-live checklist.

## 6) KPI va tieu chi nghiem thu 30 ngay

KPI ky thuat:
1. Incident-to-report latency p95 <= 5 phut (muc tieu demo/prod-lite).
2. Pipeline success rate >= 95% trong ca tuan.
3. Treo process do timeout <= 2%.

KPI chat luong RCA:
1. Root cause top-1 accuracy tang it nhat 20 diem % so voi baseline hien tai.
2. Ty le wrong-high-confidence giam it nhat 50%.
3. Ty le report bi danh dau hallucination high < 15%.

KPI van hanh:
1. Co incident runbook va rollback procedure ro rang.
2. Co dashboard theo doi realtime cho so luong incidents va ti le thanh cong RCA.

## 7) Cach trinh bay trong buoi demo

Thong diep ngan gon:
1. He thong da co xuong song graph-rag RCA va report audit ro rang.
2. Giai doan tiep theo la auto detection + auto trigger de thanh full automation.
3. Lo trinh 30 ngay da co KPI do luong va tieu chi nghiem thu cu the.

Checklist truoc demo:
1. Kiem tra datasource health truoc khi chay.
2. Chot incident input va output report duong dan ro rang.
3. Chuan bi 1 case thanh cong va 1 case uncertain de minh hoa governance.

## 8) Risk chinh va giai phap

1. Risk: Source telemetry khong on dinh
- Giai phap: Health gate + retry/backoff + degraded mode.

2. Risk: Root cause sai nhung confidence cao
- Giai phap: quality gates + confidence calibration + benchmark daily.

3. Risk: Process treo khi LLM call
- Giai phap: timeout bat buoc moi step + watchdog + kill stale runs.

4. Risk: Drift du lieu sau khi thay doi workload
- Giai phap: refresh benchmark set hang tuan + cap nhat policy theo feedback.

## 9) Ket luan
He thong da hoan thanh phan cot loi tu thu thap telemetry den RCA va report. Trong 30 ngay tiep theo, trong tam la nang cap tu semi-auto sang full auto event-driven, cung voi quality gates de tang do tin cay root cause trong van hanh thuc te.
