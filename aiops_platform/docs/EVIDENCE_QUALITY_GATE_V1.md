# EVIDENCE QUALITY GATE V1

## Goal
Prevent high-confidence RCA with weak evidence.

## Gate rules
1. Minimum evidence count: 2.
2. At least one runtime signal required.
3. At least one structural or dependency signal required.
4. If rules fail, force status to insufficient_data.

## Evidence categories
1. runtime_signal
- pod restart spike
- crashloop
- error rate spike

2. dependency_signal
- graph path from impacted service to candidate root

3. textual_signal
- runbook match
- similar historical incident match

## Confidence cap rules
1. If evidence count < 2, confidence <= 0.65.
2. If no runtime signal, confidence <= 0.55.
3. If top2 root scores are near tie (< 0.10), confidence <= 0.70.

## Output requirements
Every RCA output must include:
1. evidence list with sources
2. confidence value
3. quality gate decision notes
