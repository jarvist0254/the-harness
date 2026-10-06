"""One bounded, read-only Vulkan loader/device capability query."""
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
VULKANINFO = Path(r"E:\the_harness\records\build_vulkan_real\toolchain\sdk\Bin\vulkaninfoSDK.exe")
EXPECTED_SHA256 = "3dd853ca5acb16f6bc99fd00b5bb40783acf65b386aa9f6a3fdfa36122d52273"
SDK_BIN = VULKANINFO.parent
TIME_LIMIT_SECONDS = 30.0
STREAM_LIMIT_BYTES = 2 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def bounded_reader(pipe, destination, max_bytes, state):
    data = bytearray()
    total = 0
    try:
        while True:
            block = pipe.read(8192)
            if not block:
                break
            total += len(block)
            if len(data) < max_bytes:
                data.extend(block[:max_bytes - len(data)])
    except Exception as exc:
        state["read_error"] = type(exc).__name__
    finally:
        destination.write_bytes(bytes(data))
        state["captured_bytes"] = len(data)
        state["observed_bytes"] = total
        state["truncated"] = total > max_bytes


def main():
    if os.name != "nt":
        print(json.dumps({"status": "NOT_CHECKED", "reason": "native_windows_required"}))
        return 2
    if not VULKANINFO.is_file() or sha256(VULKANINFO) != EXPECTED_SHA256:
        print(json.dumps({"status": "NOT_CHECKED", "reason": "vulkaninfo_hash_mismatch"}))
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = HERE / ("vulkaninfo_" + stamp + ".stdout.txt")
    err = HERE / ("vulkaninfo_" + stamp + ".stderr.txt")
    receipt_path = HERE / ("vulkaninfo_" + stamp + ".receipt.json")
    command = [str(VULKANINFO)]
    before = sha256(VULKANINFO)
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(SDK_BIN), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, creationflags=CREATE_NO_WINDOW, close_fds=True)
    pid = proc.pid
    out_state, err_state = {}, {}
    out_thread = threading.Thread(target=bounded_reader, args=(proc.stdout, out, STREAM_LIMIT_BYTES, out_state), daemon=True)
    err_thread = threading.Thread(target=bounded_reader, args=(proc.stderr, err, STREAM_LIMIT_BYTES, err_state), daemon=True)
    out_thread.start()
    err_thread.start()
    timed_out = False
    try:
        proc.wait(timeout=TIME_LIMIT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()  # Acts through the retained Popen process handle for this child.
        proc.wait(timeout=5.0)
    out_thread.join(timeout=5.0)
    err_thread.join(timeout=5.0)
    elapsed = time.monotonic() - start
    after = sha256(VULKANINFO)
    reader_done = not out_thread.is_alive() and not err_thread.is_alive()
    receipt = {
        "status": "TIMEOUT" if timed_out else ("QUERY_COMPLETED" if proc.returncode == 0 and reader_done and out_state.get("read_error") is None and err_state.get("read_error") is None else "QUERY_FAILED"),
        "command": command,
        "cwd": str(SDK_BIN),
        "vulkaninfo_path": str(VULKANINFO),
        "tool_sha256_before": before,
        "tool_sha256_after": after,
        "tool_hash_unchanged": before == after == EXPECTED_SHA256,
        "sdk_version_from_file_version": "1.4.363.0",
        "pid": pid,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 6),
        "stdout_path": out.name,
        "stderr_path": err.name,
        "stdout_sha256": sha256(out) if out.is_file() else None,
        "stderr_sha256": sha256(err) if err.is_file() else None,
        "stdout_capture": out_state,
        "stderr_capture": err_state,
        "readers_finished": reader_done,
        "vulkaninfo_help_or_driver_install": False,
        "device_context_or_resource_allocation": False,
        "limitations": ["extension support is not an interoperability guarantee", "no cross-vendor memory import or allocation was attempted", "no physical VRAM/P2P claim"],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path), "stdout": str(out), "stderr": str(err), "elapsed_seconds": receipt["elapsed_seconds"], "exit_code": receipt["exit_code"]}))
    return 0 if receipt["status"] == "QUERY_COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
