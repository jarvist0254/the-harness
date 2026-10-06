"""Independent local compiler-only fallback. No import/install native actions.
ROOT must separately admit this exact source before any native use.
"""
def install(private_module):
    monotonic = private_module._monotonic
    sleep = private_module._sleep
    def wait_run(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event, dead_by):
        if spec.get('policy') != 'kill_on_close' or len(spec.get('workers', [])) != 1 or len(owned) != 1:
            return 'UNKNOWN', 'compiler_policy_mismatch'
        rec = owned[0]
        if rec.get('assigned') is not True or rec.get('resumed') is not True or rec.get('ph') is None:
            return 'UNKNOWN', 'compiler_root_ownership'
        handle = rec['ph']
        def guards():
            if rec.get('assigned') is not True or rec.get('resumed') is not True or rec.get('ph') != handle:
                return 'UNKNOWN', 'compiler_root_ownership'
            if cancel_event.is_set():
                return 'CANCELLED', 'cancelled'
            if overflow_event.is_set() or any(slot.get('overflow') for slot in slots):
                return 'FAILED', 'LOG_LIMIT'
            if any(slot.get('bad_read') for slot in slots):
                return 'UNKNOWN', 'bad_read'
            if monotonic() >= dead_by:
                return 'TIMEOUT', 'deadline'
            return None
        wapi = deps['_winapi']
        while True:
            guarded = guards()
            if guarded is not None:
                return guarded
            try:
                waited = wapi.WaitForSingleObject(handle, 0)
            except Exception:
                return 'UNKNOWN', 'wait_failed'
            if type(waited) is not int:
                return 'UNKNOWN', 'wait_failed'
            rec['wait'] = waited
            guarded = guards()
            if guarded is not None:
                return guarded
            if waited == 258:
                sleep(0.02)
                continue
            if waited != 0:
                return 'UNKNOWN', 'wait_failed'
            try:
                exit_code = wapi.GetExitCodeProcess(handle)
            except Exception:
                return 'UNKNOWN', 'exit_query_failed'
            if type(exit_code) is not int:
                return 'UNKNOWN', 'exit_query_failed'
            rec['exit_code'] = exit_code
            # Actual terminal guards run after the successful exit query too.
            guarded = guards()
            if guarded is not None:
                return guarded
            if exit_code != 0:
                return 'FAILED', 'nonzero_exit'
            return 'COMPILER_ROOT_EXITED_CLEANUP_REQUIRED', 'compiler_root_exited_zero'
    private_module._wait_run = wait_run
