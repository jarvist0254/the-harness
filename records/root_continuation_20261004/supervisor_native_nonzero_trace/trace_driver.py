"""Single admitted nonzero-exit native diagnostic with retained controller handle."""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from ctypes import Structure, WinDLL, byref, c_uint32, c_void_p, sizeof
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
SOURCE = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor.py")
WORKER = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_native_fixture\worker.py")
CONTROLLER = HERE / "trace_controller.py"
CONTRACT = HERE / "trace_contract.json"
ADMISSION = HERE / "trace_admission.json"
OUTER_LIMIT = 30.0
CREATE_NO_WINDOW = 0x08000000


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def process_ids():
    class PROCESSENTRY32W(Structure):
        _fields_ = [
            ("dwSize", c_uint32), ("cntUsage", c_uint32), ("th32ProcessID", c_uint32),
            ("th32DefaultHeapID", c_void_p), ("th32ModuleID", c_uint32),
            ("cntThreads", c_uint32), ("th32ParentProcessID", c_uint32),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", c_uint32),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    k32 = WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.argtypes = [c_uint32, c_uint32]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32FirstW.restype = wintypes.BOOL
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    snapshot = k32.CreateToolhelp32Snapshot(2, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot")
    ids = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = sizeof(entry)
        ok = k32.Process32FirstW(snapshot, byref(entry))
        while ok:
            ids.add(int(entry.th32ProcessID))
            ok = k32.Process32NextW(snapshot, byref(entry))
        err = ctypes.get_last_error()
        if err not in (0, 18):
            raise OSError(err, "Process32NextW")
    finally:
        if not k32.CloseHandle(snapshot):
            raise OSError(ctypes.get_last_error(), "CloseHandle(snapshot)")
    return ids


def main():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    if os.name != "nt" or sys.version_info[:2] != (3, 10) or Path(sys.executable).resolve() != PYTHON.resolve():
        print(json.dumps({"status": "NOT_CHECKED", "reason": "runtime_mismatch"}))
        return 2
    paths = {
        "source": SOURCE,
        "worker": WORKER,
        "trace_controller.py": CONTROLLER,
        "trace_driver.py": Path(__file__),
        "trace_contract.json": CONTRACT,
        "python": PYTHON,
    }
    expected = admission["sha256"]
    actual = {name: sha256(path) for name, path in paths.items()}
    if actual != expected or any(len(value) != 64 for value in expected.values()):
        print(json.dumps({"status": "NOT_CHECKED", "reason": "input_hash_gate_failed", "actual": actual, "expected": expected}))
        return 2
    run_id = datetime.now(timezone.utc).strftime("nonzero_trace_%Y%m%dT%H%M%SZ")
    run_root = HERE / "native_runs" / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    output = run_root / "supervisor_output"
    trace = run_root / "native_api_trace.jsonl"
    command = [str(PYTHON), str(CONTROLLER), "--output", str(output), "--trace", str(trace)]
    before = {name: sha256(path) for name, path in paths.items()}
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(HERE), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, creationflags=CREATE_NO_WINDOW, close_fds=True)
    controller_pid = proc.pid
    timeout = False
    try:
        stdout, stderr = proc.communicate(timeout=OUTER_LIMIT)
    except subprocess.TimeoutExpired:
        timeout = True
        proc.kill()
        stdout, stderr = proc.communicate(timeout=8.0)
    elapsed = time.monotonic() - start
    (run_root / "controller_stdout.log").write_bytes(stdout)
    (run_root / "controller_stderr.log").write_bytes(stderr)
    after = {name: sha256(path) for name, path in paths.items()}
    controller_absent = controller_pid not in process_ids()
    payload = json.loads(stdout.decode("utf-8").strip().splitlines()[-1]) if stdout else {}
    result = payload.get("result", {})
    worker_pids = [int(w["pid"]) for w in result.get("workers", [])]
    current = process_ids()
    receipt = {
        "status": "TRACE_CAPTURED" if not timeout and proc.returncode == 0 and payload.get("trace", {}).get("complete") else "FAILED_OR_INCOMPLETE",
        "run_id": run_id,
        "command": command,
        "cwd": str(HERE),
        "python_abi_bits": ctypes.sizeof(ctypes.c_void_p) * 8,
        "python_machine": os.environ.get("PROCESSOR_ARCHITECTURE"),
        "controller_pid": controller_pid,
        "controller_exit_code": proc.returncode,
        "controller_timeout": timeout,
        "controller_elapsed_seconds": round(elapsed, 6),
        "controller_pid_absent_after_wait": controller_absent,
        "worker_pids": worker_pids,
        "worker_pids_absent_after_cleanup": not any(pid in current for pid in worker_pids),
        "hashes_before": before,
        "hashes_after": after,
        "hashes_unchanged": before == after and payload.get("hashes_unchanged") is True,
        "controller_payload": payload,
        "native_trace_sha256": sha256(trace) if trace.is_file() else None,
        "native_trace_bytes": trace.stat().st_size if trace.is_file() else None,
        "native_trace_lines": sum(1 for _ in trace.open("rb")) if trace.is_file() else 0,
        "raw_worker_receipt": (output / "native_nonzero_trace_receipt.json").read_text(encoding="utf-8") if (output / "native_nonzero_trace_receipt.json").is_file() else None,
        "limitations": ["one diagnostic case only", "point-in-time process snapshots", "no whole-tree certificate", "resource high-water unmeasured"],
    }
    encoded = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8")
    with (run_root / "trace_receipt.json").open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"run_root": str(run_root), "status": receipt["status"], "supervisor_status": result.get("status"), "drain_proof": result.get("drain_proof"), "trace_lines": receipt["native_trace_lines"]}))
    return 0 if receipt["status"] == "TRACE_CAPTURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
