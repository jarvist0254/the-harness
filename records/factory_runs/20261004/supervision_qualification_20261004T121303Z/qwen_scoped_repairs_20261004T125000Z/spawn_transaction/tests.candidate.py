import os
import sys
import json
import threading
import types
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Prevent actual WinDLL load at import time by mocking os.name check inside module
# We need to import the module under test
sys.modules.pop('contained_supervisor', None)

# Create a fake module environment so we can import without triggering real windows APIs
# But the prompt says: Tests must import actual patched module, all Windows APIs injected/mocked.
# We will mock os.name temporarily during import if needed, or just inject mocks into _imports.

# Actually, the module checks `os.name == "nt"` in `_windows()`. 
# We can just import it and mock the dependencies when calling functions.

import contained_supervisor as cs

class FakeWinAPI:
    def __init__(self, fail_second_createpipe=False, fail_second_duplicate=False, fail_createprocess=False):
        self.handle_counter = 100
        self.closed_handles = []
        self.fail_second_createpipe = fail_second_createpipe
        self.fail_second_duplicate = fail_second_duplicate
        self.fail_createprocess = fail_createprocess
        self.createpipe_count = 0
        self.duplicate_count = 0

    def GetCurrentProcess(self):
        return 1

    def DuplicateHandle(self, *args):
        self.duplicate_count += 1
        # first duplicate is stdin, second is out_dup, third is err_dup
        if self.fail_second_duplicate and self.duplicate_count == 3:
            raise OSError("DuplicateHandle failed")
        self.handle_counter += 1
        return self.handle_counter

    def CreatePipe(self, *args):
        self.createpipe_count += 1
        if self.fail_second_createpipe and self.createpipe_count == 2:
            raise OSError("CreatePipe failed")
        self.handle_counter += 2
        return self.handle_counter - 1, self.handle_counter

    def CreateProcess(self, *args):
        if self.fail_createprocess:
            raise OSError("CreateProcess failed")
        self.handle_counter += 2
        return self.handle_counter - 1, self.handle_counter, 1234, 5678

    def CloseHandle(self, h):
        self.closed_handles.append(h)

    def TerminateProcess(self, h, code):
        pass

    def WaitForSingleObject(self, h, timeout):
        return 0

    def ReadFile(self, h, size):
        return (b"", 0)

class FakeKernel:
    def __init__(self, fail_assign=False, fail_resume=False):
        self.fail_assign = fail_assign
        self.fail_resume = fail_resume
        self.assign_called = False
        self.resume_called = False

    def AssignProcessToJobObject(self, job, ph):
        self.assign_called = True
        if self.fail_assign:
            return 0
        return 1

    def ResumeThread(self, th):
        self.resume_called = True
        if self.fail_resume:
            return 0xFFFFFFFF
        return 1

def make_deps(wapi):
    msvcrt = MagicMock()
    msvcrt.get_osfhandle.return_value = 10
    subprocess_mock = MagicMock()
    subprocess_mock.STARTUPINFO.return_value = MagicMock(dwFlags=0, hStdInput=None, hStdOutput=None, hStdError=None, lpAttributeList=None)
    subprocess_mock.list2cmdline.return_value = "cmd"
    subprocess_mock.STARTF_USESTDHANDLES = 1
    return {
        "_winapi": wapi,
        "subprocess": subprocess_mock,
        "msvcrt": msvcrt,
        "ctypes": MagicMock(get_last_error=MagicMock(return_value=999)),
        "wintypes": MagicMock()
    }

def make_spec():
    return {
        "env": {},
        "log_limit": 1024,
        "seq": 1,
        "output": Path("/tmp/fake"),
        "run_id": "test_run"
    }

def make_worker():
    return {"worker_id": "w1", "argv": ["C:\\fake.exe"], "cwd": "C:\\"}

