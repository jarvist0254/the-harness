"""Single-case diagnostic wrapper; delegates all observed native calls unchanged."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor.py")
WORKER = Path(r"E:\the_harness\records\root_continuation_20261004\supervisor_native_fixture\worker.py")
SOURCE_SHA256 = "4d8272aa5dbc330e4199b216bd9b3fd3d240c2c8d1c59e223e37d249c936f663"
WORKER_SHA256 = "6d9cffd5e7a610f69754c513789d45ed88286a57a79c8c08830b88a9c39efc31"
MAX_TRACE_BYTES = 65536
MAX_EVENTS = 128
MAX_LINE_BYTES = 2048
WATCH = {
    "TerminateProcess", "WaitForSingleObject", "GetExitCodeProcess", "CloseHandle",
    "TerminateJobObject", "QueryInformationJobObject",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


class EventSink:
    def __init__(self, path):
        self.handle = Path(path).open("xb")
        self.bytes = 0
        self.count = 0
        self.dropped = 0

    def emit(self, event):
        if self.count >= MAX_EVENTS:
            self.dropped += 1
            return
        data = (json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        if len(data) > MAX_LINE_BYTES or self.bytes + len(data) > MAX_TRACE_BYTES:
            self.dropped += 1
            return
        try:
            self.handle.write(data)
            self.handle.flush()
        except Exception:
            self.dropped += 1
            return
        self.bytes += len(data)
        self.count += 1

    def close(self):
        self.handle.close()


class DelegatingProxy:
    """Logs selected methods and returns/re-raises the exact delegated outcome."""
    def __init__(self, target, api_group, sink):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_api_group", api_group)
        object.__setattr__(self, "_sink", sink)

    def __getattr__(self, name):
        target = object.__getattribute__(self, "_target")
        value = getattr(target, name)
        if name not in WATCH or not callable(value):
            return value
        group = object.__getattribute__(self, "_api_group")
        sink = object.__getattribute__(self, "_sink")

        def call_through(*args, **kwargs):
            started = time.monotonic_ns()
            try:
                result = value(*args, **kwargs)
            except BaseException as exc:
                event = {
                    "api": group + "." + name,
                    "outcome": "exception",
                    "exception_type": type(exc).__name__,
                    "winerror": getattr(exc, "winerror", None),
                    "hresult": getattr(exc, "hresult", None),
                    "elapsed_ns": time.monotonic_ns() - started,
                    "arg_types": [type(arg).__name__ for arg in args],
                }
                sink.emit(event)
                raise
            event = {
                "api": group + "." + name,
                "outcome": "return",
                "result_type": type(result).__name__,
                "result": result if result is None or type(result) in (bool, int) else None,
                "elapsed_ns": time.monotonic_ns() - started,
                "arg_types": [type(arg).__name__ for arg in args],
            }
            if type(result) is bool and not result or type(result) is int and result == 0 and name not in ("WaitForSingleObject",):
                error = ctypes.get_last_error()
                event["native_winerror"] = int(error)
                sink.emit(event)
                ctypes.set_last_error(error)
            else:
                sink.emit(event)
            return result

        return call_through


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--trace", required=True)
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info[:2] != (3, 10):
        print(json.dumps({"controller_status": "NOT_CHECKED", "reason": "runtime_mismatch"}))
        return 2
    before = {"source": sha256(SOURCE), "worker": sha256(WORKER)}
    if before != {"source": SOURCE_SHA256, "worker": WORKER_SHA256}:
        print(json.dumps({"controller_status": "FAILED", "reason": "input_hash_mismatch", "hashes_before": before}))
        return 2
    sink = EventSink(args.trace)
    spec = importlib.util.spec_from_file_location("traced_contained_supervisor", SOURCE)
    if spec is None or spec.loader is None:
        sink.close()
        print(json.dumps({"controller_status": "FAILED", "reason": "source_import_failed"}))
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    original_imports = module._imports
    original_kernel = module._kernel

    def traced_imports():
        deps = original_imports()
        deps["_winapi"] = DelegatingProxy(deps["_winapi"], "_winapi", sink)
        return deps

    def traced_kernel(deps):
        return DelegatingProxy(original_kernel(deps), "kernel32", sink)

    module._imports = traced_imports
    module._kernel = traced_kernel

    executable = Path(sys.executable)
    manifest = {
        "version": 1,
        "run_id": "native_nonzero_trace",
        "workers": [{
            "worker_id": "nonzero_worker",
            "argv": [str(executable), str(WORKER), "nonzero_worker", "nonzero"],
            "executable_sha256": sha256(executable),
            "cwd": str(WORKER.parent),
        }],
        "deadline_seconds": 5,
        "startup_seconds": 5,
        "log_limit_bytes": 1024,
        "containment_policy": "kill_on_close",
    }
    result = module.run_workers(manifest, args.output)
    restarted = module.restart_receipt(args.output, manifest["run_id"])
    restart_matches = (
        restarted.get("run_id") == result.get("run_id")
        and restarted.get("status") == result.get("status")
        and restarted.get("failure_reason") == result.get("failure_reason")
        and restarted.get("drain_proof") == result.get("drain_proof")
        and restarted.get("reattach") is False
        and restarted.get("replay") is False
    )
    sink.close()
    after = {"source": sha256(SOURCE), "worker": sha256(WORKER)}
    payload = {
        "controller_status": "RETURNED",
        "result": result,
        "restart_receipt": restarted,
        "restart_matches": restart_matches,
        "hashes_before": before,
        "hashes_after": after,
        "hashes_unchanged": before == after,
        "trace": {"path": Path(args.trace).name, "event_count": sink.count, "dropped_events": sink.dropped, "bytes": sink.bytes, "complete": sink.dropped == 0},
    }
    print(json.dumps(payload, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
