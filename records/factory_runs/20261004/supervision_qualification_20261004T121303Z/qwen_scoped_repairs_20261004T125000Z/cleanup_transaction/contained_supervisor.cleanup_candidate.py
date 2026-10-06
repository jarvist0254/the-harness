"""Standalone Windows contained-worker supervisor.

Import is side-effect free: no _winapi, ctypes, WinDLL, or processes at import.
ROOT_STATIC_ADMISSION admits that import safety only. Process fixtures still
require Windows and RUN_CONTAINMENT_FIXTURES=1. This module does not import PyRe.
Explicit terminate is the default. No kill-on-close is installed unless requested.
Closing the controller job handle is not a drain certificate. Without a cooperating
wrapper holding its own job handle, controller loss is UNKNOWN_INTERRUPTED.
No PID reattach and no replay.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path

_RECEIPT_MAX = 131072
_CREATE_SUSPENDED = 0x00000004
_CREATE_NO_WINDOW = 0x08000000
_JOB_LIMIT_KILL_ON_CLOSE = 0x2000
_JOB_EXTENDED_LIMIT = 9
_JOB_ACCOUNTING = 1
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 258
_ENV_KEYS = ("SystemRoot", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP")


class WindowsJobError(RuntimeError):
    def __init__(self, code, winerror=None):
        self.code = code
        self.winerror = winerror
        super().__init__(code if winerror is None else f"{code}: winerror={winerror}")


def _windows():
    return os.name == "nt"


def _monotonic():
    return time.monotonic()


def _sleep(seconds):
    time.sleep(seconds)


def _imports():
    import _winapi
    import ctypes
    import msvcrt
    import subprocess
    from ctypes import wintypes
    return {"_winapi": _winapi, "ctypes": ctypes, "wintypes": wintypes, "msvcrt": msvcrt, "subprocess": subprocess}


def _kernel(deps):
    ctypes = deps["ctypes"]
    wt = deps["wintypes"]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    specs = {
        "CreateJobObjectW": ([ctypes.c_void_p, wt.LPCWSTR], wt.HANDLE),
        "AssignProcessToJobObject": ([wt.HANDLE, wt.HANDLE], wt.BOOL),
        "TerminateJobObject": ([wt.HANDLE, wt.UINT], wt.BOOL),
        "SetInformationJobObject": ([wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD], wt.BOOL),
        "QueryInformationJobObject": ([wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p], wt.BOOL),
        "CloseHandle": ([wt.HANDLE], wt.BOOL),
        "ResumeThread": ([wt.HANDLE], wt.DWORD),
    }
    for name, (args, result) in specs.items():
        fn = getattr(kernel, name)
        fn.argtypes = args
        fn.restype = result
    return kernel


def _limit_structs(deps):
    ctypes = deps["ctypes"]
    wt = deps["wintypes"]

    class Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wt.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wt.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wt.DWORD),
            ("SchedulingClass", wt.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", Basic),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    return Basic, Extended


def job_limit_structs():
    if not _windows():
        raise NotImplementedError("NOT_IMPLEMENTED")
    return _limit_structs(_imports())


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _int(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, int) or not (lo <= value <= hi):
        raise ValueError(label)
    return value


def _abs_text(value, label):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(label)
    path = Path(value)
    if (not path.is_absolute()) or (".." in path.parts):
        raise ValueError(label)
    return path


def _child_env():
    env = {}
    for key in _ENV_KEYS:
        value = os.environ.get(key)
        if isinstance(value, str) and value and "\x00" not in value:
            env[key] = value
    return env


def _validate(manifest, output_root):
    if not isinstance(manifest, dict):
        raise TypeError("manifest")
    allowed = {"version", "run_id", "workers", "deadline_seconds", "startup_seconds", "log_limit_bytes", "containment_policy"}
    if set(manifest) - allowed:
        raise ValueError("unknown_field")
    if _int(manifest.get("version"), 1, 1, "version") != 1:
        raise ValueError("version")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.isidentifier() or "\x00" in run_id:
        raise ValueError("run_id")
    workers = manifest.get("workers")
    if not isinstance(workers, list) or not (1 <= len(workers) <= 4):
        raise ValueError("workers")
    deadline = _int(manifest.get("deadline_seconds"), 1, 60, "deadline")
    startup = _int(manifest.get("startup_seconds"), 1, 10, "startup")
    log_limit = _int(manifest.get("log_limit_bytes"), 1024, 131072, "log_limit")
    policy = manifest.get("containment_policy", "explicit_terminate")
    if policy not in ("explicit_terminate", "kill_on_close"):
        raise ValueError("policy")
    seen = set()
    clean = []
    wfields = {"worker_id", "argv", "executable_sha256", "cwd"}
    for worker in workers:
        if not isinstance(worker, dict) or set(worker) - wfields:
            raise ValueError("worker")
        worker_id = worker.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id.isidentifier() or worker_id in seen:
            raise ValueError("worker_id")
        seen.add(worker_id)
        argv = worker.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or "\x00" in a for a in argv):
            raise ValueError("argv")
        exe = _abs_text(argv[0], "exe")
        if not exe.is_file():
            raise ValueError("exe")
        sha = worker.get("executable_sha256")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
            raise ValueError("sha")
        if _sha256_file(exe) != sha.lower():
            raise ValueError("sha_mismatch")
        cwd = _abs_text(worker.get("cwd"), "cwd")
        if not cwd.is_dir():
            raise ValueError("cwd")
        clean.append({"worker_id": worker_id, "argv": list(argv), "cwd": str(cwd)})
    output = _abs_text(os.fspath(output_root), "output_root")
    if output.exists():
        raise ValueError("output_exists")
    return {"run_id": run_id, "workers": clean, "deadline": deadline, "startup": startup, "log_limit": log_limit, "policy": policy, "output": output, "env": _child_env(), "seq": 1}


def _write_all(handle, data):
    view = memoryview(data)
    while len(view):
        wrote = handle.write(view)
        if not wrote:
            raise OSError("short write")
        view = view[wrote:]


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".part_", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            _write_all(handle, data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _journal(spec, event):
    payload = dict(event)
    payload["seq"] = spec["seq"]
    spec["seq"] += 1
    line = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
    path = spec["output"] / f"{spec['run_id']}.journal"
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
    with os.fdopen(fd, "ab") as handle:
        _write_all(handle, line)
        handle.flush()
        os.fsync(handle.fileno())


def _read_pipe(handle, limit, slot, read_file, close_handle, overflow_event):
    stored = bytearray()
    overflow = False
    bad = False
    try:
        while True:
            try:
                record = read_file(handle, 4096)
            except OSError:
                bad = True
                break
            if not isinstance(record, tuple) or len(record) != 2:
                bad = True
                break
            data, err = record
            if not isinstance(data, (bytes, bytearray)) or isinstance(err, bool) or not isinstance(err, int):
                bad = True
                break
            if len(stored) + len(data) > limit:
                room = limit - len(stored)
                if room:
                    stored += data[:room]
                overflow = True
                overflow_event.set()
                break
            if data:
                stored += data
            if err != 0 or not data:
                break
    finally:
        slot["data"] = bytes(stored)
        slot["overflow"] = overflow
        slot["bytes"] = len(stored)
        slot["bad_read"] = bad
        try:
            close_handle(handle)
        except OSError:
            pass
        slot["closed"] = True


def _close_quiet(close_handle, handles):
    while handles:
        handle = handles.pop()
        try:
            close_handle(handle)
        except OSError:
            pass


def _accounting(deps, kernel, job):
    ctypes = deps["ctypes"]
    wt = deps["wintypes"]

    class Accounting(ctypes.Structure):
        _fields_ = [
            ("times", ctypes.c_longlong * 4),
            ("page_faults", wt.DWORD),
            ("total", wt.DWORD),
            ("active", wt.DWORD),
            ("terminated", wt.DWORD),
        ]

    data = Accounting()
    if not kernel.QueryInformationJobObject(job, _JOB_ACCOUNTING, ctypes.byref(data), ctypes.sizeof(data), None):
        return None
    return int(data.active), int(data.total)


def _open_job(deps, kernel, run_id):
    ctypes = deps["ctypes"]
    name = f"Local\\CS_{run_id}_{os.getpid()}_{time.monotonic_ns()}"
    ctypes.set_last_error(0)
    handle = kernel.CreateJobObjectW(None, name)
    err = ctypes.get_last_error()
    if not handle:
        raise WindowsJobError("CREATE_JOB_FAILED", err)
    if err == 183:
        kernel.CloseHandle(handle)
        raise WindowsJobError("JOB_COLLISION", 183)
    return handle


def _enable_kill_on_close(deps, kernel, job):
    ctypes = deps["ctypes"]
    _basic, extended = _limit_structs(deps)
    info = extended()
    info.BasicLimitInformation.LimitFlags = _JOB_LIMIT_KILL_ON_CLOSE
    if not kernel.SetInformationJobObject(job, _JOB_EXTENDED_LIMIT, ctypes.byref(info), ctypes.sizeof(info)):
        raise WindowsJobError("SET_LIMIT_FAILED", ctypes.get_last_error())
    got = extended()
    returned = deps["wintypes"].DWORD()
    if not kernel.QueryInformationJobObject(job, _JOB_EXTENDED_LIMIT, ctypes.byref(got), ctypes.sizeof(got), ctypes.byref(returned)):
        raise WindowsJobError("QUERY_LIMIT_FAILED", ctypes.get_last_error())
    if (int(got.BasicLimitInformation.LimitFlags) & _JOB_LIMIT_KILL_ON_CLOSE) != _JOB_LIMIT_KILL_ON_CLOSE:
        raise WindowsJobError("KILL_ON_CLOSE_NOT_SET")


def _spawn(deps, kernel, job, spec, worker, owned, threads, slots, overflow_event):
    wapi = deps["_winapi"]
    subprocess = deps["subprocess"]
    current = wapi.GetCurrentProcess()
    nul = open(os.devnull, "rb")
    close_after = []
    reads = []
    ph = th = None
    try:
        stdin_h = wapi.DuplicateHandle(current, deps["msvcrt"].get_osfhandle(nul.fileno()), current, 0, True, 2)
        close_after.append(stdin_h)
        out_r, out_w = wapi.CreatePipe(None, 0)
        err_r, err_w = wapi.CreatePipe(None, 0)
        reads.extend((out_r, err_r))
        close_after.extend((out_w, err_w))
        out_dup = wapi.DuplicateHandle(current, out_w, current, 0, True, 2)
        err_dup = wapi.DuplicateHandle(current, err_w, current, 0, True, 2)
        close_after.extend((out_dup, err_dup))
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESTDHANDLES
        startup.hStdInput, startup.hStdOutput, startup.hStdError = stdin_h, out_dup, err_dup
        startup.lpAttributeList = {"handle_list": [stdin_h, out_dup, err_dup]}
        ph, th, pid, _tid = wapi.CreateProcess(
            worker["argv"][0], subprocess.list2cmdline(worker["argv"]), None, None, True,
            _CREATE_SUSPENDED | _CREATE_NO_WINDOW, spec["env"], worker["cwd"], startup,
        )
        rec = {"worker_id": worker["worker_id"], "ph": ph, "th": th, "pid": pid, "assigned": False, "resumed": False, "exit_code": None, "wait": None}
        owned.append(rec)
        ph = th = None
        _close_quiet(wapi.CloseHandle, close_after)
        if not kernel.AssignProcessToJobObject(job, rec["ph"]):
            raise WindowsJobError("ASSIGN_FAILED", deps["ctypes"].get_last_error())
        rec["assigned"] = True
        if kernel.ResumeThread(rec["th"]) == 0xFFFFFFFF:
            raise WindowsJobError("RESUME_FAILED", deps["ctypes"].get_last_error())
        rec["resumed"] = True
        for stream, read_h in (("stdout", reads[0]), ("stderr", reads[1])):
            slot = {"data": b"", "overflow": False, "bytes": 0, "closed": False, "stream": stream, "worker_id": worker["worker_id"]}
            slots.append(slot)
            thread = threading.Thread(target=_read_pipe, args=(read_h, spec["log_limit"], slot, wapi.ReadFile, wapi.CloseHandle, overflow_event), daemon=True)
            thread.start()
            threads.append(thread)
        reads.clear()
    finally:
        _close_quiet(wapi.CloseHandle, close_after)
        _close_quiet(wapi.CloseHandle, reads)
        if th is not None:
            wapi.CloseHandle(th)
        if ph is not None:
            try:
                wapi.TerminateProcess(ph, 1)
            except OSError:
                pass
            wapi.WaitForSingleObject(ph, 5000)
            wapi.CloseHandle(ph)
        nul.close()


def _join(threads, timeout):
    for thread in threads:
        if thread.is_alive():
            thread.join(timeout)


def _wait_run(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event, dead_by):
    wapi = deps["_winapi"]
    while True:
        if cancel_event.is_set():
            return "CANCELLED", "cancelled"
        if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
            return "FAILED", "LOG_LIMIT"
        if _monotonic() >= dead_by:
            return "TIMEOUT", "deadline"
        running = False
        for rec in owned:
            try:
                waited = wapi.WaitForSingleObject(rec["ph"], 0)
            except Exception:
                return "UNKNOWN", "wait_failed"
            rec["wait"] = waited
            if waited == _WAIT_TIMEOUT:
                running = True
            elif waited != _WAIT_OBJECT_0:
                return "UNKNOWN", "wait_failed"
        if running:
            _sleep(0.02)
            continue
        try:
            counts = _accounting(deps, kernel, job)
        except Exception:
            return "UNKNOWN", "query_failed"
        if counts is None:
            return "UNKNOWN", "query_failed"
        spec["active"] = counts[0]
        if counts[0] > 0:
            _sleep(0.02)
            continue
        _join(threads, 2)
        if any(thread.is_alive() for thread in threads):
            return "UNKNOWN", "reader_join"
        if cancel_event.is_set():
            return "CANCELLED", "cancelled"
        if _monotonic() >= dead_by:
            return "TIMEOUT", "deadline"
        if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
            return "FAILED", "LOG_LIMIT"
        if any(slot.get("bad_read") for slot in slots):
            return "UNKNOWN", "bad_read"
        failed = False
        for rec in owned:
            if rec["wait"] != _WAIT_OBJECT_0:
                return "UNKNOWN", "wait_failed"
            try:
                rec["exit_code"] = wapi.GetExitCodeProcess(rec["ph"])
            except Exception:
                return "UNKNOWN", "exit_query_failed"
            if rec["exit_code"] != 0:
                failed = True
        if failed:
            return "FAILED", "nonzero_exit"
        return "PROCESS_COMPLETED", ""


def _launch_and_wait(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event):
    origin = _monotonic()
    start_by = origin + spec["startup"]
    dead_by = origin + spec["deadline"]
    for worker in spec["workers"]:
        now = _monotonic()
        if cancel_event.is_set():
            return "CANCELLED", "cancelled"
        if now >= start_by:
            return "TIMEOUT", "startup_budget"
        if now >= dead_by:
            return "TIMEOUT", "deadline"
        _spawn(deps, kernel, job, spec, worker, owned, threads, slots, overflow_event)
        _journal(spec, {"event": "resumed", "worker_id": worker["worker_id"], "pid": owned[-1]["pid"]})
    return _wait_run(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event, dead_by)


def _shutdown(deps, kernel, job, owned, terminate):
    wapi = deps["_winapi"]
    if terminate:
        for rec in owned:
            if rec["ph"] is not None:
                try:
                    wapi.TerminateProcess(rec["ph"], 1)
                except Exception:
                    pass
        try:
            kernel.TerminateJobObject(job, 1)
        except Exception:
            pass
    end = _monotonic() + 8
    waits_ok = True
    for rec in owned:
        if rec["ph"] is None:
            waits_ok = False
            continue
        left = int(max(0.0, end - _monotonic()) * 1000)
        try:
            waited = wapi.WaitForSingleObject(rec["ph"], left)
        except Exception:
            waits_ok = False
            rec["wait"] = None
            continue
        rec["wait"] = waited
        if waited != _WAIT_OBJECT_0:
            waits_ok = False
            continue
        try:
            rec["exit_code"] = wapi.GetExitCodeProcess(rec["ph"])
        except Exception:
            waits_ok = False
    counts = None
    try:
        counts = _accounting(deps, kernel, job)
    except Exception:
        pass
    if counts is None or not waits_ok:
        return (None if counts is None else counts[0]), "UNKNOWN_DRAIN"
    active = counts[0]
    if active != 0:
        return active, "UNKNOWN_DRAIN"
    return active, "CLEANUP"


def _close_owned(wapi, owned):
    for rec in owned:
        if rec.get("th") is not None:
            try:
                wapi.CloseHandle(rec["th"])
            except OSError:
                pass
            rec["th"] = None
        if rec.get("ph") is not None:
            try:
                wapi.CloseHandle(rec["ph"])
            except OSError:
                pass
            rec["ph"] = None


def _emit(spec, status, reason, owned, slots, active, drain):
    logs = {}
    for slot in slots:
        raw = bytes(slot.get("data", b""))[: spec["log_limit"]]
        path = spec["output"] / f"{slot['worker_id']}.{slot['stream']}.log"
        _atomic_write(path, raw)
        entry = logs.setdefault(slot["worker_id"], {})
        entry[slot["stream"]] = raw.decode("utf-8", "replace")
        entry[slot["stream"] + "_bytes"] = len(raw)
        entry[slot["stream"] + "_overflow"] = bool(slot.get("overflow"))
        entry[slot["stream"] + "_path"] = path.name
    payload = {
        "version": 1,
        "run_id": spec["run_id"],
        "status": status,
        "failure_reason": reason,
        "containment_policy": spec["policy"],
        "workers": [{"worker_id": r["worker_id"], "pid": r["pid"], "exit_code": r["exit_code"], "assigned": r["assigned"], "resumed": r["resumed"]} for r in owned],
        "job_active_count": active,
        "drain_proof": drain,
        "whole_tree_certificate": False,
        "logs": logs,
        "reattach": False,
        "replay": False,
    }
    encoded = json.dumps(payload).encode()
    if len(encoded) > _RECEIPT_MAX:
        for entry in logs.values():
            entry["stdout"] = ""
            entry["stderr"] = ""
        payload["logs_externalized"] = True
        encoded = json.dumps(payload).encode()
    if len(encoded) > _RECEIPT_MAX:
        raise WindowsJobError("RECEIPT_TOO_LARGE")
    _atomic_write(spec["output"] / f"{spec['run_id']}_receipt.json", encoded)
    _journal(spec, {"event": "terminal", "status": status, "failure_reason": reason})
    return payload


def run_workers(manifest, output_root, *, cancel_event=None):
    if not _windows():
        raise NotImplementedError("NOT_IMPLEMENTED")
    if cancel_event is None:
        cancel_event = threading.Event()
    spec = _validate(manifest, output_root)
    deps = _imports()
    kernel = _kernel(deps)
    job = _open_job(deps, kernel, spec["run_id"])
    owned, threads, slots = [], [], []
    overflow_event = threading.Event()
    status, reason, active, drain = "UNKNOWN", "init", None, "UNKNOWN"
    result = None
    try:
        spec["output"].mkdir()
        _journal(spec, {"event": "start", "policy": spec["policy"]})
        if spec["policy"] == "kill_on_close":
            _enable_kill_on_close(deps, kernel, job)
        status, reason = _launch_and_wait(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event)
        active = spec.get("active")
    except WindowsJobError as exc:
        if status not in ("CANCELLED", "TIMEOUT"):
            status, reason = "FAILED", exc.code
    except Exception:
        if status not in ("CANCELLED", "TIMEOUT", "FAILED"):
            status, reason = "FAILED", "EXCEPTION"
    finally:
        try:
            try:
                active2, drain = _shutdown(deps, kernel, job, owned, status != "PROCESS_COMPLETED")
                if active2 is not None:
                    active = active2
            except Exception:
                drain = "UNKNOWN_DRAIN"
            try:
                _join(threads, 2)
            except Exception:
                pass
            if any(t.is_alive() for t in threads) or drain not in ("CLEANUP", "UNKNOWN_DRAIN"):
                drain = "UNKNOWN_DRAIN"
            if drain != "CLEANUP" and status == "PROCESS_COMPLETED":
                status, reason = "UNKNOWN", "proof_incomplete"
            if any(slot.get("bad_read") for slot in slots) and status == "PROCESS_COMPLETED":
                status, reason = "UNKNOWN", "bad_read"
            try:
                _close_owned(deps["_winapi"], owned)
            except Exception:
                pass
            try:
                if spec["output"].is_dir():
                    result = _emit(spec, status, reason, owned, slots, active, drain)
                else:
                    result = {"version": 1, "run_id": spec["run_id"], "status": status, "failure_reason": reason, "drain_proof": "UNKNOWN_DRAIN", "whole_tree_certificate": False, "reattach": False, "replay": False}
            except Exception:
                result = {"version": 1, "run_id": spec["run_id"], "status": status, "failure_reason": reason, "drain_proof": drain, "whole_tree_certificate": False, "reattach": False, "replay": False}
        finally:
            try:
                kernel.CloseHandle(job)
            except Exception:
                pass
    if result is None:
        result = {"version": 1, "run_id": spec["run_id"], "status": status, "failure_reason": reason, "drain_proof": drain, "whole_tree_certificate": False, "reattach": False, "replay": False}
    return result


def restart_receipt(output_root, run_id):
    if not _windows():
        raise NotImplementedError("NOT_IMPLEMENTED")
    if not isinstance(run_id, str) or not run_id.isidentifier():
        raise ValueError("run_id")
    output = _abs_text(os.fspath(output_root), "output_root")
    receipt = output / f"{run_id}_receipt.json"
    journal = output / f"{run_id}.journal"
    if receipt.is_file():
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("run_id") != run_id:
            return {"version": 1, "run_id": run_id, "status": "UNKNOWN_INTERRUPTED", "failure_reason": "RECEIPT_MISMATCH", "drain_proof": "UNKNOWN", "whole_tree_certificate": False, "reattach": False, "replay": False}
        data["reattach"] = False
        data["replay"] = False
        return data
    if journal.is_file():
        return {"version": 1, "run_id": run_id, "status": "UNKNOWN_INTERRUPTED", "failure_reason": "IN_FLIGHT_NO_WRAPPER", "drain_proof": "UNKNOWN", "whole_tree_certificate": False, "reattach": False, "replay": False}
    raise FileNotFoundError(run_id)
