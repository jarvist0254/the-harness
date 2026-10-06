"""Owned child controller for the bounded Windows native supervisor fixture."""
import argparse
import hashlib
import importlib.util
import json
import os
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor.py")
SOURCE_SHA256 = "4d8272aa5dbc330e4199b216bd9b3fd3d240c2c8d1c59e223e37d249c936f663"
WORKER = HERE / "worker.py"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, choices=("natural", "nonzero", "timeout", "cancel", "overflow"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if os.name != "nt" or sys_version() != (3, 10):
        print(json.dumps({"controller_status": "NOT_CHECKED", "reason": "runtime_mismatch"}))
        return 2
    if sha256(SOURCE) != SOURCE_SHA256 or not SOURCE.is_file() or not WORKER.is_file():
        print(json.dumps({"controller_status": "FAILED", "reason": "source_hash_mismatch"}))
        return 2
    spec = importlib.util.spec_from_file_location("fixture_contained_supervisor", SOURCE)
    if spec is None or spec.loader is None:
        print(json.dumps({"controller_status": "FAILED", "reason": "source_import_failed"}))
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if args.case == "natural":
        worker_ids = ["natural_a", "natural_b", "natural_c", "natural_d"]
        worker_mode = "natural"
    else:
        worker_ids = [args.case + "_worker"]
        worker_mode = args.case
    py = Path(sys_executable())
    executable_hash = sha256(py)
    workers = [
        {
            "worker_id": worker_id,
            "argv": [str(py), str(WORKER), worker_id, worker_mode],
            "executable_sha256": executable_hash,
            "cwd": str(HERE),
        }
        for worker_id in worker_ids
    ]
    manifest = {
        "version": 1,
        "run_id": "native_" + args.case,
        "workers": workers,
        "deadline_seconds": 1 if args.case == "timeout" else 5,
        "startup_seconds": 5,
        "log_limit_bytes": 1024,
        "containment_policy": "kill_on_close",
    }
    cancel = threading.Event()
    timer = None
    if args.case == "cancel":
        timer = threading.Timer(0.25, cancel.set)
        timer.daemon = True
        timer.start()
    result = module.run_workers(manifest, args.output, cancel_event=cancel)
    if timer is not None:
        timer.cancel()
    restarted = module.restart_receipt(args.output, manifest["run_id"])
    restart_matches = (
        restarted.get("run_id") == manifest["run_id"]
        and restarted.get("status") == result.get("status")
        and restarted.get("failure_reason") == result.get("failure_reason")
        and restarted.get("drain_proof") == result.get("drain_proof")
        and restarted.get("reattach") is False
        and restarted.get("replay") is False
    )
    source_hash_after = sha256(SOURCE)
    worker_hash_after = sha256(WORKER)
    print(json.dumps({
        "controller_status": "RETURNED",
        "result": result,
        "restart_receipt": restarted,
        "restart_matches": restart_matches,
        "source_hash_before": SOURCE_SHA256,
        "source_hash_after": source_hash_after,
        "worker_hash_after": worker_hash_after,
        "restart_commit_verified": restart_matches and source_hash_after == SOURCE_SHA256,
    }, separators=(",", ":")), flush=True)
    return 0


def sys_executable():
    import sys
    return sys.executable


def sys_version():
    import sys
    return sys.version_info[:2]


if __name__ == "__main__":
    raise SystemExit(main())
