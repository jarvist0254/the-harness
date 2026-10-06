"""Root-admitted, single-run Vulkan capability-query supervisor."""
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
ADMISSION = ROOT / "ROOT_RUNTIME_ADMISSION.json"
SOURCE_ORIGINAL = ROOT / "external_memory_query.cpp"
SOURCE_COPY = BASE / "external_memory_query.cpp"
EXE = ROOT / "attempt_004/external_memory_query.exe"
EXPECTED = {
    "source": "9ae6355ddc8ff72f4c33bce5116669ad84a734e7271287490926d136ec360e8c",
    "exe": "67c69e60c12780415bfd62858536078e09d2749cc539ee3928079657bbc718b5",
    "python": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
    "timeout_seconds": 10.0,
    "capture_limit_bytes_per_stream": 262144,
}
CREATE_NO_WINDOW = 0x08000000
CAPTURE = EXPECTED["capture_limit_bytes_per_stream"]
TIMEOUT = EXPECTED["timeout_seconds"]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


class BoundedReader(threading.Thread):
    def __init__(self, pipe, path, overflow_event):
        super().__init__(daemon=True)
        self.pipe = pipe
        self.path = path
        self.overflow_event = overflow_event
        self.saved = bytearray()
        self.observed = 0
        self.error = None
        self.write_error = None

    def run(self):
        try:
            while True:
                block = self.pipe.read(16384)
                if not block:
                    break
                self.observed += len(block)
                remaining = CAPTURE - len(self.saved)
                if remaining > 0:
                    self.saved.extend(block[:remaining])
                if self.observed > CAPTURE:
                    self.overflow_event.set()
        except Exception as exc:
            self.error = type(exc).__name__
        try:
            self.path.write_bytes(self.saved)
        except Exception as exc:
            self.write_error = type(exc).__name__

    def receipt(self):
        return {
            "path": self.path.name,
            "captured_bytes": len(self.saved),
            "observed_bytes": self.observed,
            "overflow": self.observed > CAPTURE,
            "reader_error": self.error,
            "write_error": self.write_error,
            "sha256": sha256(self.path) if self.path.is_file() else None,
        }


