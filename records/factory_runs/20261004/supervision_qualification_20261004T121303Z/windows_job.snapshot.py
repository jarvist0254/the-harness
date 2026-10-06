"""Recoverable Windows process containment; closing a handle does not cancel work.

Launch uses CPython's CreateProcessW binding with CREATE_SUSPENDED. Assignment
precedes ResumeThread, including on failure paths. Jobs use default limits:
neither breakaway nor kill-on-last-handle-close is enabled.

Recovery requires a cooperating wrapper to open and retain its own job handle
and acknowledge readiness before the controller closes its handle. Although
members survive last-handle closure, Windows removes the name at that point.
The wrapper must retain its handle until its descendants have drained.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from contextlib import ExitStack
from ctypes import wintypes
from pathlib import Path


class WindowsJobError(RuntimeError):
    def __init__(self, code: str, winerror: int | None = None):
        self.code = code
        self.winerror = winerror
        super().__init__(code if winerror is None else f"{code}: winerror={winerror}")


def _api():
    if os.name != "nt":
        raise WindowsJobError("WINDOWS_JOB_UNSUPPORTED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        "OpenJobObjectW": (
            [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR],
            wintypes.HANDLE,
        ),
        "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        "QueryInformationJobObject": (
            [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.c_void_p,
            ],
            wintypes.BOOL,
        ),
        "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
        "OpenProcess": (
            [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD],
            wintypes.HANDLE,
        ),
        "IsProcessInJob": (
            [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)],
            wintypes.BOOL,
        ),
        "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes = args
        function.restype = result
    return kernel


def _error(code):
    error = ctypes.get_last_error()
    return WindowsJobError("WINDOWS_JOB_ACCESS_DENIED" if error == 5 else code, error)


class JobProcess:
    """Owned, non-inheritable process handle. Closing it does not terminate work."""

    def __init__(self, handle, pid):
        self._handle = handle
        self.pid = pid

    def poll(self):
        import _winapi

        if self._handle is None:
            raise WindowsJobError("WINDOWS_PROCESS_CLOSED")
        if _winapi.WaitForSingleObject(self._handle, 0) == 258:
            return None
        return _winapi.GetExitCodeProcess(self._handle)

    def wait(self, timeout=10):
        deadline = time.monotonic() + timeout
        while (result := self.poll()) is None:
            if time.monotonic() >= deadline:
                raise WindowsJobError("WINDOWS_PROCESS_WAIT_TIMEOUT")
            time.sleep(0.02)
        return result

    def close(self):
        if self._handle is not None:
            import _winapi

            _winapi.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class WindowsJob:
    def __init__(self, name, handle, kernel):
        self.name = name
        self._handle = handle
        self._kernel = kernel
        self._drain_handles = []
        self._drain_started = False
        self._drain_unknown = False
        self._drain_total = None
        self._drain_complete = False
        self._drain_count = 0
        self.termination_initiated = False
        self.assignment_sealed = False

    @classmethod
    def create(cls, name):
        kernel = _api()
        if not isinstance(name, str) or not name or "\0" in name:
            raise WindowsJobError("WINDOWS_JOB_INVALID_NAME")
        ctypes.set_last_error(0)
        handle = kernel.CreateJobObjectW(None, name)
        if not handle:
            raise _error("WINDOWS_JOB_CREATE_FAILED")
        if ctypes.get_last_error() == 183:
            kernel.CloseHandle(handle)
            raise WindowsJobError("WINDOWS_JOB_ALREADY_EXISTS", 183)
        return cls(name, handle, kernel)

    @classmethod
    def open(cls, name):
        kernel = _api()
        if not isinstance(name, str) or not name or "\0" in name:
            raise WindowsJobError("WINDOWS_JOB_INVALID_NAME")
        handle = kernel.OpenJobObjectW(1 | 4 | 8, False, name)
        if not handle:
            if ctypes.get_last_error() == 2:
                raise WindowsJobError("WINDOWS_JOB_NOT_FOUND", 2)
            raise _error("WINDOWS_JOB_OPEN_FAILED")
        return cls(name, handle, kernel)

    @property
    def closed(self):
        return self._handle is None

    def _checked_handle(self):
        if self.closed:
            raise WindowsJobError("WINDOWS_JOB_CLOSED")
        return self._handle

    def _assign(self, process_handle):
        if self.assignment_sealed:
            raise WindowsJobError("WINDOWS_JOB_ASSIGNMENT_SEALED")
        if not self._kernel.AssignProcessToJobObject(
            self._checked_handle(), process_handle
        ):
            raise _error("WINDOWS_JOB_ASSIGN_FAILED")

    def launch(
        self,
        command,
        *,
        cwd=None,
        environment=None,
        stdout_path=None,
        stderr_path=None,
        detached=False,
        lifetime=None,
    ):
        """Launch an explicit executable; environment replaces the inherited map.

        Only three duplicated standard handles are inherited when log files are
        requested. Otherwise handle inheritance is disabled. Standard input is
        always NUL for logged launches. Output files append binary data.
        """
        self._checked_handle()
        import _winapi
        import msvcrt

        if isinstance(command, (str, bytes)) or not command:
            raise WindowsJobError("WINDOWS_JOB_INVALID_COMMAND")
        command = [os.fspath(part) for part in command]
        if not Path(command[0]).is_absolute() or any("\0" in part for part in command):
            raise WindowsJobError("WINDOWS_JOB_INVALID_COMMAND")
        startup = subprocess.STARTUPINFO()
        process_handle = thread_handle = None
        with ExitStack() as stack:
            inherit = stdout_path is not None or stderr_path is not None
            if inherit:
                handles = []
                for path, mode in [
                    (os.devnull, "rb"),
                    (stdout_path or os.devnull, "ab"),
                    (stderr_path or os.devnull, "ab"),
                ]:
                    stream = stack.enter_context(open(path, mode))
                    current = _winapi.GetCurrentProcess()
                    handle = _winapi.DuplicateHandle(
                        current,
                        msvcrt.get_osfhandle(stream.fileno()),
                        current,
                        0,
                        True,
                        2,
                    )
                    stack.callback(_winapi.CloseHandle, handle)
                    handles.append(handle)
                startup.dwFlags |= subprocess.STARTF_USESTDHANDLES
                startup.hStdInput, startup.hStdOutput, startup.hStdError = handles
                startup.lpAttributeList = {"handle_list": handles}
            try:
                process_handle, thread_handle, pid, _ = _winapi.CreateProcess(
                    command[0],
                    subprocess.list2cmdline(command),
                    None,
                    None,
                    inherit,
                    0x00000004
                    | (0x00000008 if detached else 0x08000000)
                    | (0x00000001 if lifetime is not None else 0),
                    environment,
                    os.fspath(cwd) if cwd is not None else None,
                    startup,
                )
                self._assign(process_handle)
                if lifetime is not None:
                    lifetime.capture(pid, process_handle, root=True)
                if self._kernel.ResumeThread(thread_handle) == 0xFFFFFFFF:
                    raise _error("WINDOWS_JOB_RESUME_FAILED")
                result = JobProcess(process_handle, pid)
                process_handle = None
                return result
            except OSError as exc:
                raise WindowsJobError(
                    "WINDOWS_JOB_LAUNCH_FAILED", exc.winerror
                ) from exc
            finally:
                if thread_handle is not None:
                    _winapi.CloseHandle(thread_handle)
                if process_handle is not None:
                    try:
                        _winapi.TerminateProcess(process_handle, 1)
                        if lifetime is not None:
                            # Creation and pumping must share a thread. Never wait
                            # behind a pending debug exit, including failed launch.
                            deadline = time.monotonic() + 10
                            while (
                                _winapi.WaitForSingleObject(process_handle, 0) == 258
                                and time.monotonic() < deadline
                            ):
                                lifetime.pump(10)
                        if _winapi.WaitForSingleObject(process_handle, 10000) != 0:
                            raise WindowsJobError("WINDOWS_JOB_CLEANUP_TIMEOUT")
                    finally:
                        _winapi.CloseHandle(process_handle)

    def active_process_ids(self):
        capacity = 16
        while capacity <= 1048576:

            class ProcessList(ctypes.Structure):
                _fields_ = [
                    ("assigned", wintypes.DWORD),
                    ("count", wintypes.DWORD),
                    ("pids", ctypes.c_size_t * capacity),
                ]

            data = ProcessList()
            if self._kernel.QueryInformationJobObject(
                self._checked_handle(), 3, ctypes.byref(data), ctypes.sizeof(data), None
            ):
                return list(data.pids[: data.count])
            if ctypes.get_last_error() != 234:
                raise _error("WINDOWS_JOB_QUERY_FAILED")
            capacity = max(capacity * 2, data.assigned)
        raise WindowsJobError("WINDOWS_JOB_QUERY_LIMIT")

    def total_processes(self):
        """Cumulative assignments detect members missed across capture/termination."""

        class Accounting(ctypes.Structure):
            _fields_ = [
                ("times", ctypes.c_longlong * 4),
                ("page_faults", wintypes.DWORD),
                ("total", wintypes.DWORD),
                ("active", wintypes.DWORD),
                ("terminated", wintypes.DWORD),
            ]

        data = Accounting()
        if not self._kernel.QueryInformationJobObject(
            self._checked_handle(),
            1,
            ctypes.byref(data),
            ctypes.sizeof(data),
            None,
        ):
            raise _error("WINDOWS_JOB_QUERY_FAILED")
        return data.total

    def _capture_drain(self):
        self._drain_started = True
        self._drain_total = self.total_processes()
        pids = self.active_process_ids()
        if len(pids) > 4096:
            raise WindowsJobError("WINDOWS_JOB_DRAIN_CAPTURE_LIMIT")
        for pid in pids:
            handle = self._kernel.OpenProcess(0x100000 | 0x0400, False, pid)
            if not handle:
                raise _error("WINDOWS_JOB_MEMBER_OPEN_FAILED")
            try:
                contained = wintypes.BOOL()
                if (
                    not self._kernel.IsProcessInJob(
                        handle,
                        self._checked_handle(),
                        ctypes.byref(contained),
                    )
                    or not contained.value
                ):
                    raise WindowsJobError("WINDOWS_JOB_MEMBER_IDENTITY_UNKNOWN")
                # The handle keeps this exact process object alive despite PID reuse.
                self._drain_handles.append(handle)
                self._drain_count += 1
                handle = None
            finally:
                if handle is not None:
                    self._kernel.CloseHandle(handle)
        if self.total_processes() != self._drain_total:
            raise WindowsJobError("WINDOWS_JOB_DRAIN_UNKNOWN")

    def terminate(self, exit_code=1):
        """Initiate whole-job termination even if positive-drain capture fails.

        No waiting here: wrappers may terminate the job containing themselves.
        The external caller must separately wait_empty before certifying a drain.
        """
        self._checked_handle()
        self.prepare_drain()
        if not self._kernel.TerminateJobObject(self._checked_handle(), exit_code):
            raise _error("WINDOWS_JOB_TERMINATE_FAILED")
        self.termination_initiated = True

    def prepare_drain(self):
        """Capture immediately before forced termination can remove members."""
        if not self._drain_started:
            try:
                self._capture_drain()
            except Exception:
                self._drain_started = True
                self._drain_unknown = True

    def drain_proof(self):
        # Stable totals prove no additions, not that departed objects signaled.
        # Without lifetime monitoring, only complete lifetime capture authorizes
        # a whole-tree certificate. wait_empty remains usable for ordinary cleanup.
        if (
            not self.termination_initiated
            or not self._drain_complete
            or self._drain_unknown
            or self._drain_count != self._drain_total
        ):
            raise WindowsJobError("WINDOWS_JOB_DRAIN_UNKNOWN")
        return {
            "exact_handles_signaled": True,
            "total_processes": self._drain_total,
            "captured_members": self._drain_count,
        }

    def _close_drain_handles(self):
        for handle in self._drain_handles:
            self._kernel.CloseHandle(handle)
        self._drain_handles.clear()

    def wait_empty(self, timeout=10):
        deadline = time.monotonic() + timeout
        if self._drain_started:
            if self._drain_unknown or self.total_processes() != self._drain_total:
                self._drain_unknown = True
                raise WindowsJobError("WINDOWS_JOB_DRAIN_UNKNOWN")
            for handle in self._drain_handles:
                remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                status = self._kernel.WaitForSingleObject(handle, remaining_ms)
                if status == 258:
                    raise WindowsJobError("WINDOWS_JOB_WAIT_TIMEOUT")
                if status != 0:
                    self._drain_unknown = True
                    raise WindowsJobError("WINDOWS_JOB_DRAIN_UNKNOWN")
        while self.active_process_ids():
            if time.monotonic() >= deadline:
                raise WindowsJobError("WINDOWS_JOB_WAIT_TIMEOUT")
            time.sleep(0.02)
        if self._drain_started:
            if self.total_processes() != self._drain_total:
                self._drain_unknown = True
                raise WindowsJobError("WINDOWS_JOB_DRAIN_UNKNOWN")
            self._drain_complete = True
            self._close_drain_handles()

    def close(self):
        self._close_drain_handles()
        if not self.closed:
            if not self._kernel.CloseHandle(self._handle):
                raise _error("WINDOWS_JOB_CLOSE_FAILED")
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
