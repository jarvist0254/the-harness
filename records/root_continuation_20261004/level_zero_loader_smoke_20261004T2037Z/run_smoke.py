import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from ctypes import Structure, c_uint32, c_void_p, sizeof, wintypes
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE / "levelzero_probe_worker.py"
CONTROLLER = HERE / "probe_controller.py"
DRIVER = Path(__file__).resolve()
SUPERVISOR = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py")
PYTHON310 = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
LOADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\runtime_source\build\bin\ze_loader.dll")
HEADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h")
ADMISSION = HERE / "ROOT_ADMISSION.json"
EXPECTED = {
    "worker_sha256": "",
    "controller_sha256": "",
    "driver_sha256": "",
    "supervisor_sha256": "3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c",
    "python_sha256": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
    "loader_sha256": "0838c395a7393c313fdfeff8cea5d08a71ba044dc28f793aa4f7d28f60095162",
    "header_sha256": "c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de",
}
CREATE_NO_WINDOW = 0x08000000
MAX_CAPTURE = 128 * 1024
OUTER_TIMEOUT_S = 12.0


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, obj):
    tmp = path.with_name(path.name + ".part")
    data = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tmp.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def process_ids():
    class PROCESSENTRY32W(Structure):
        _fields_ = [
            ("dwSize", c_uint32), ("cntUsage", c_uint32), ("th32ProcessID", c_uint32),
            ("th32DefaultHeapID", c_void_p), ("th32ModuleID", c_uint32),
            ("cntThreads", c_uint32), ("th32ParentProcessID", c_uint32),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", c_uint32),
            ("szExeFile", wintypes.WCHAR * 260),
        ]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.argtypes = [c_uint32, c_uint32]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32FirstW.restype = wintypes.BOOL
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if not snap or snap == invalid:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot")
    ids = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = sizeof(entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            ids.add(int(entry.th32ProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
        err = ctypes.get_last_error()
        if err not in (0, 18):
            raise OSError(err, "Process32NextW")
    finally:
        if not k32.CloseHandle(snap):
            raise OSError(ctypes.get_last_error(), "CloseHandle(snapshot)")
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-sha256", required=True)
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info[:2] != (3, 10) or Path(sys.executable).resolve() != PYTHON310.resolve():
        raise SystemExit("refusing: exact Windows Python 3.10 runtime required")
    if len(args.admission_sha256) != 64 or not ADMISSION.is_file() or sha256(ADMISSION) != args.admission_sha256.lower():
        raise SystemExit("refusing: admission pin mismatch")
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    if admission.get("admitted") is not True or admission.get("scope") != "zeInit_GPU_ONLY_then_zeDriverGet_count_only":
        raise SystemExit("refusing: task scope not admitted")
    paths = {"worker_sha256": WORKER, "controller_sha256": CONTROLLER, "driver_sha256": DRIVER,
             "supervisor_sha256": SUPERVISOR, "python_sha256": PYTHON310,
             "loader_sha256": LOADER, "header_sha256": HEADER}
    before = {key: sha256(path) if path.is_file() else None for key, path in paths.items()}
    for key, expected in EXPECTED.items():
        if before.get(key) is None or (expected and before[key] != expected):
            raise SystemExit("refusing: local input pin mismatch: " + key)
        if admission.get(key) != before[key]:
            raise SystemExit("refusing: admission differs from actual pin: " + key)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = HERE / "runs" / ("run_" + stamp)
    if run_dir.exists():
        raise SystemExit("refusing: run directory exists")
    run_dir.mkdir(parents=True)
    command = [str(PYTHON310), str(CONTROLLER)]
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(HERE), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            shell=False, close_fds=True, creationflags=CREATE_NO_WINDOW)
    controller_pid = proc.pid
    timeout = False
    controller_reaped = False
    try:
        stdout, stderr = proc.communicate(timeout=OUTER_TIMEOUT_S)
        controller_reaped = proc.poll() is not None
    except subprocess.TimeoutExpired:
        timeout = True
        proc.kill()  # Only this retained Popen child is terminated.
        try:
            stdout, stderr = proc.communicate(timeout=8.0)
            controller_reaped = proc.poll() is not None
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b"controller_output_unavailable_after_owned_kill"
    elapsed = time.monotonic() - start
    capture_ok = len(stdout) <= MAX_CAPTURE and len(stderr) <= MAX_CAPTURE
    if not capture_ok:
        stdout = stdout[:MAX_CAPTURE]
        stderr = stderr[:MAX_CAPTURE]
    out_path, err_path = run_dir / "controller.stdout.bin", run_dir / "controller.stderr.bin"
    out_path.write_bytes(stdout)
    err_path.write_bytes(stderr)
    try:
        alive = process_ids()
        controller_absent = controller_pid not in alive
    except Exception:
        alive = None
        controller_absent = False
    after = {key: sha256(path) if path.is_file() else None for key, path in paths.items()}
    controller_exit = proc.returncode
    result = None
    parse_error = None
    if not timeout and capture_ok and controller_exit == 0:
        try:
            result = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
        except Exception as exc:
            parse_error = type(exc).__name__
    workers = (result or {}).get("result", {}).get("workers", [])
    worker_pids = [int(w["pid"]) for w in workers if isinstance(w, dict) and isinstance(w.get("pid"), int)]
    worker_pids_absent = None if alive is None or len(workers) != 1 else all(pid not in alive for pid in worker_pids)
    supervisor_result = (result or {}).get("result", {})
    probe = (result or {}).get("probe_stdout_json")
    job_clean = (supervisor_result.get("status") == "PROCESS_COMPLETED"
                 and supervisor_result.get("job_active_count") == 0
                 and supervisor_result.get("drain_proof") == "CLEANUP"
                 and all(w.get("assigned") is True and w.get("resumed") is True for w in workers))
    gates_passed = (not timeout and controller_reaped and capture_ok and controller_exit == 0 and controller_absent is True
                and before == after and (result or {}).get("controller_status") == "RETURNED"
                and (result or {}).get("restart_matches") is True
                and (result or {}).get("restart_commit_verified") is True
                and len(workers) == 1 and len(worker_pids) == 1 and workers[0].get("worker_id") == "levelzero_probe"
                and worker_pids_absent is True and job_clean and isinstance(probe, dict))
    outcome = (probe or {}).get("status", "UNPARSED")
    receipt = {
        "schema": "level-zero-loader-smoke-receipt-v1",
        "admission_path": str(ADMISSION), "admission_sha256": args.admission_sha256.lower(),
        "command": command, "cwd": str(HERE), "controller_pid": controller_pid,
        "controller_exit_code": controller_exit, "controller_timeout": timeout,
        "controller_reaped": controller_reaped,
        "controller_elapsed_seconds": round(elapsed, 6), "controller_pid_absent_after_wait": controller_absent,
        "stdout_path": str(out_path), "stdout_sha256": sha256(out_path), "stdout_bytes": out_path.stat().st_size,
        "stderr_path": str(err_path), "stderr_sha256": sha256(err_path), "stderr_bytes": err_path.stat().st_size,
        "capture_limit_bytes_per_stream": MAX_CAPTURE, "capture_ok": capture_ok,
        "input_hashes_before": before, "input_hashes_after": after, "input_hashes_unchanged": before == after,
        "supervisor_result": supervisor_result, "restart_matches": (result or {}).get("restart_matches"),
        "restart_commit_verified": (result or {}).get("restart_commit_verified"),
        "worker_pids": worker_pids, "worker_pids_absent_after_cleanup": worker_pids_absent,
        "job_status": supervisor_result.get("status"), "job_active_count": supervisor_result.get("job_active_count"),
        "drain_proof": supervisor_result.get("drain_proof"), "probe": probe,
        "probe_outcome": outcome, "parse_error": parse_error,
        "containment_and_receipt_gates_passed": gates_passed,
        "p2p_claim": "UNPROVEN", "vendor_qualification": "NOT_PERFORMED",
        "whole_tree_certificate": supervisor_result.get("whole_tree_certificate", False),
    }
    atomic_json(run_dir / "outer_receipt.json", receipt)
    print(json.dumps({"run_dir": str(run_dir), "containment_and_receipt_gates_passed": gates_passed,
                      "probe_outcome": outcome, "controller_pid": controller_pid,
                      "controller_exit": controller_exit}, separators=(",", ":")))
    return 0 if gates_passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