def parse_and_validate_stdout(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    value = json.loads(text)
    if not isinstance(value, dict) or value.get("query") != "physical-device external host buffer capabilities only":
        raise ValueError("unexpected query JSON identity")
    devices = value.get("devices")
    if not isinstance(devices, list) or value.get("physical_device_count") != len(devices):
        raise ValueError("physical device count/list mismatch")
    vendors = [device.get("vendor_id_hex", "").lower() for device in devices if isinstance(device, dict)]
    if "0x10de" not in vendors or "0x1002" not in vendors:
        raise ValueError("expected NVIDIA and AMD were not both enumerated")
    intel_count = sum(1 for vendor in vendors if vendor == "0x8086")
    expected_intel_status = "ENUMERATED" if intel_count else "NOT_ENUMERATED_BY_THIS_VULKAN_INSTANCE"
    if value.get("intel_vendor_id_0x8086_devices_enumerated") != intel_count or value.get("intel_status") != expected_intel_status:
        raise ValueError("Intel enumeration accounting mismatch")
    expected_handles = {"HOST_ALLOCATION", "HOST_MAPPED_FOREIGN_MEMORY"}
    expected_usages = {"TRANSFER_SRC|TRANSFER_DST", "STORAGE_BUFFER|TRANSFER_SRC|TRANSFER_DST"}
    per_device = []
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("non-object device entry")
        if device.get("vk_ext_external_memory_host") is True:
            rows = device.get("host_memory_queries")
            if not isinstance(rows, list) or len(rows) != 4:
                raise ValueError("advertised host-memory extension must have four independent query records")
            pairs = {(row.get("handle"), row.get("usage")) for row in rows if isinstance(row, dict)}
            if len(pairs) != 4 or pairs != {(h, u) for h in expected_handles for u in expected_usages}:
                raise ValueError("query matrix does not contain the exact two handles and two usages")
            for row in rows:
                for key in ("importable", "exportable", "dedicated_only", "compatible_handle_types_hex", "export_from_imported_handle_types_hex"):
                    if key not in row:
                        raise ValueError("query feature result missing " + key)
            per_device.append({"vendor": device.get("vendor"), "name": device.get("name"), "status": "QUERIED", "queries": rows})
        else:
            rows = device.get("host_memory_queries")
            if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("status") != "UNAVAILABLE":
                raise ValueError("non-advertising device must explicitly report UNAVAILABLE")
            per_device.append({"vendor": device.get("vendor"), "name": device.get("name"), "status": "UNAVAILABLE", "reason": rows[0].get("reason")})
    return {
        "json_valid": True,
        "query_complete": True,
        "physical_device_count": len(devices),
        "nvidia_enumerated": "0x10de" in vendors,
        "amd_enumerated": "0x1002" in vendors,
        "intel_enumeration_status": expected_intel_status,
        "intel_devices_enumerated": intel_count,
        "per_device_capabilities": per_device,
        "qualification_interpretation": "Capability advertisement only; no import, memory transfer, device allocation, direct peer access, P2P, or residency test occurred.",
    }


def environment_fingerprint():
    canonical = json.dumps(sorted(os.environ.items()), separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main():
    if os.name != "nt" or Path(sys.executable).resolve() != PYTHON.resolve():
        print("NOT_CHECKED: unexpected controller runtime", file=sys.stderr)
        return 2
    if any(item.name not in {"run_query_once.py", "external_memory_query.cpp"} for item in BASE.iterdir()):
        print("NOT_CHECKED: runtime output folder is not fresh", file=sys.stderr)
        return 2
    if not SOURCE_COPY.exists():
        print("NOT_CHECKED: pinned source copy missing", file=sys.stderr)
        return 2
    inputs = {"source_original": SOURCE_ORIGINAL, "source_copy": SOURCE_COPY, "exe": EXE,
              "python": PYTHON, "admission": ADMISSION, "controller": Path(__file__)}
    before = {name: sha256(path) for name, path in inputs.items()}
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    if admission.get("adjudicator") != "ROOT" or admission.get("command_arguments") != []:
        print("NOT_CHECKED: root admission identity/arguments mismatch", file=sys.stderr)
        return 2
    expected = {"source_original": EXPECTED["source"], "source_copy": EXPECTED["source"],
                "exe": EXPECTED["exe"], "python": EXPECTED["python"]}
    actual = {name: before[name] for name in expected}
    if actual != expected or admission.get("source_sha256") != EXPECTED["source"] or admission.get("executable_sha256") != EXPECTED["exe"] or admission.get("controller_python_sha256") != EXPECTED["python"]:
        write_json(BASE / "preflight_refusal.json", {"status": "NOT_CHECKED", "reason": "input/admission hash mismatch", "expected": expected, "actual": actual})
        return 2
    if admission.get("timeout_seconds") != TIMEOUT or admission.get("capture_limit_bytes_per_stream") != CAPTURE:
        write_json(BASE / "preflight_refusal.json", {"status": "NOT_CHECKED", "reason": "runtime bound mismatch"})
        return 2

    command = [str(EXE)]
    stdout_path, stderr_path = BASE / "stdout.raw.log", BASE / "stderr.raw.log"
    overflow = threading.Event()
    env_hash_before = environment_fingerprint()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    started = time.monotonic()
    try:
        proc = subprocess.Popen(command, cwd=str(EXE.parent), env=None, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                creationflags=CREATE_NO_WINDOW, close_fds=True)
    except Exception as exc:
        write_json(BASE / "run_receipt.json", {
            "status": "LAUNCH_FAILED", "command": command, "launch_error": type(exc).__name__,
            "input_hashes_before": before, "input_hashes_after": {name: sha256(path) for name, path in inputs.items()},
            "native_scope": "No successful child launch was recorded.",
        })
        return 1
    pid = proc.pid
    out_reader = BoundedReader(proc.stdout, stdout_path, overflow)
    err_reader = BoundedReader(proc.stderr, stderr_path, overflow)
    out_reader.start(); err_reader.start()
    timed_out = False
    overflowed = False
    cleanup_wait_failed = False
    while proc.poll() is None:
        if overflow.is_set():
            overflowed = True
            break
        elapsed = time.monotonic() - started
        if elapsed >= TIMEOUT:
            timed_out = True
            break
        time.sleep(min(0.01, max(0.001, TIMEOUT - elapsed)))
    if timed_out or overflowed:
        proc.kill()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            cleanup_wait_failed = True
    else:
        proc.wait()
    out_reader.join(timeout=2.0); err_reader.join(timeout=2.0)
    elapsed = time.monotonic() - started
    after = {name: sha256(path) for name, path in inputs.items()}
    env_hash_after = environment_fingerprint()
    parent_env_unchanged = env_hash_before == env_hash_after
    bounded = not out_reader.receipt()["overflow"] and not err_reader.receipt()["overflow"]
    streams_written = all(reader.write_error is None and reader.error is None for reader in (out_reader, err_reader))
    parse_result = None
    parse_error = None
    if proc.returncode == 0 and not timed_out and not overflowed and bounded and streams_written and not cleanup_wait_failed:
        try:
            parse_result = parse_and_validate_stdout(stdout_path)
        except Exception as exc:
            parse_error = type(exc).__name__ + ": " + str(exc)
    receipt = {
        "status": "QUERY_COMPLETE" if parse_result and parse_result.get("query_complete") and streams_written else (
            "TIMEOUT" if timed_out else "OUTPUT_LIMIT_EXCEEDED" if overflowed or not bounded else "QUERY_FAILED_OR_INVALID_OUTPUT"),
        "command": command, "cwd": str(EXE.parent), "pid": pid, "exit_code": proc.returncode,
        "process_present_after_wait": proc.poll() is None, "timeout_seconds": TIMEOUT,
        "timed_out": timed_out, "overflowed": overflowed, "cleanup_wait_failed": cleanup_wait_failed,
        "elapsed_seconds": round(elapsed, 6), "start_utc": start_utc,
        "stdout": out_reader.receipt(), "stderr": err_reader.receipt(),
        "streams_written_and_read": streams_written,
        "input_hashes_before": before, "input_hashes_after": after,
        "input_hashes_unchanged": before == after, "parent_environment_unchanged": parent_env_unchanged,
        "json_validation": parse_result, "json_validation_error": parse_error,
        "parent_environment_sha256_before": env_hash_before,
        "parent_environment_sha256_after": env_hash_after,
        "native_scope": "Vulkan instance/physical-device capability queries only; no VkDevice, buffers, allocation, import, semaphore, queue, or GPU work",
        "capability_results_are_not_transfer_proof": True,
        "runtime_source_hash": before["source_original"], "runtime_executable_hash": before["exe"],
        "runtime_python_hash": before["python"], "runtime_admission_hash": before["admission"],
    }
    write_json(BASE / "run_receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "exit_code": proc.returncode,
                      "elapsed_seconds": receipt["elapsed_seconds"], "pid": pid,
                      "query_complete": bool(parse_result and parse_result.get("query_complete")),
                      "hashes_unchanged": before == after}))
    return 0 if receipt["status"] == "QUERY_COMPLETE" and before == after and parent_env_unchanged and streams_written else 1


if __name__ == "__main__":
    raise SystemExit(main())