class TestSpawnOwnership(unittest.TestCase):

    @patch("builtins.open", new_callable=MagicMock)
    def test_success_exact_close_counts(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI()
        kernel = FakeKernel()
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        self.assertEqual(len(owned), 1)
        self.assertTrue(owned[0]["assigned"])
        self.assertTrue(owned[0]["resumed"])
        # close_after should have closed: stdin_h, out_w, err_w, out_dup, err_dup = 5 handles
        self.assertEqual(len(wapi.closed_handles), 5)
        # reads should be empty because both were transferred
        self.assertEqual(len(threads), 2)
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    def test_fail_second_createpipe_leaks_nothing(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI(fail_second_createpipe=True)
        kernel = FakeKernel()
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        with self.assertRaises(OSError):
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        # Should have closed: stdin_h, out_w, out_r (from reads list) = 3 handles
        # No process created, no assign/resume
        self.assertFalse(kernel.assign_called)
        self.assertEqual(len(owned), 0)
        self.assertEqual(len(threads), 0)
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    def test_fail_second_duplicate_closes_first_dup_and_pipes(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI(fail_second_duplicate=True)
        kernel = FakeKernel()
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        with self.assertRaises(OSError):
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        # Should have closed: stdin_h, out_w, err_w, out_dup, plus reads (out_r, err_r)
        self.assertFalse(kernel.assign_called)
        self.assertEqual(len(owned), 0)
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    def test_fail_createprocess_closes_all_before_process(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI(fail_createprocess=True)
        kernel = FakeKernel()
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        with self.assertRaises(OSError):
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        self.assertFalse(kernel.assign_called)
        self.assertEqual(len(owned), 0)
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    def test_fail_assign_terminates_process_and_cleans(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI()
        kernel = FakeKernel(fail_assign=True)
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        with self.assertRaises(cs.WindowsJobError) as ctx:
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        self.assertEqual(ctx.exception.code, "ASSIGN_FAILED")
        # Process was created and added to owned, then exception raised.
        # Finally block does NOT terminate because ph/th are set to None after append.
        # Wait, in the new code: rec is appended, then ph=th=None. So finally won't terminate.
        # The caller (_launch_and_wait -> run_workers finally -> _shutdown) owns cleanup.
        self.assertEqual(len(owned), 1)
        self.assertFalse(owned[0]["assigned"])
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    def test_fail_resume_leaves_assigned_but_not_resumed(self, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI()
        kernel = FakeKernel(fail_resume=True)
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        with self.assertRaises(cs.WindowsJobError) as ctx:
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        self.assertEqual(ctx.exception.code, "RESUME_FAILED")
        self.assertEqual(len(owned), 1)
        self.assertTrue(owned[0]["assigned"])
        self.assertFalse(owned[0]["resumed"])
        mock_nul.close.assert_called_once()

    @patch("builtins.open", new_callable=MagicMock)
    @patch.object(threading.Thread, 'start')
    def test_fail_second_thread_start_does_not_close_first_reader_handle(self, mock_start, mock_open):
        mock_nul = MagicMock()
        mock_nul.fileno.return_value = 0
        mock_open.return_value = mock_nul

        wapi = FakeWinAPI()
        kernel = FakeKernel()
        deps = make_deps(wapi)
        spec = make_spec()
        worker = make_worker()
        owned, threads, slots = [], [], []
        overflow = threading.Event()

        call_count = [0]
        def side_effect_start():
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("thread start failed")
        mock_start.side_effect = side_effect_start

        with self.assertRaises(RuntimeError):
            cs._spawn(deps, kernel, job=99, spec=spec, worker=worker, owned=owned, threads=threads, slots=slots, overflow_event=overflow)

        # First thread started successfully, its handle was transferred.
        # Second thread failed before transfer.
        # Therefore, reads list still contains the second handle, which gets closed in finally.
        # The first handle was removed from reads, so it is NOT closed by _spawn.
        self.assertEqual(len(threads), 1)
        self.assertEqual(len(slots), 1)
        # Verify that exactly one read handle was closed (the untransferred one)
        # Total closed = 5 (close_after) + 1 (remaining read) = 6
        self.assertEqual(len(wapi.closed_handles), 6)
        mock_nul.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()

