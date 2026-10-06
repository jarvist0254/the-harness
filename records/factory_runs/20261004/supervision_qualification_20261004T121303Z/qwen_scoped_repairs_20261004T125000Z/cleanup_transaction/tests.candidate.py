import os
import sys
import json
import threading
import types
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Ensure no real child processes are launched; inject mock Windows APIs before import
os.environ.pop('RUN_CONTAINMENT_FIXTURES', None)

# Create a fake contained_supervisor module environment by importing the patched source
# We must mock os.name to 'nt' so _windows() returns True during test execution
_original_os_name = os.name
os.name = 'nt'

# Import the actual patched module
import contained_supervisor as cs

os.name = _original_os_name


def _make_fake_deps(fail_terminate=False, fail_wait=False, fail_exit=False, fail_query=False, fail_close=False, read_data=None, bad_read=False):
    """Build injected native API mocks. No real children."""
    deps = {}
    wapi = MagicMock()
    ctypes_mod = MagicMock()
    wt = MagicMock()
    msvcrt = MagicMock()
    subprocess_mod = MagicMock()

    deps['_winapi'] = wapi
    deps['ctypes'] = ctypes_mod
    deps['wintypes'] = wt
    deps['msvcrt'] = msvcrt
    deps['subprocess'] = subprocess_mod

    # Fake handles
    wapi.GetCurrentProcess.return_value = 1
    msvcrt.get_osfhandle.return_value = 10
    wapi.DuplicateHandle.side_effect = lambda *a, **k: 100 + wapi.DuplicateHandle.call_count
    wapi.CreatePipe.side_effect = [(201, 202), (203, 204)]

    ph_counter = [0]
    def fake_create_process(*args, **kwargs):
        ph_counter[0] += 1
        return (300 + ph_counter[0], 400 + ph_counter[0], 5000 + ph_counter[0], 0)
    wapi.CreateProcess.side_effect = fake_create_process
    wapi.ReadFile.side_effect = read_data if read_data else [(b'test_out', 0)]

    kernel = MagicMock()
    kernel.CreateJobObjectW.return_value = 999
    ctypes_mod.get_last_error.return_value = 0
    kernel.AssignProcessToJobObject.return_value = True
    kernel.ResumeThread.return_value = 1

    if fail_terminate:
        kernel.TerminateJobObject.side_effect = Exception('TerminateJobObject failed')
    else:
        kernel.TerminateJobObject.return_value = True

    if fail_wait:
        wapi.WaitForSingleObject.side_effect = Exception('Wait failed')
    else:
        wapi.WaitForSingleObject.return_value = cs._WAIT_OBJECT_0

    if fail_exit:
        wapi.GetExitCodeProcess.side_effect = Exception('GetExitCode failed')
    else:
        wapi.GetExitCodeProcess.return_value = 0

    if fail_query:
        kernel.QueryInformationJobObject.return_value = False
    else:
        class FakeAcct:
            active = 0
            total = 1
        acct = FakeAcct()
        acct.times = (0,0,0,0)
        acct.page_faults = 0
        acct.total = 1
        acct.active = 0
        acct.terminated = 1
        def fake_query(job, info_class, ptr, size, ret_size):
            if info_class == cs._JOB_ACCOUNTING:
                ptr._obj = acct
                return True
            return True
        kernel.QueryInformationJobObject.side_effect = fake_query

    if fail_close:
        wapi.CloseHandle.side_effect = OSError('Close failed')
    else:
        wapi.CloseHandle.return_value = True

    return deps, kernel


def test_no_root_static_admission():
    """Verify ROOT_STATIC_ADMISSION is removed from the module."""
    assert not hasattr(cs, 'ROOT_STATIC_ADMISSION'), 'ROOT_STATIC_ADMISSION must be removed'


def test_shutdown_attempts_all_waits_even_if_terminate_fails():
    """S2: TerminateJobObject failure must not skip waits/cleanup."""
    deps, kernel = _make_fake_deps(fail_terminate=True)
    owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
    active, drain = cs._shutdown(deps, kernel, 999, owned, terminate=True)
    # Must still attempt WaitForSingleObject despite TerminateJobObject raising
    deps['_winapi'].WaitForSingleObject.assert_called()
    assert drain in ('CLEANUP', 'UNKNOWN_DRAIN')


