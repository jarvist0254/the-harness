# Revision 2 native supervisor fixture

All five admitted CPU-only native cases ran sequentially with no early stop. The run used the unchanged revision2 supervisor (`3CB1E44E35EA6C2EF9C01E0D329FB0DF98C7785056D65E33CED52EC04706E51C`), pinned Python 3.10.11 x64, four-worker maximum, `kill_on_close`, 5-second startup/deadline ceiling, 1-KiB per-stream cap, hidden child controllers, and 30-second retained-process-handle outer bounds. All six source/runtime/fixture pins passed before launch and remained equal before/after each case.

| Case | Elapsed | Supervisor result | Job active / drain | Controller and worker PIDs absent | Restart receipt |
|---|---:|---|---|---|---|
| Four natural workers | 0.281 s | `PROCESS_COMPLETED`; four exit 0 | 0 / `CLEANUP` | yes / yes | exact status/run ID/drain match |
| Nonzero worker | 0.125 s | `FAILED/nonzero_exit`; exit 3 | 0 / `CLEANUP` | yes / yes | exact match |
| Deadline | 1.078 s | `TIMEOUT/deadline`; worker terminated | 0 / `CLEANUP` | yes / yes | exact match |
| Cancellation | 0.328 s | `CANCELLED/cancelled`; worker terminated | 0 / `CLEANUP` | yes / yes | exact match |
| Log overflow | 0.141 s | `FAILED/LOG_LIMIT`; worker terminated | 0 / `CLEANUP` | yes / yes | exact match |

The natural run captured the eight exact distinct stdout/stderr markers. Timeout and cancellation each captured the worker's `sleeping` marker. Overflow retained exactly 1,024 stdout bytes and marked overflow; the child wrote 16 KiB as requested. All per-stream logs and raw supervisor receipts remain under `native_runs/native_20261004T144031Z/`. Every receipt keeps `whole_tree_certificate=false`; PID evidence is point-in-time, and resource high-water is unmeasured.

The suite summary is `native_runs/native_20261004T144031Z/suite_receipt.json` (SHA-256 `462F36FC76E44F2BA037F31209C8ABFAC51107FC10AB95B5C194A95AB4AAC85E`). One receipt-format quirk is preserved: the driver's `accepted` field serializes as a worker list for timeout/cancel because the gate helper returns its final `and workers` operand; those nonempty lists are truthy and the suite's overall result is `FIXTURE_EXPECTATIONS_MET`. Their raw status, drain, PID, and restart checks are recorded separately. This fixture does not admit production use or certify arbitrary descendants.
