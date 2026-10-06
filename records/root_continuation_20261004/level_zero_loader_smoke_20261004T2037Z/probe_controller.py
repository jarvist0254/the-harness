import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPERVISOR = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py")
SUPERVISOR_SHA256 = "3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c"
WORKER = HERE / "levelzero_probe_worker.py"
PYTHON310 = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
PYTHON310_SHA256 = "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260"
LOADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\runtime_source\build\bin\ze_loader.dll")
LOADER_SHA256 = "0838c395a7393c313fdfeff8cea5d08a71ba044dc28f793aa4f7d28f60095162"
HEADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h")
HEADER_SHA256 = "c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if os.name != "nt" or sys.version_info[:2] != (3, 10):
        print(json.dumps({"controller_status": "NOT_CHECKED", "reason": "runtime_mismatch"}))
        return 2
    pins = {"supervisor": (SUPERVISOR, SUPERVISOR_SHA256),
            "worker": (WORKER, None), "python310": (PYTHON310, PYTHON310_SHA256),
            "loader": (LOADER, LOADER_SHA256), "sdk_header": (HEADER, HEADER_SHA256)}
    before = {name: sha256(path) if path.is_file() else None for name, (path, _) in pins.items()}
    for name, (path, expected) in pins.items():
        if before[name] is None or (expected is not None and before[name] != expected):
            print(json.dumps({"controller_status": "NOT_CHECKED", "reason": "pin_mismatch", "pin": name,
                              "source_hashes_before": before}, separators=(",", ":")))
            return 2
    spec = importlib.util.spec_from_file_location("contained_supervisor_revision2", SUPERVISOR)
    if spec is None or spec.loader is None:
        print(json.dumps({"controller_status": "NOT_CHECKED", "reason": "supervisor_import_failed"}))
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run_id = "levelzero_loader_smoke"
    supervisor_output = HERE / "supervisor_output"
    manifest = {
        "version": 1,
        "run_id": run_id,
        "workers": [{
            "worker_id": "levelzero_probe",
            "argv": [str(PYTHON310), str(WORKER)],
            "executable_sha256": PYTHON310_SHA256,
            "cwd": str(HERE),
        }],
        "deadline_seconds": 5,
        "startup_seconds": 3,
        "log_limit_bytes": 4096,
        "containment_policy": "kill_on_close",
    }
    try:
        result = module.run_workers(manifest, supervisor_output)
        restarted = module.restart_receipt(supervisor_output, run_id)
    except Exception as exc:
        after = {name: sha256(path) if path.is_file() else None for name, (path, _) in pins.items()}
        print(json.dumps({"controller_status": "SUPERVISOR_EXCEPTION", "exception_type": type(exc).__name__,
                          "source_hashes_before": before, "source_hashes_after": after}, separators=(",", ":")))
        return 1
    restart_matches = (
        restarted.get("run_id") == run_id
        and restarted.get("status") == result.get("status")
        and restarted.get("failure_reason") == result.get("failure_reason")
        and restarted.get("drain_proof") == result.get("drain_proof")
        and restarted.get("reattach") is False
        and restarted.get("replay") is False
    )
    after = {name: sha256(path) if path.is_file() else None for name, (path, _) in pins.items()}
    unchanged = before == after
    worker_log = result.get("logs", {}).get("levelzero_probe", {})
    try:
        probe = json.loads(worker_log.get("stdout", ""))
    except Exception:
        probe = None
    payload = {
        "controller_status": "RETURNED",
        "source_hashes_before": before,
        "source_hashes_after": after,
        "source_hashes_unchanged": unchanged,
        "result": result,
        "restart_receipt": restarted,
        "restart_matches": restart_matches,
        "probe_stdout_json": probe,
        "restart_commit_verified": restart_matches and unchanged,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

