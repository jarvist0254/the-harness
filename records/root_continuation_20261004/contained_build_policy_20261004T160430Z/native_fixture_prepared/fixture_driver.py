"""Bounded, fixed-case outer runner for the admitted native supervisor fixture."""
import argparse
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
CONTRACT = HERE / "fixture_contract.json"
EXPECTED_PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
EXPECTED_PYTHON_SHA256 = "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260"
EXPECTED_SOURCE_SHA256 = "fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3"
CREATE_NO_WINDOW = 0x08000000
MAX_CAPTURE = 128 * 1024
CONTROLLER_BOUND_SECONDS = 30.0


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    temp = path.with_name(path.name + ".part")
    data = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
    with temp.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def process_ids():
    """Return a snapshot of current process IDs using Toolhelp; never opens/kills by PID."""
    import ctypes

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
    snapshot = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid:
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


def verify_static_gate():
    if os.name != "nt":
        raise RuntimeError("native_windows_required")
    if sys.version_info[:2] != (3, 10) or Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise RuntimeError("unexpected_interpreter")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    admission = json.loads((HERE / "fixture_admission.json").read_text(encoding="utf-8"))
    source = Path(contract["source"])
    pinned = {
        "source": (source, admission["source"]["sha256"]),
        "interpreter": (EXPECTED_PYTHON, admission["runtime"]["sha256"]),
        "fixture_contract.json": (CONTRACT, admission["fixture_hashes_sha256"]["fixture_contract.json"]),
        "fixture_driver.py": (Path(__file__), admission["fixture_hashes_sha256"]["fixture_driver.py"]),
        "fixture_controller.py": (HERE / "fixture_controller.py", admission["fixture_hashes_sha256"]["fixture_controller.py"]),
        "worker.py": (HERE / "worker.py", admission["fixture_hashes_sha256"]["worker.py"]),
    }
    for label, (path, expected) in pinned.items():
        if not isinstance(expected, str) or len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise RuntimeError("invalid_pin:" + label)
        if sha256(path) != expected:
            raise RuntimeError("hash_mismatch:" + label)
    if admission.get("run_command") != [str(EXPECTED_PYTHON), str(Path(__file__).resolve()), "--run"]:
        raise RuntimeError("command_pin_mismatch")
    return source


