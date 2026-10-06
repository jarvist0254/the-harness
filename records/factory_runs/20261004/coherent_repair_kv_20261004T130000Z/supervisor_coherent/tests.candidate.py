import os
import sys
import json
import threading
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ.pop('RUN_CONTAINMENT_FIXTURES', None)
_original_os_name = os.name
os.name = 'nt'

import contained_supervisor as cs

os.name = _original_os_name

FORBIDDEN = []
def deny(label):
    def f(*a, **k):
        FORBIDDEN.append(label)
        raise AssertionError('REAL_NATIVE_OR_PROCESS_FORBIDDEN ' + label)
    return f

import subprocess, ctypes
subprocess.Popen = deny('subprocess.Popen')
subprocess.run = deny('subprocess.run')
os.system = deny('os.system')
ctypes.WinDLL = deny('ctypes.WinDLL')


class FakeAPI:
    def __init__(self, fail_pipe=None, fail_dup=None, bad_read=False, wait_error=False, fail_assign=False, fail_resume=False, fail_terminate=False, fail_query=False, fail_exit=False):
        self.calls = []
        self.next = 100
        self.pipe_n = 0
        self.dup_n = 0
        self.fail_pipe = fail_pipe
        self.fail_dup = fail_dup
        self.bad_read = bad_read
        self.wait_error = wait_error
        self.fail_assign = fail_assign
        self.fail_resume = fail_resume
        self.fail_terminate = fail_terminate
        self.fail_query = fail_query
        self.fail_exit = fail_exit
        self.alloc = []
        self.proc = []

    def new(self, kind):
        self.next += 1
        self.alloc.append((kind, self.next))
        return self.next

    def GetCurrentProcess(self):
        return -1

    def DuplicateHandle(self, *args):
        self.dup_n += 1
        if self.dup_n == self.fail_dup:
            raise OSError('injected duplicate failure')
        return self.new('duplicate')

    def CreatePipe(self, *args):
        self.pipe_n += 1
        if self.pipe_n == self.fail_pipe:
            raise OSError('injected pipe failure')
        return self.new('read'), self.new('write')

    def CreateProcess(self, *args):
        ph, th = self.new('process'), self.new('thread')
        self.proc.append((ph, th))
        self.calls.append(('fake_create_process', ph, th))
        return ph, th, 10000 + ph, 1

    def CloseHandle(self, h):
        self.calls.append(('close', h))

    def ReadFile(self, *args):
        if self.bad_read:
            return ('INVALID_DATA', 0)
        return (b'', 109)

    def TerminateProcess(self, h, code):
        self.calls.append(('terminate_process', h))

    def WaitForSingleObject(self, h, ms):
        self.calls.append(('wait', h, ms))
        if self.wait_error:
            raise OSError('injected wait failure')
        return 0

    def GetExitCodeProcess(self, h):
        self.calls.append(('exit_code', h))
        if self.fail_exit:
            raise OSError('injected exit failure')
        return 0


class FakeKernel:
    def __init__(self, fail_terminate=False, fail_assign=False, fail_resume=False, fail_query=False):
        self.calls = []
        self.fail_terminate = fail_terminate
        self.fail_assign = fail_assign
        self.fail_resume = fail_resume
        self.fail_query = fail_query

    def CreateJobObjectW(self, *args):
        self.calls.append(('create_job',))
        return 900

    def AssignProcessToJobObject(self, j, h):
        self.calls.append(('assign', h))
        if self.fail_assign:
            return 0
        return 1

    def ResumeThread(self, h):
        self.calls.append(('resume', h))
        if self.fail_resume:
            return 0xFFFFFFFF
        return 1

    def TerminateJobObject(self, j, code):
        self.calls.append(('terminate_job',))
        if self.fail_terminate:
            raise OSError('injected terminate failure')
        return 1

    def CloseHandle(self, h):
        self.calls.append(('close_job', h))
        return 1

    def QueryInformationJobObject(self, *args):
        if self.fail_query:
            raise OSError('injected query failure')
        return 0


