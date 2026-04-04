# RISK REGISTER V1

| ID | Risk | Probability | Impact | Trigger | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R1 | Scope expansion beyond MVP | Medium | High | New features requested after Week 8 | Freeze MVP and defer extras | Nghia + Loc | Open |
| R2 | Retrieval quality too low | Medium | High | Low evidence precision | Improve chunking, reranker, query rewrite | Nghia | Open |
| R3 | Graph data stale or incomplete | Medium | High | Wrong dependency path in RCA | Add graph refresh job and integrity checks | Nghia | Open |
| R4 | Tool execution timeout | High | Medium | Long response from cluster commands | Add timeout, retry, and fallback path | Loc | Open |
| R5 | Unsafe action proposal | Low | Critical | Mutating action suggested without guard | Safety gate, denylist, approval required | Loc | Open |
| R6 | Incident labels are weak | Medium | High | Conflicting ground truth | Label review checklist and dual review | Nghia + Loc | Open |
| R7 | Benchmark not reproducible | Medium | High | Results vary without clear reason | Version config, deterministic scripts, seed control | Nghia | Open |
| R8 | Demo instability | Medium | High | Crash during defense demo | Prepare fallback demo and recorded run | Nghia + Loc | Open |

## Review cadence
- Review every Friday.
- Escalate any High impact risk not mitigated within one week.
