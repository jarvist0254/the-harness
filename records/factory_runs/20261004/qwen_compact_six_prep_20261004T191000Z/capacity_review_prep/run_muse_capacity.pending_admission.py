"""Pinned, bounded Muse audit launcher. Prepared for review; do not run without root admission."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

ROOT = Path(r"E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\capacity_review_prep")
MUSE = Path(r"C:\Users\thoma\AppData\Local\Programs\muse\muse-bin-1.4.2-R4684.1.exe")
PROMPT = ROOT / "muse_capacity.prompt.txt"
SCHEMA = ROOT / "output_schema.json"
OUTPUT = ROOT / "run_output"
MAX_SECONDS = 300.0
MAX_CAPTURE = 2 * 1024 * 1024
PINS = {
    r"E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\capacity_review_prep\spec.snapshot.txt": "8AB81AA30E7CCD104B2E8AE6FBB9D19C87B31FFFB7FCB32880DC97F0C02D1BB8",
    r"E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\capacity_review_prep\tests.snapshot.txt": "AAE6BE310522F4D7A3152652FFD2816DF186DB72A317F5EAD1372EC9DDA95239",
    r"E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\capacity_review_prep\source.snapshot.txt": "7005C1FC83A4A9901E30CF8E705DBE5961DC1010C645E963BB08EC75A7808267",
}
MUSE_SHA256 = "39A97806D315ECE0FC5CDBB88C903EF5BC77655F32E66DC22D267A212C5030BA"
PROMPT_SHA256 = "7B386F3D129562A67A7CCD13000F4E519D2A98B231177C3880161F0065C15090"
SCHEMA_SHA256 = "049318FD4338375A9798BFA32ECE33AE60C28DA2AC8E05B78BD30419EE9E659F"

RESULT_KEYS = {"verdict", "findings", "safety_checks"}
SECRET_KEY = re.compile(r"(authorization|api.?key|access.?token|refresh.?token|password|secret|credential)", re.I)
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
URL_QUERY = re.compile(r"(https?://[^\s\"']+\?)[^\s\"']+")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _find_result(value, found):
    if isinstance(value, dict):
        if set(value) == RESULT_KEYS:
            found.append(value)
        for child in value.values():
            _find_result(child, found)
    elif isinstance(value, list):
        for child in value:
            _find_result(child, found)


def validate_result(value):
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        return False
    if value["verdict"] not in {"SUPPORT_WITH_LIMITS", "REQUEST_CHANGES", "NEEDS_DISCUSSION"}:
        return False
    findings = value["findings"]
    checks = value["safety_checks"]
    if not isinstance(findings, list) or len(findings) > 16:
        return False
    if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
        return False
    required = {"region", "exact_source", "reason", "minimal_fix"}
    for item in findings:
        if not isinstance(item, dict) or set(item) != required:
            return False
        if any(not isinstance(item[k], str) or not item[k] or len(item[k]) > 2048 for k in required):
            return False
    return all(isinstance(x, str) and 0 < len(x) <= 8192 for x in checks)


def parse_jsonl(data: bytes):
    if len(data) > MAX_CAPTURE:
        return {"status": "OUTPUT_LIMIT", "event_count": 0, "result": None, "usage": "UNKNOWN"}
    if not data or not data.endswith(b"\n"):
        return {"status": "TRUNCATED_JSONL", "event_count": 0, "result": None, "usage": "UNKNOWN"}
    events = []
    try:
        for line in data.splitlines():
            if not line.strip():
                continue
            events.append(json.loads(line.decode("utf-8"), object_pairs_hook=strict_object))
    except Exception:
        return {"status": "INVALID_JSONL", "event_count": len(events), "result": None, "usage": "UNKNOWN"}
    if any(not isinstance(event, dict) for event in events):
        return {"status": "INVALID_EVENT", "event_count": len(events), "result": None, "usage": "UNKNOWN"}
    candidates = []
    for event in events:
        _find_result(event, candidates)
    if len(candidates) > 1:
        return {"status": "AMBIGUOUS_RESULT", "event_count": len(events), "result": None, "usage": "UNKNOWN"}
    if not candidates or not validate_result(candidates[0]):
        return {"status": "UNKNOWN_RESULT_SHAPE", "event_count": len(events), "result": None, "usage": "UNKNOWN"}
    return {"status": "STRUCTURED_RESULT_PARSED", "event_count": len(events), "result": candidates[0], "usage": "UNKNOWN"}


def redact_value(value, key=""):
    if SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact_value(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v, key) for v in value]
    if isinstance(value, str):
        return URL_QUERY.sub(r"\1[REDACTED]", BEARER.sub("Bearer [REDACTED]", value))
    return value


def redact_jsonl(data: bytes) -> bytes:
    output = []
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line.decode("utf-8"), object_pairs_hook=strict_object)
            output.append(json.dumps(redact_value(event), ensure_ascii=False, separators=(",", ":")))
        except Exception:
            output.append('"[REDACTED_INVALID_EVENT]"')
    return (("\n".join(output) + "\n") if output else "").encode("utf-8")


# Win32 declarations are created only by main(); importing this module is pure.
def _win32():
    if os.name != "nt":
        raise RuntimeError("WINDOWS_REQUIRED")
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    HANDLE = wintypes.HANDLE
    DWORD = wintypes.DWORD
    SIZE_T = ctypes.c_size_t
    class SA(ctypes.Structure):
        _fields_ = [("nLength", DWORD), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", wintypes.BOOL)]
    class SI(ctypes.Structure):
        _fields_ = [("cb", DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", DWORD), ("dwY", DWORD), ("dwXSize", DWORD), ("dwYSize", DWORD), ("dwXCountChars", DWORD),
                    ("dwYCountChars", DWORD), ("dwFillAttribute", DWORD), ("dwFlags", DWORD), ("wShowWindow", wintypes.WORD),
                    ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.POINTER(ctypes.c_byte)), ("hStdInput", HANDLE),
                    ("hStdOutput", HANDLE), ("hStdError", HANDLE)]
    class PI(ctypes.Structure):
        _fields_ = [("hProcess", HANDLE), ("hThread", HANDLE), ("dwProcessId", DWORD), ("dwThreadId", DWORD)]
    class BLI(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", DWORD),
                    ("MinimumWorkingSetSize", SIZE_T), ("MaximumWorkingSetSize", SIZE_T), ("ActiveProcessLimit", DWORD),
                    ("Affinity", SIZE_T), ("PriorityClass", DWORD), ("SchedulingClass", DWORD)]
    class IOC(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class JELI(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BLI), ("IoInfo", IOC), ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T), ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]
    class JBAI(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong), ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                    ("ThisPeriodTotalKernelTime", ctypes.c_longlong), ("TotalPageFaultCount", DWORD), ("TotalProcesses", DWORD),
                    ("ActiveProcesses", DWORD), ("TotalTerminatedProcesses", DWORD)]
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]; k.CreateJobObjectW.restype = HANDLE
    k.SetInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD]; k.SetInformationJobObject.restype = wintypes.BOOL
    k.AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]; k.AssignProcessToJobObject.restype = wintypes.BOOL
    k.TerminateJobObject.argtypes = [HANDLE, wintypes.UINT]; k.TerminateJobObject.restype = wintypes.BOOL
    k.QueryInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD)]; k.QueryInformationJobObject.restype = wintypes.BOOL
    k.CreatePipe.argtypes = [ctypes.POINTER(HANDLE), ctypes.POINTER(HANDLE), ctypes.POINTER(SA), DWORD]; k.CreatePipe.restype = wintypes.BOOL
    k.SetHandleInformation.argtypes = [HANDLE, DWORD, DWORD]; k.SetHandleInformation.restype = wintypes.BOOL
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, DWORD, DWORD, ctypes.POINTER(SA), DWORD, DWORD, HANDLE]; k.CreateFileW.restype = HANDLE
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, DWORD,
                                 ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(SI), ctypes.POINTER(PI)]; k.CreateProcessW.restype = wintypes.BOOL
    k.ResumeThread.argtypes = [HANDLE]; k.ResumeThread.restype = DWORD
    k.WaitForSingleObject.argtypes = [HANDLE, DWORD]; k.WaitForSingleObject.restype = DWORD
    k.GetExitCodeProcess.argtypes = [HANDLE, ctypes.POINTER(DWORD)]; k.GetExitCodeProcess.restype = wintypes.BOOL
    k.TerminateProcess.argtypes = [HANDLE, wintypes.UINT]; k.TerminateProcess.restype = wintypes.BOOL
    k.ReadFile.argtypes = [HANDLE, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD), ctypes.c_void_p]; k.ReadFile.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [HANDLE]; k.CloseHandle.restype = wintypes.BOOL
    return k, SA, SI, PI, JELI, JBAI


def _check(ok, label):
    if not ok:
        raise OSError(ctypes.get_last_error(), label)


def _read_pipe(k, handle, state, lock, overflow):
    buffer = ctypes.create_string_buffer(8192)
    while True:
        count = wintypes.DWORD()
        ok = k.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None)
        if not ok:
            code = ctypes.get_last_error()
            if code == 109:  # ERROR_BROKEN_PIPE is ordinary EOF after all writers close.
                break
            state["error"] = code
            break
        if count.value == 0:
            break
        chunk = buffer.raw[:count.value]
        with lock:
            left = max(0, MAX_CAPTURE - state["global_total"][0])
            keep = min(left, len(chunk))
            state["parts"].append(chunk[:keep])
            state["captured"][0] += keep; state["global_total"][0] += keep
            if keep != len(chunk):
                overflow.set()
    state["done"].set()


def _job_active(k, job, JBAI):
    info = JBAI()
    returned = wintypes.DWORD()
    _check(k.QueryInformationJobObject(job, 1, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)), "QueryInformationJobObject")
    return int(info.ActiveProcesses)


def _capture(handles, k):
    global_total = [0]
    state = {name: {"parts": [], "captured": [0], "global_total": global_total, "done": threading.Event(), "error": None} for name in ("stdout", "stderr")}
    lock = threading.Lock()
    overflow = threading.Event()
    threads = []
    for name, handle in zip(("stdout", "stderr"), handles):
        t = threading.Thread(target=_read_pipe, args=(k, handle, state[name], lock, overflow), daemon=True)
        t.start(); threads.append(t)
    return state, overflow, threads


def run():
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("PYTHON310_REQUIRED")
    if OUTPUT.exists():
        raise RuntimeError("OUTPUT_ALREADY_EXISTS_NO_RETRY")
    python_executable = Path(sys.executable).resolve()
    expected = {str(MUSE): MUSE_SHA256, str(PROMPT): PROMPT_SHA256, str(SCHEMA): SCHEMA_SHA256, str(python_executable): sha256_file(python_executable), **PINS}
    before = {path: sha256_file(Path(path)) for path in expected}
    if any(before[path] != digest for path, digest in expected.items()):
        raise RuntimeError("PIN_MISMATCH")
    if len(PROMPT.read_bytes()) > 128 * 1024 or SCHEMA.stat().st_size > 32 * 1024:
        raise RuntimeError("INPUT_SIZE_LIMIT")
    json.loads(SCHEMA.read_text(encoding="utf-8-sig"))
    job_root = ROOT.resolve()
    args = [str(MUSE), "exec", "--provider", "meta", "--json", "--prompt-file", str(PROMPT), "--output-schema", str(SCHEMA),
            "--reasoning-effort", "high", "--max-model-steps", "4", "--max-tool-output-bytes", "8192", "--no-parallel-tool-calls",
            "--workspace", str(job_root), "--approval-mode", "untrusted", "--disable-shell", "--disable-write",
            "--disable-web-tools", "--no-foreign-personal-context", "--no-session-log", "--user-input-auto-resolve"]
    k, SA, SI, PI, JELI, JBAI = _win32()
    OUTPUT.mkdir()
    progress_path = OUTPUT / "progress.json"
    def progress(status, pid=None, extra=None):
        payload = {"status": status, "pid": pid, "elapsed_seconds": round(time.monotonic() - started, 3), "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if extra: payload.update(extra)
        tmp = progress_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, progress_path)
    started = time.monotonic()
    last_progress_time = started
    job = k.CreateJobObjectW(None, None)
    if not job: raise OSError(ctypes.get_last_error(), "CreateJobObjectW")
    proc = thread = None
    read_handles = []
    write_handles = []
    stdin_handle = None
    state = overflow = threads = None
    exit_code = None
    status = "UNKNOWN"
    failure = "setup"
    assigned = resumed = False
    cleanup_ok = False
    active_final = None
    try:
        limits = JELI(); limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        _check(k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)), "SetInformationJobObject")
        sa = SA(ctypes.sizeof(SA), None, True)
        for _ in range(2):
            r = wintypes.HANDLE(); w = wintypes.HANDLE()
            _check(k.CreatePipe(ctypes.byref(r), ctypes.byref(w), ctypes.byref(sa), 0), "CreatePipe")
            _check(k.SetHandleInformation(r, 1, 0), "SetHandleInformation")
            read_handles.append(r); write_handles.append(w)
        stdin_handle = k.CreateFileW("NUL", 0x80000000, 1 | 2, ctypes.byref(sa), 3, 0x80, None)
        if not stdin_handle or ctypes.cast(stdin_handle, ctypes.c_void_p).value == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(), "CreateFileW_NUL")
        si = SI(); si.cb = ctypes.sizeof(SI); si.dwFlags = 0x100
        si.hStdInput = stdin_handle; si.hStdOutput = write_handles[0]; si.hStdError = write_handles[1]
        pi = PI(); cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        _check(k.CreateProcessW(str(MUSE), cmdline, None, None, True, 0x4 | 0x08000000 | 0x400, None, str(job_root), ctypes.byref(si), ctypes.byref(pi)), "CreateProcessW")
        proc, thread = pi.hProcess, pi.hThread
        _check(k.AssignProcessToJobObject(job, proc), "AssignProcessToJobObject")
        assigned = True
        for handle in write_handles:
            _check(k.CloseHandle(handle), "ClosePipeWriter");
        write_handles = []
        _check(k.CloseHandle(stdin_handle), "CloseStdin"); stdin_handle = None
        resume_count = k.ResumeThread(thread)
        _check(resume_count == 1, "ResumeThread"); resumed = True
        state, overflow, threads = _capture(read_handles, k)
        progress("RUNNING", int(pi.dwProcessId), {"assigned": assigned, "resumed": resumed, "deadline_seconds": MAX_SECONDS, "output_cap_bytes": MAX_CAPTURE})
        deadline = started + MAX_SECONDS
        root_signaled = False
        while time.monotonic() < deadline:
            if overflow.is_set():
                status, failure = "OUTPUT_LIMIT", "stdout_stderr_cap"
                break
            if not root_signaled:
                waited = k.WaitForSingleObject(proc, 0)
                if waited == 0:
                    root_signaled = True
                    code = wintypes.DWORD(); _check(k.GetExitCodeProcess(proc, ctypes.byref(code)), "GetExitCodeProcess"); exit_code = int(code.value)
                    if exit_code != 0:
                        status, failure = "PROCESS_FAILED", "nonzero_exit"
                        break
                elif waited != 258:
                    status, failure = "UNKNOWN", "unexpected_root_wait"
                    break
            if root_signaled:
                active = _job_active(k, job, JBAI)
                active_final = active
                if active == 0 and all(state[n]["done"].is_set() for n in state):
                    status, failure = "PROCESS_COMPLETED", ""
                    break
            now = time.monotonic()
            if now - last_progress_time >= 15.0:
                progress("RUNNING", int(pi.dwProcessId), {"root_signaled": root_signaled, "active_job_processes": (_job_active(k, job, JBAI) if root_signaled else None), "stdout_bytes": state["stdout"]["captured"][0], "stderr_bytes": state["stderr"]["captured"][0]})
                last_progress_time = now
            time.sleep(0.1)
        else:
            status, failure = "TIMEOUT", "deadline"
        if status != "PROCESS_COMPLETED":
            term_ok = bool(k.TerminateJobObject(job, 1))
            wait_ok = (k.WaitForSingleObject(proc, 5000) == 0) if proc else False
            try: active_after = _job_active(k, job, JBAI)
            except Exception: active_after = None
            cleanup_ok = term_ok and wait_ok and active_after == 0
            if not cleanup_ok: status = "UNKNOWN_CLEANUP"
        else:
            cleanup_ok = True
    except Exception as exc:
        status, failure = "UNKNOWN", type(exc).__name__
        if proc and not assigned:
            try: k.TerminateProcess(proc, 1)
            except Exception: pass
        if job and assigned:
            try: cleanup_ok = bool(k.TerminateJobObject(job, 1)) and (k.WaitForSingleObject(proc, 5000) == 0 if proc else True)
            except Exception: cleanup_ok = False
    finally:
        for handle in write_handles + ([stdin_handle] if stdin_handle else []):
            try: k.CloseHandle(handle)
            except Exception: pass
        if job:
            try: k.CloseHandle(job)  # KILL_ON_JOB_CLOSE is the final owned-tree boundary.
            except Exception: cleanup_ok = False
        if threads:
            for t in threads: t.join(5.0)
        for handle in read_handles:
            try: k.CloseHandle(handle)
            except Exception: cleanup_ok = False
        for handle in (thread, proc):
            if handle:
                try: k.CloseHandle(handle)
                except Exception: cleanup_ok = False
    if state and any(state[n]["error"] is not None for n in state):
        status, failure = "UNKNOWN_PIPE_READ", "ReadFile_failed"
        cleanup_ok = False
    if threads and any(t.is_alive() for t in threads):
        status, failure = "UNKNOWN_CLEANUP", "reader_thread_unresolved"
        cleanup_ok = False
    if not cleanup_ok and status == "PROCESS_COMPLETED":
        status, failure = "UNKNOWN_CLEANUP", "owned_cleanup_unproven"
    stdout = b"".join(state["stdout"]["parts"]) if state else b""
    stderr = b"".join(state["stderr"]["parts"]) if state else b""
    (OUTPUT / "stdout.raw.jsonl").write_bytes(stdout)
    (OUTPUT / "stderr.raw.log").write_bytes(stderr)
    parsed = parse_jsonl(stdout) if status == "PROCESS_COMPLETED" else {"status": "UNKNOWN", "event_count": 0, "result": None, "usage": "UNKNOWN"}
    if parsed.get("result") is not None:
        (OUTPUT / "parsed_review.json").write_text(json.dumps(parsed["result"], ensure_ascii=False, indent=2), encoding="utf-8")
    after = {path: sha256_file(Path(path)) for path in expected}
    if after != before:
        status, failure = "INPUT_PIN_CHANGED", "post_run_pin_mismatch"
    receipt = {"status": status, "failure_reason": failure, "process_exit_code": exit_code, "assigned": assigned, "resumed": resumed,
               "cleanup_proof": "CLEANUP" if cleanup_ok else "UNKNOWN_DRAIN", "whole_tree_certificate": False, "active_job_processes_final": active_final, "pipe_eof": ({n: state[n]["done"].is_set() for n in state} if state else {"stdout": False, "stderr": False}),
               "elapsed_seconds": round(time.monotonic() - started, 3), "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
               "stdout_sha256": hashlib.sha256(stdout).hexdigest().upper(), "stderr_sha256": hashlib.sha256(stderr).hexdigest().upper(),
               "parsed": parsed, "usage": "UNKNOWN" if parsed.get("usage") == "UNKNOWN" else parsed.get("usage"),
               "tool_calls": "UNKNOWN", "subagents": "UNKNOWN", "source_pins_before": before, "source_pins_after": after,
               "muse_command": args, "muse_binary_sha256": MUSE_SHA256, "python_executable": str(python_executable), "python_version": sys.version}
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    progress(status, int(pi.dwProcessId) if pi else None, {"cleanup_proof": receipt["cleanup_proof"], "receipt": str(OUTPUT / "receipt.json")})
    if status != "PROCESS_COMPLETED" or not cleanup_ok or parsed.get("status") != "STRUCTURED_RESULT_PARSED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