class FakeCT:
    def set_last_error(self, x):
        pass

    def get_last_error(self):
        return 5


class Startup:
    def __init__(self):
        self.dwFlags = 0


class ImmediateThread:
    count = 0
    fail_second = False

    def __init__(self, target, args, daemon):
        self.target = target
        self.args = args

    def start(self):
        type(self).count += 1
        if type(self).fail_second and type(self).count == 2:
            raise RuntimeError('injected second reader start')
        self.target(*self.args)

    def is_alive(self):
        return False

    def join(self, timeout):
        pass


def deps(api):
    return {
        '_winapi': api,
        'ctypes': FakeCT(),
        'msvcrt': types.SimpleNamespace(get_osfhandle=lambda fd: 3),
        'subprocess': types.SimpleNamespace(STARTUPINFO=Startup, STARTF_USESTDHANDLES=256, list2cmdline=lambda av: ' '.join(av))
    }


def spec(out):
    return {
        'run_id': 'adversarial',
        'workers': [{'worker_id': 'w1', 'argv': ['C:\\fake.exe'], 'cwd': str(out.parent)}],
        'env': {},
        'deadline': 10,
        'startup': 5,
        'log_limit': 1024,
        'policy': 'explicit_terminate',
        'output': out,
        'seq': 1
    }


def threading_event():
    return cs.threading.Event()


