# Build-policy supervisor native fixture — root review data

Status: `ROOT_REVIEW_READY_FIVE_NATIVE_CASES_MET`.
This records the root-admitted five-case CPU-only fixture. It is not production admission.

| Case | Status / reason | Worker exits | Assigned/resumed | Job active | Drain | Restart | PIDs absent | Recomputed |
|---|---|---|---|---:|---|---|---|---|
| natural | PROCESS_COMPLETED /  | 0,0,0,0 | True,True,True,True | 0 | CLEANUP | True | True | True |
| nonzero | FAILED / nonzero_exit | 3 | True | 0 | CLEANUP | True | True | True |
| timeout | TIMEOUT / deadline | 1 | True | 0 | CLEANUP | True | True | True |
| cancel | CANCELLED / cancelled | 1 | True | 0 | CLEANUP | True | True | True |
| overflow | FAILED / LOG_LIMIT | 1 | True | 0 | CLEANUP | True | True | True |

Worker PIDs were also rechecked after the run using process enumeration; this is a point-in-time absence check. `whole_tree_certificate` remains false. Driver `accepted` values were not used as proof; raw case conditions were recomputed independently.

The overflow control observed `LOG_LIMIT` with 1,024 captured stdout bytes and overflow flagged; the worker exited 1 after the bounded pipe closed. This is recorded as an observed fixture side effect, not normalized to exit 0.