def run_case(case_id, run_root):
    case_root = run_root / case_id
    if case_root.exists():
        raise RuntimeError("case_output_exists")
    case_root.mkdir()
    supervisor_output = case_root / "supervisor_output"
    command = [str(EXPECTED_PYTHON), str(HERE / "fixture_controller.py"), "--case", case_id, "--output", str(supervisor_output)]
    source_path = Path(json.loads(CONTRACT.read_text(encoding="utf-8"))["source"])
    hashes_before = {
        "source": sha256(source_path),
        "contract": sha256(CONTRACT),
        "admission": sha256(HERE / "fixture_admission.json"),
        "driver": sha256(Path(__file__)),
        "controller": sha256(HERE / "fixture_controller.py"),
        "worker": sha256(HERE / "worker.py"),
        "interpreter": sha256(EXPECTED_PYTHON),
    }
    started = time.monotonic()
    proc = subprocess.Popen(
        command,
        cwd=str(HERE),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )
    controller_pid = proc.pid
    timed_out = False
    try:
        out, err = proc.communicate(timeout=CONTROLLER_BOUND_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()  # This is the retained Popen handle for this controller only.
        out, err = proc.communicate(timeout=8.0)
    elapsed = time.monotonic() - started
    if len(out) > MAX_CAPTURE or len(err) > MAX_CAPTURE:
        capture_ok = False
        out = out[:MAX_CAPTURE]
        err = err[:MAX_CAPTURE]
    else:
        capture_ok = True
    (case_root / "controller_stdout.log").write_bytes(out)
    (case_root / "controller_stderr.log").write_bytes(err)
    controller_exit = proc.returncode
    controller_absent = controller_pid not in process_ids()
    hashes_after = {
        "source": sha256(source_path),
        "contract": sha256(CONTRACT),
        "admission": sha256(HERE / "fixture_admission.json"),
        "driver": sha256(Path(__file__)),
        "controller": sha256(HERE / "fixture_controller.py"),
        "worker": sha256(HERE / "worker.py"),
        "interpreter": sha256(EXPECTED_PYTHON),
    }
    record = {
        "case_id": case_id,
        "command": command,
        "cwd": str(HERE),
        "controller_pid": controller_pid,
        "controller_exit_code": controller_exit,
        "controller_timeout": timed_out,
        "controller_elapsed_seconds": round(elapsed, 6),
        "controller_pid_absent_after_wait": controller_absent,
        "source_and_runtime_hashes_before": hashes_before,
        "source_and_runtime_hashes_after": hashes_after,
        "source_and_runtime_hashes_unchanged": hashes_before == hashes_after,
        "stdout_bytes": len(out),
        "stderr_bytes": len(err),
        "capture_limit_ok": capture_ok,
        "worker_pids": [],
        "worker_pids_absent_after_cleanup": None,
        "supervisor_status": None,
        "supervisor_failure_reason": None,
        "accepted": False,
    }
    if timed_out or not controller_absent or not capture_ok or controller_exit != 0 or hashes_before != hashes_after:
        record["outer_failure"] = "controller_timeout_or_exit_or_capture_or_process_check"
        atomic_json(case_root / "outer_case_receipt.json", record)
        return record
    try:
        lines = out.decode("utf-8").strip().splitlines()
        payload = json.loads(lines[-1])
        result = payload["result"]
        workers = result["workers"]
        pids = [int(worker["pid"]) for worker in workers]
        alive = process_ids()
        pids_absent = not any(pid in alive for pid in pids)
        record.update({
            "worker_pids": pids,
            "worker_pids_absent_after_cleanup": pids_absent,
            "supervisor_status": result.get("status"),
            "supervisor_failure_reason": result.get("failure_reason"),
            "supervisor": result,
            "restart_receipt": payload.get("restart_receipt"),
            "restart_matches": payload.get("restart_matches"),
            "restart_commit_verified": payload.get("restart_commit_verified"),
            "controller_source_hash_after": payload.get("source_hash_after"),
            "controller_worker_hash_after": payload.get("worker_hash_after"),
        })
        record["accepted"] = (
            payload.get("controller_status") == "RETURNED"
            and payload.get("restart_matches") is True
            and payload.get("restart_commit_verified") is True
            and payload.get("source_hash_after") == EXPECTED_SOURCE_SHA256
            and payload.get("worker_hash_after") == hashes_before["worker"]
            and case_expectation(case_id, result, pids_absent)
        )
    except Exception as exc:
        record["outer_failure"] = "malformed_controller_result:" + type(exc).__name__
    atomic_json(case_root / "outer_case_receipt.json", record)
    return record


def case_expectation(case_id, result, pids_absent):
    status = result.get("status")
    if not pids_absent or result.get("drain_proof") != "CLEANUP" or result.get("whole_tree_certificate") is not False:
        return False
    workers = result.get("workers", [])
    if case_id == "natural":
        return (
            status == "PROCESS_COMPLETED"
            and len(workers) == 4
            and all(w.get("assigned") and w.get("resumed") and w.get("exit_code") == 0 for w in workers)
            and result.get("job_active_count") == 0
            and len(result.get("logs", {})) == 4
            and all(
                result["logs"][w["worker_id"]].get("stdout", "").strip() == w["worker_id"] + ":stdout"
                and result["logs"][w["worker_id"]].get("stderr", "").strip() == w["worker_id"] + ":stderr"
                for w in workers
            )
        )
    if case_id == "nonzero":
        return status == "FAILED" and result.get("failure_reason") == "nonzero_exit" and workers and workers[0].get("exit_code") == 3
    if case_id == "timeout":
        return status == "TIMEOUT" and result.get("failure_reason") == "deadline" and workers
    if case_id == "cancel":
        return status == "CANCELLED" and result.get("failure_reason") == "cancelled" and workers
    if case_id == "overflow":
        if status != "FAILED" or result.get("failure_reason") != "LOG_LIMIT" or not workers:
            return False
        stream = result.get("logs", {}).get(workers[0]["worker_id"], {})
        return stream.get("stdout_overflow") is True and stream.get("stdout_bytes") == 1024
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="execute the fixed admitted native cases")
    args = parser.parse_args()
    if not args.run:
        print("Use --run to execute the fixed native Windows fixture cases.")
        return 0
    try:
        source = verify_static_gate()
    except Exception as exc:
        print(json.dumps({"status": "NOT_CHECKED", "reason": type(exc).__name__ + ":" + str(exc)}))
        return 2
    run_id = datetime.now(timezone.utc).strftime("native_%Y%m%dT%H%M%SZ")
    runs = HERE / "native_runs"
    runs.mkdir(exist_ok=True)
    run_root = runs / run_id
    run_root.mkdir()
    case_ids = ("natural", "nonzero", "timeout", "cancel", "overflow")
    summary = {
        "run_id": run_id,
        "source": str(source),
        "source_sha256": sha256(source),
        "contract_sha256": sha256(CONTRACT),
        "admission_sha256": sha256(HERE / "fixture_admission.json"),
        "driver_sha256": sha256(Path(__file__)),
        "controller_sha256": sha256(HERE / "fixture_controller.py"),
        "worker_sha256": sha256(HERE / "worker.py"),
        "interpreter": str(EXPECTED_PYTHON),
        "interpreter_sha256": sha256(EXPECTED_PYTHON),
        "controller_bound_seconds": CONTROLLER_BOUND_SECONDS,
        "containment_policy": "kill_on_close",
        "cases": [],
        "overall": "IN_PROGRESS",
        "limitations": ["native fixture only", "point-in-time PID snapshots", "resource high-water unmeasured", "whole_tree_certificate remains false"],
    }
    atomic_json(run_root / "suite_receipt.json", summary)
    for case_id in case_ids:
        record = run_case(case_id, run_root)
        summary["cases"].append(record)
        atomic_json(run_root / "suite_receipt.json", summary)
        if case_id == "natural" and not record["accepted"]:
            summary["overall"] = "BASELINE_FAILED_STOPPED"
            break
        if record.get("outer_failure") or record.get("supervisor_status") == "UNKNOWN" or not record["accepted"]:
            summary["overall"] = "NATIVE_FIXTURE_FAILED_STOPPED"
            break
    else:
        summary["overall"] = "FIXTURE_EXPECTATIONS_MET"
    atomic_json(run_root / "suite_receipt.json", summary)
    print(json.dumps({"run_root": str(run_root), "overall": summary["overall"], "case_count": len(summary["cases"])}))
    return 0 if summary["overall"] == "FIXTURE_EXPECTATIONS_MET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