class SupervisorCases(unittest.TestCase):
    def run_fake(self, api, k, account=lambda *a: (0, 1)):
        with tempfile.TemporaryDirectory() as tmp:
            sp = spec(Path(tmp) / 'output')
            ImmediateThread.count = 0
            ImmediateThread.fail_second = False
            with patch.object(cs, '_validate', return_value=sp), \
                 patch.object(cs, '_imports', return_value=deps(api)), \
                 patch.object(cs, '_kernel', return_value=k), \
                 patch.object(cs, '_accounting', side_effect=account), \
                 patch.object(cs.threading, 'Thread', ImmediateThread):
                return cs.run_workers({}, str(sp['output']))

    def spawn_fake(self, api, fail_second=False, fail_assign=False, fail_resume=False):
        k = FakeKernel(fail_assign=fail_assign, fail_resume=fail_resume)
        owned = []
        threads = []
        slots = []
        ImmediateThread.count = 0
        ImmediateThread.fail_second = fail_second
        with tempfile.TemporaryDirectory() as tmp, patch.object(cs.threading, 'Thread', ImmediateThread):
            sp = spec(Path(tmp) / 'output')
            try:
                with self.assertRaises((OSError, RuntimeError, cs.WindowsJobError)):
                    cs._spawn(deps(api), k, 900, sp, sp['workers'][0], owned, threads, slots, threading_event())
            finally:
                pass
        return api, k, owned, threads, slots

    def test_no_root_static_admission(self):
        self.assertFalse(hasattr(cs, 'ROOT_STATIC_ADMISSION'))

    def test_second_pipe_failure_no_leaks(self):
        api, k, owned, threads, slots = self.spawn_fake(FakeAPI(fail_pipe=2))
        closed = [c[1] for c in api.calls if c[0] == 'close']
        alloc_handles = {h for _, h in api.alloc}
        self.assertTrue(alloc_handles.issubset(set(closed)))
        self.assertEqual(len(owned), 0)

    def test_second_writer_duplicate_failure_no_leaks(self):
        api, k, owned, threads, slots = self.spawn_fake(FakeAPI(fail_dup=3))
        closed = [c[1] for c in api.calls if c[0] == 'close']
        alloc_handles = {h for _, h in api.alloc}
        self.assertTrue(alloc_handles.issubset(set(closed)))
        self.assertEqual(len(owned), 0)

    def test_second_reader_start_no_double_close(self):
        api, k, owned, threads, slots = self.spawn_fake(FakeAPI(), fail_second=True)
        reads = [h for kind, h in api.alloc if kind == 'read']
        closed = [c[1] for c in api.calls if c[0] == 'close']
        self.assertTrue(all(closed.count(h) <= 1 for h in reads))
        self.assertEqual(len(threads), 1)
        self.assertEqual(len(slots), 1)

    def test_failed_job_termination_still_waits_roots(self):
        api = FakeAPI()
        k = FakeKernel(fail_terminate=True)
        owned = [{'worker_id': 'w1', 'ph': 123, 'th': 456, 'pid': 10000, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
        r = cs._shutdown(deps(api), k, 900, owned, True)
        self.assertTrue(any(c[0] == 'wait' and c[1] == 123 for c in api.calls))
        self.assertIn(r[1], ('CLEANUP', 'UNKNOWN_DRAIN'))

    def test_wait_exception_still_closes_owned_handles(self):
        api = FakeAPI(wait_error=True)
        k = FakeKernel()
        result = self.run_fake(api, k)
        roots = [h for pair in api.proc for h in pair]
        closed = [c[1] for c in api.calls if c[0] == 'close']
        self.assertTrue(roots and all(h in closed for h in roots))
        self.assertNotEqual(result['status'], 'PROCESS_COMPLETED')

    def test_query_exception_still_closes_owned_handles(self):
        api = FakeAPI()
        k = FakeKernel(fail_query=True)
        result = self.run_fake(api, k)
        roots = [h for pair in api.proc for h in pair]
        closed = [c[1] for c in api.calls if c[0] == 'close']
        self.assertTrue(roots and all(h in closed for h in roots))
        self.assertNotEqual(result['status'], 'PROCESS_COMPLETED')

    def test_bad_read_never_process_completed(self):
        r = self.run_fake(FakeAPI(bad_read=True), FakeKernel())
        self.assertNotEqual(r['status'], 'PROCESS_COMPLETED')

    def test_assign_failure_terminates_process(self):
        api, k, owned, threads, slots = self.spawn_fake(FakeAPI(), fail_assign=True)
        self.assertTrue(any(c[0] == 'terminate_process' for c in api.calls))
        self.assertEqual(len(owned), 1)
        self.assertFalse(owned[0]['assigned'])

    def test_resume_failure_leaves_assigned(self):
        api, k, owned, threads, slots = self.spawn_fake(FakeAPI(), fail_resume=True)
        self.assertEqual(len(owned), 1)
        self.assertTrue(owned[0]['assigned'])
        self.assertFalse(owned[0]['resumed'])

    def test_shutdown_attempts_all_waits_even_if_wait_raises(self):
        api = FakeAPI(wait_error=True)
        k = FakeKernel()
        owned = [
            {'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None},
            {'worker_id': 'w2', 'ph': 302, 'th': 402, 'pid': 5002, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None},
        ]
        active, drain = cs._shutdown(deps(api), k, 999, owned, True)
        self.assertEqual(api.calls.count(('wait', 301, api.calls[1][2])) + api.calls.count(('wait', 302, api.calls[3][2])), 0)
        wait_calls = [c for c in api.calls if c[0] == 'wait']
        self.assertEqual(len(wait_calls), 2)
        self.assertEqual(drain, 'UNKNOWN_DRAIN')

    def test_read_pipe_bad_read_sets_flag(self):
        slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
        overflow_event = threading.Event()
        def failing_read(handle, size):
            raise OSError('pipe broken')
        cs._read_pipe(123, 1024, slot, failing_read, lambda h: None, overflow_event)
        self.assertTrue(slot['bad_read'])

    def test_read_pipe_bad_format_sets_flag(self):
        slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
        overflow_event = threading.Event()
        def bad_format_read(handle, size):
            return 'not_a_tuple'
        cs._read_pipe(123, 1024, slot, bad_format_read, lambda h: None, overflow_event)
        self.assertTrue(slot['bad_read'])

    def test_read_pipe_close_always_called(self):
        slot = {'data': b'', 'overflow': False, 'bytes': 0, 'closed': False, 'stream': 'stdout', 'worker_id': 'w1'}
        overflow_event = threading.Event()
        closed_handles = []
        def failing_read(handle, size):
            raise OSError('fail')
        def track_close(h):
            closed_handles.append(h)
        cs._read_pipe(999, 1024, slot, failing_read, track_close, overflow_event)
        self.assertIn(999, closed_handles)
        self.assertTrue(slot['closed'])

    def test_wait_run_rechecks_cancel_after_joins(self):
        api = FakeAPI()
        k = FakeKernel()
        cancel_event = threading.Event()
        overflow_event = threading.Event()
        owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
        threads = []
        slots = [{'data': b'', 'overflow': False, 'bytes': 0, 'closed': True, 'stream': 'stdout', 'worker_id': 'w1', 'bad_read': False}]
        original_join = cs._join
        def cancel_during_join(thds, timeout):
            cancel_event.set()
        cs._join = cancel_during_join
        dead_by = cs._monotonic() + 100
        status, reason = cs._wait_run(deps(api), k, 999, {}, owned, threads, slots, overflow_event, cancel_event, dead_by)
        cs._join = original_join
        self.assertEqual(status, 'CANCELLED')

    def test_wait_run_bad_read_returns_unknown(self):
        api = FakeAPI()
        k = FakeKernel()
        cancel_event = threading.Event()
        overflow_event = threading.Event()
        owned = [{'worker_id': 'w1', 'ph': 301, 'th': 401, 'pid': 5001, 'assigned': True, 'resumed': True, 'exit_code': None, 'wait': None}]
        threads = []
        slots = [{'data': b'', 'overflow': False, 'bytes': 0, 'closed': True, 'stream': 'stdout', 'worker_id': 'w1', 'bad_read': True}]
        dead_by = cs._monotonic() + 100
        status, reason = cs._wait_run(deps(api), k, 999, {}, owned, threads, slots, overflow_event, cancel_event, dead_by)
        self.assertEqual(status, 'UNKNOWN')
        self.assertEqual(reason, 'bad_read')

    def test_run_workers_returns_fallback_on_emit_failure(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'out'
            api = FakeAPI()
            k = FakeKernel()
            sp = spec(out)
            orig_emit = cs._emit
            def failing_emit(*args, **kwargs):
                raise RuntimeError('emit failed')
            with patch.object(cs, '_validate', return_value=sp), \
                 patch.object(cs, '_imports', return_value=deps(api)), \
                 patch.object(cs, '_kernel', return_value=k), \
                 patch.object(cs, '_accounting', return_value=(0, 1)), \
                 patch.object(cs.threading, 'Thread', ImmediateThread), \
                 patch.object(cs, '_emit', failing_emit):
                result = cs.run_workers({}, str(out))
            self.assertIsNotNone(result)
            self.assertIn('status', result)

    def test_run_workers_close_owned_independent_of_shutdown_exception(self):
        api = FakeAPI()
        k = FakeKernel()
        sp_dict = None
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'out'
            sp_dict = spec(out)
            orig_shutdown = cs._shutdown
            def failing_shutdown(*args, **kwargs):
                raise RuntimeError('shutdown exploded')
            with patch.object(cs, '_validate', return_value=sp_dict), \
                 patch.object(cs, '_imports', return_value=deps(api)), \
                 patch.object(cs, '_kernel', return_value=k), \
                 patch.object(cs, '_accounting', return_value=(0, 1)), \
                 patch.object(cs.threading, 'Thread', ImmediateThread), \
                 patch.object(cs, '_shutdown', failing_shutdown):
                result = cs.run_workers({}, str(out))
        roots = [h for pair in api.proc for h in pair]
        closed = [c[1] for c in api.calls if c[0] == 'close']
        self.assertTrue(roots and all(h in closed for h in roots))
        self.assertIsNotNone(result)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() and not FORBIDDEN else 1)

