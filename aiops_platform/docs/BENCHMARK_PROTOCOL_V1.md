# BENCHMARK PROTOCOL V1

## 1. Objective
Provide a reproducible benchmark process for RCA and safe action planning.

## 2. Incident dataset plan
- Minimum incidents: 30.
- Categories (minimum 6 per category):
1. Dependency failure
2. Config drift
3. Rollout failure
4. Resource pressure
5. Pipeline regression

## 3. Incident record template
Each incident must contain:
1. incident_id
2. timestamp
3. category
4. primary_service
5. observed_signals
6. ground_truth_root_cause
7. expected_safe_actions

## 4. Baseline run protocol
For each incident, run in order:
1. Baseline A
2. Baseline B
3. Baseline C
4. Baseline D

Execution rules:
1. Same incident input across baselines.
2. Same timeout policy.
3. Same evaluation script.

## 5. Metrics to collect per run
1. top1_hit
2. top3_hit
3. evidence_precision_at_5
4. timeout_flag
5. unsafe_action_flag
6. diagnose_latency_seconds
7. time_to_resolution_seconds

## 6. Aggregation protocol
1. Aggregate by category.
2. Aggregate overall.
3. Report confidence intervals where possible.

## 7. Acceptance criteria
Benchmark is valid only if:
1. All incidents have ground truth labels.
2. All runs produce structured output.
3. Missing data rate is below 5 percent.

## 8. Output artifacts
1. benchmark_results.csv
2. benchmark_summary.md
3. failure_cases.md
4. ablation_table.csv
