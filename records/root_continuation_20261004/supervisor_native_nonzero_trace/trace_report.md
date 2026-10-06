# Nonzero `UNKNOWN_DRAIN` trace

The one admitted diagnostic reproduced the prior result with an unchanged supervisor SHA-256 `4D8272AA5DBC330E4199B216BD9B3FD3D240C2C8D1C59E223E37D249C936F663`, the same harmless worker, Python 3.10.11, manifest limits, and `kill_on_close`. It captured 21 native API events in 0.141 seconds. The controller returned normally; point-in-time Toolhelp snapshots found its PID and the worker PID absent after cleanup. The supervisor restart receipt matched the original status/run ID/drain fields.

The exact sequence establishes the cause:

1. `WaitForSingleObject` returned 0 for the worker, and `GetExitCodeProcess` returned 3.
2. Cleanup called `_winapi.TerminateProcess` on that already-exited worker. The real call raised `PermissionError` with `winerror=5` (access denied).
3. `kernel32.TerminateJobObject` returned 1. The owned worker PID was absent and later job accounting reported active count 0.
4. `_shutdown` still sets `terminate_ok=False` when `TerminateProcess` raises, then returns `UNKNOWN_DRAIN` at [contained_supervisor.py](E:/the_harness/records/root_continuation_20261004/supervisor_cleanup_root_repair/contained_supervisor.py:549) and [contained_supervisor.py](E:/the_harness/records/root_continuation_20261004/supervisor_cleanup_root_repair/contained_supervisor.py:587), despite the successful job termination and zero active count.

This confirms the root hypothesis for the prior nonzero case. The wrapper delegated each observed API call with unchanged arguments, returned the original native result, or re-raised the original exception; it did not inject outcomes. The trace records actual return types, values, exception type, and WinError. Input hashes were unchanged before and after. No source was modified, and no additional fixture cases were run.

The run receipt is `native_runs/nonzero_trace_20261004T143231Z/trace_receipt.json`; the raw 21-event log is `native_runs/nonzero_trace_20261004T143231Z/native_api_trace.jsonl`. The log SHA-256 is `E86F13BC13198458875F27E7781DD924B19EFE41E075534467DA2AA3132D91DE`. This is a diagnosis of the experimental candidate's drain classification, not production admission or whole-tree certification.
