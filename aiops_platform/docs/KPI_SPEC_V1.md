# KPI SPEC V1

## 1. Purpose
Define measurable outcomes for the project.

## 2. KPI definitions
### 2.1 RCA Top-1 Accuracy
- Definition: proportion of incidents where predicted top root cause equals ground truth.
- Formula: correct_top1 / total_incidents.
- Target: >= 0.70.

### 2.2 RCA Top-3 Accuracy
- Definition: proportion of incidents where ground truth appears in top 3 candidates.
- Formula: correct_top3 / total_incidents.
- Target: >= 0.90.

### 2.3 Evidence Precision at 5
- Definition: relevant evidence items in top 5 divided by 5.
- Formula: relevant_in_top5 / 5.
- Target: >= 0.75 average.

### 2.4 Timeout Rate
- Definition: timed out operations divided by total tool operations.
- Formula: timeout_count / total_tool_calls.
- Target: <= 0.02.

### 2.5 Unsafe Action Proposal Rate
- Definition: unsafe suggested actions divided by total suggested actions.
- Formula: unsafe_proposals / total_proposals.
- Target: <= 0.01.

### 2.6 MTTR Reduction
- Definition: relative reduction in mean time to resolution versus baseline A.
- Formula: (mttr_baseline_a - mttr_system) / mttr_baseline_a.
- Target: >= 0.25.

## 3. Evaluation groups
1. Baseline A: LLM only.
2. Baseline B: LLM + Vector RAG.
3. Baseline C: LLM + Vector + Graph retrieval.
4. Baseline D: Baseline C + Agent + Safety gate.

## 4. Data collection requirements
1. Every incident must have a unique ID.
2. Ground truth root cause is mandatory.
3. Evidence entries must include source references.
4. Action plan must include safety level.
5. Tool execution logs must include timeout and error codes.

## 5. Reporting format
Weekly KPI report must include:
1. KPI summary table by baseline.
2. Failure case analysis.
3. Distribution plots for latency and confidence.
4. Change log for major prompt and retrieval updates.