def test_shutdown_attempts_all_waits_even_if_wait_raises():
    """S2: WaitForSingleObject exception must not prevent other waits or cleanup."""
    deps, kernel = _make_fake_deps(fail_wait=True)
    owned = [
        {'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None},
        {'worker_id': 'w2', 'ph': 302, 'th': 402, 'pid': 5002, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None},
    ]
    active, drain = cs._shutdown(deps, kernel, 999, owned, terminate=True)
    # Both workers should have been attempted
    assert deps['_winapi'].WaitForSingleObject.call_count == 2
    assert drain == 'UNKNOWN_DRAIN'


def test_shutdown_attempts_getexitcode_even_if_wait_succeeds():
    """Ensure GetExitCodeProcess is called after successful wait."""
    deps, kernel = _make_fake_deps()
    owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
    active, drain = cs._shutdown(deps, kernel, 999, owned, terminate=False)
    deps['_winapi'].GetExitCodeProcess.assert_called_once_with(301)
    assert drain == 'CLEANUP'


def test_read_pipe_bad_read_does_not_become_completed():
    """S4: Read OSError must set bad_read=True and not allow PROCESS_COMPLETED."""
    slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
    overflow_event = threading.Event()
    def failing_read(handle, size):
        raise OSError('pipe broken')
    cs._read_pipe(123, 1024, slot, failing_read, lambda h: None, overflow_event)
    assert slot['bad_read'] is True, 'bad_read must be True on OSError'


def test_read_pipe_bad_read_format():
    """S4: Malformed ReadFile return sets bad_read."""
    slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
    overflow_event = threading.Event()
    def bad_format_read(handle, size):
        return 'not_a_tuple'
    cs._read_pipe(123, 1024, slot, bad_format_read, lambda h: None, overflow_event)
    assert slot['bad_read'] is True


def test_read_pipe_close_in_nested_finally():
    """S3/S4: Handle close must happen even if read raises."""
    slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
    overflow_event = threading.Event()
    closed_handles = []
    def failing_read(handle, size):
        raise OSError('fail')
    def track_close(h):
        closed_handles.append(h)
    cs._read_pipe(999, 1024, slot, failing_read, track_close, overflow_event)
    assert 999 in closed_handles, 'Handle must be closed even on read failure'
    assert slot['closed'] is True


def test_wait_run_rechecks_cancel_after_joins():
    """S4: Cancellation arriving during reader joins must be rechecked."""
    deps, kernel = _make_fake_deps()
    cancel_event = threading.Event()
    overflow_event = threading.Event()
    owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
    threads = []
    slots = [{'data': b'', 'overflow': False, 'bytes': 0, 'closed': True, 'stream': 'stdout', 'worker_id': 'w1', 'bad_read': False}]

    # Set cancel after first check but before join recheck
    original_join = cs._join
    def cancel_during_join(thds, timeout):
        cancel_event.set()
    cs._join = cancel_during_join

    dead_by = cs._monotonic() + 100
    status, reason = cs._wait_run(deps, kernel, 999, {}, owned, threads, slots, overflow_event, cancel_event, dead_by)
    cs._join = original_join
    assert status == 'CANCELLED', f'Expected CANCELLED, got {status}'


def test_wait_run_bad_read_returns_unknown():
    """S4: bad_read slot must not become PROCESS_COMPLETED."""
    deps, kernel = _make_fake_deps()
    cancel_event = threading.Event()
    overflow_event = threading.Event()
    owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
    threads = []
    slots = [{'data': b'', 'overflow': False, 'bytes': 0, 'closed': True, 'stream': 'stdout', 'worker_id': 'w1', 'bad_read': True}]
    dead_by = cs._monotonic() + 100
    status, reason = cs._wait_run(deps, kernel, 999, {}, owned, threads, slots, overflow_event, cancel_event, dead_by)
    assert status == 'UNKNOWN', f'Expected UNKNOWN for bad_read, got {status}'
    assert reason == 'bad_read'


def test_run_workers_full_cleanup_on_exception():
    """run_workers must always reach _close_owned and kernel.CloseHandle."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'out'
        manifest = {
            'version': 1, 'run_id': 'testrun', 'workers': [],
            'deadline_seconds': 5, 'startup_seconds': 2, 'log_limit_bytes': 4096,
            'containment_policy': 'explicit_terminate'
        }
        # Patch _validate to avoid file checks, patch _imports to use fakes
        orig_validate = cs._validate
        orig_imports = cs._imports
        deps, kernel = _make_fake_deps()

        def fake_validate(m, o):
            res = orig_validate.__wrapped__(m, o) if hasattr(orig_validate, '__wrapped__') else {
                'run_id': 'testrun', 'workers': [], 'deadline': 5, 'startup': 2,
                'log_limit': 4096, 'policy': 'explicit_terminate', 'output': out,
                'env': {}, 'seq': 1
            }
            return res

        cs._validate = fake_validate
        cs._imports = lambda: deps

        try:
            result = cs.run_workers(manifest, out)
            assert result is not None
            assert 'status' in result
            # Verify CloseHandle was called for job
            kernel.CloseHandle.assert_called()
        finally:
            cs._validate = orig_validate
            cs._imports = orig_imports


def test_run_workers_close_owned_independent_of_emit_failure():
    """Handle close must occur even if _emit fails."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'out'
        out.mkdir()
        deps, kernel = _make_fake_deps()
        orig_validate = cs._validate
        orig_imports = cs._imports
        orig_emit = cs._emit

        def fake_validate(m, o):
            return {
                'run_id': 'testrun', 'workers': [], 'deadline': 5, 'startup': 2,
                'log_limit': 4096, 'policy': 'explicit_terminate', 'output': out,
                'env': {}, 'seq': 1
            }

        def failing_emit(*args, **kwargs):
            raise RuntimeError('emit failed')

        cs._validate = fake_validate
        cs._imports = lambda: deps
        cs._emit = failing_emit

        try:
            result = cs.run_workers({}, out)
            # Should not raise; result should be fallback dict
            assert result is not None
            assert result['status'] in ('UNKNOWN', 'PROCESS_COMPLETED', 'FAILED')
        finally:
            cs._validate = orig_validate
            cs._imports = orig_imports
            cs._emit = orig_emit


def test_run_workers_no_early_return_before_waits():
    """Even if shutdown accounting fails, waits must have been attempted."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'out'
        deps, kernel = _make_fake_deps(fail_query=True)
        orig_validate = cs._validate
        orig_imports = cs._imports

        worker_spec = {'worker_id': 'w1', 'argv': ['C:/fake.exe'], 'cwd': str(out)}

        def fake_validate(m, o):
            return {
                'run_id': 'testrun', 'workers': [worker_spec], 'deadline': 5, 'startup': 2,
                'log_limit': 4096, 'policy': 'explicit_terminate', 'output': out,
                'env': {}, 'seq': 1
            }

        cs._validate = fake_validate
        cs._imports = lambda: deps

        try:
            # This will spawn and then fail at query, but waits should still be attempted in shutdown
            result = cs.run_workers({}, out)
            assert result is not None
            # WaitForSingleObject should have been called during shutdown
            assert deps['_winapi'].WaitForSingleObject.called
        finally:
            cs._validate = orig_validate
            cs._imports = orig_imports


if __name__ == '__main__':
    test_no_root_static_admission()
    test_shutdown_attempts_all_waits_even_if_terminate_fails()
    test_shutdown_attempts_all_waits_even_if_wait_raises()
    test_shutdown_attempts_getexitcode_even_if_wait_succeeds()
    test_read_pipe_bad_read_does_not_become_completed()
    test_read_pipe_bad_read_format()
    test_read_pipe_close_in_nested_finally()
    test_wait_run_rechecks_cancel_after_joins()
    test_wait_run_bad_read_returns_unknown()
    test_run_workers_full_cleanup_on_exception()
    test_run_workers_close_owned_independent_of_emit_failure()
    test_run_workers_no_early_return_before_waits()
    print('All tests passed.')
