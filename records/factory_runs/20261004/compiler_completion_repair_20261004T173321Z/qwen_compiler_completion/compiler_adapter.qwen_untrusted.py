import threading

_COMPILER_ROOT_EXITED_CLEANUP_REQUIRED = "COMPILER_ROOT_EXITED_CLEANUP_REQUIRED"
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 258
_SLEEP_SECONDS = 0.02

def _compiler_wait_run(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event, dead_by):
    wapi = deps["_winapi"]
    mono_fn = deps.get("monotonic")
    sleep_fn = deps.get("sleep")
    if mono_fn is None:
        import time
        mono_fn = time.monotonic
    if sleep_fn is None:
        import time
        sleep_fn = time.sleep
    if spec.get("policy") != "kill_on_close":
        return "UNKNOWN", "policy_mismatch"
    workers = spec.get("workers", [])
    if len(workers) != 1 or len(owned) != 1:
        return "UNKNOWN", "worker_count_mismatch"
    rec = owned[0]
    if not rec.get("assigned") or not rec.get("resumed"):
        return "UNKNOWN", "not_assigned_resumed"
    root_ph = rec.get("ph")
    if root_ph is None:
        return "UNKNOWN", "no_root_handle"
    while True:
        if cancel_event.is_set():
            return "CANCELLED", "cancelled"
        if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
            return "FAILED", "LOG_LIMIT"
        if any(slot.get("bad_read") for slot in slots):
            return "UNKNOWN", "bad_read"
        now = mono_fn()
        if now >= dead_by:
            return "TIMEOUT", "deadline"
        try:
            waited = wapi.WaitForSingleObject(root_ph, 0)
        except Exception:
            return "UNKNOWN", "wait_exception"
        rec["wait"] = waited
        if waited == _WAIT_OBJECT_0:
            break
        elif waited == _WAIT_TIMEOUT:
            sleep_fn(_SLEEP_SECONDS)
            continue
        else:
            return "UNKNOWN", "unexpected_wait_status"
    if cancel_event.is_set():
        return "CANCELLED", "cancelled"
    if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
        return "FAILED", "LOG_LIMIT"
    if any(slot.get("bad_read") for slot in slots):
        return "UNKNOWN", "bad_read"
    now = mono_fn()
    if now >= dead_by:
        return "TIMEOUT", "deadline"
    try:
        exit_code = wapi.GetExitCodeProcess(root_ph)
    except Exception:
        return "UNKNOWN", "exit_query_exception"
    rec["exit_code"] = exit_code
    if exit_code != 0:
        return "FAILED", "nonzero_exit"
    return _COMPILER_ROOT_EXITED_CLEANUP_REQUIRED, "compiler_root_zero_auxiliaries_possible"

def install(private_module):
    private_module._wait_run = _compiler_wait_run
