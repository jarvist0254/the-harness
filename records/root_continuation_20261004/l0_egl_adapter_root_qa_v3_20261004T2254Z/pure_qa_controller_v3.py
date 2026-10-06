from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from datetime import datetime, timezone

ROOT = Path(r"E:\the_harness\records\root_continuation_20261004\l0_egl_adapter_root_qa_v3_20261004T2254Z")
SOURCE = Path(r"E:\the_harness\records\factory_runs\20261004\l0_egl_sync_bridge_two_prep_20261004T212837Z\qwen_l0_egl_fence_adapter\source.qwen_untrusted.py")
PROVIDER_TESTS = Path(r"E:\the_harness\records\factory_runs\20261004\l0_egl_sync_bridge_two_prep_20261004T212837Z\qwen_l0_egl_fence_adapter\tests_source.qwen_untrusted.txt")
TESTS = ROOT / "test_adapter_independent_contract_v3.py"
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
ROOT_ADMISSION = ROOT / "ROOT_PURE_QA_ADMISSION_V3.json"
CAP_BYTES = 128 * 1024
DEADLINE_SECONDS = 20
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
EXPECTED = {
    "source_sha256": "99375e8072f22a7103517e0772f327b232dd3134f1f6820039a42a55f37c017c",
    "provider_tests_sha256": "0e4372f0c706c2e7f9b5ba8354b4e46b7c70649b2f585e8824ab1c8598014491",
    "python_sha256": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)


def capture_child(argv: list[str], env: dict[str, str], out_dir: Path) -> dict:
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        env=env,
        shell=False,
        creationflags=CREATE_NO_WINDOW,
    )
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    eof = {"stdout": False, "stderr": False}
    reader_errors = []
    overflow = threading.Event()

    def drain(pipe, name: str) -> None:
        try:
            while True:
                chunk = pipe.read(8192)
                if not chunk:
                    eof[name] = True
                    return
                room = CAP_BYTES - len(buffers[name])
                if room > 0:
                    buffers[name].extend(chunk[:room])
                if len(chunk) > room:
                    overflow.set()
        except BaseException as exc:
            reader_errors.append(f"{name}:{type(exc).__name__}")

    readers = [
        threading.Thread(target=drain, args=(proc.stdout, "stdout"), daemon=True),
        threading.Thread(target=drain, args=(proc.stderr, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    killed = False
    while proc.poll() is None:
        if overflow.is_set() or time.monotonic() - started >= DEADLINE_SECONDS:
            timed_out = not overflow.is_set()
            killed = True
            proc.kill()  # Only the child created and retained by this controller.
            break
        time.sleep(0.05)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        killed = True
    for reader in readers:
        reader.join(timeout=5)
    reader_threads_done = all(not reader.is_alive() for reader in readers)
    streams_complete = reader_threads_done and all(eof.values()) and not reader_errors

    result = {
        "argv": argv,
        "pid": proc.pid,
        "started_utc": started_utc,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "returncode": proc.poll(),
        "timed_out": timed_out,
        "outer_killed_owned_child": killed,
        "owned_child_exited": proc.poll() is not None,
        "stream_overflow": overflow.is_set(),
        "reader_eof": dict(eof),
        "reader_threads_done": reader_threads_done,
        "streams_complete": streams_complete,
        "reader_errors": list(reader_errors),
    }
    for name, data in buffers.items():
        path = out_dir / f"{name}.bin"
        write_new(path, bytes(data))
        result[name + "_path"] = str(path)
        result[name + "_sha256"] = sha(path)
        result[name + "_bytes"] = path.stat().st_size
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Root-admitted pure adapter QA only")
    parser.add_argument("--admission-sha256", required=True)
    args = parser.parse_args()

    if len(args.admission_sha256) != 64:
        raise SystemExit("refusing: admission SHA-256 required")
    expected_local = {
        SOURCE: EXPECTED["source_sha256"],
        PROVIDER_TESTS: EXPECTED["provider_tests_sha256"],
        TESTS: None,
        PYTHON: EXPECTED["python_sha256"],
        Path(__file__).resolve(): None,
    }
    for path, expected in expected_local.items():
        if not path.is_file():
            raise SystemExit(f"refusing: missing pinned input {path.name}")
        if expected is not None and sha(path) != expected:
            raise SystemExit(f"refusing: input pin mismatch {path.name}")

    admission_bytes = ROOT_ADMISSION.read_bytes()
    if hashlib.sha256(admission_bytes).hexdigest() != args.admission_sha256.lower():
        raise SystemExit("refusing: root admission hash mismatch")
    admission = json.loads(admission_bytes.decode("utf-8"))
    required = {
        "scope": "PURE_CALLBACK_STATE_MACHINE_TESTS_ONLY",
        "admitted": True,
        "source_sha256": sha(SOURCE),
        "independent_tests_sha256": sha(TESTS),
        "controller_sha256": sha(Path(__file__).resolve()),
        "python_sha256": sha(PYTHON),
        "deadline_seconds": DEADLINE_SECONDS,
        "per_stream_cap_bytes": CAP_BYTES,
        "provider_tests_executed": False,
        "native_or_gpu_calls": False,
    }
    if any(admission.get(key) != value for key, value in required.items()):
        raise SystemExit("refusing: root admission fields do not match this exact pure QA scope")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "runs" / f"pure_qa_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    before = {str(path): sha(path) for path in expected_local}
    if before[str(TESTS)] != admission["independent_tests_sha256"]:
        raise SystemExit("refusing: independent tests hash mismatch")

    # Minimal child environment. Values are not emitted into receipts.
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP") if k in os.environ}
    env["PROTOCOL_ADAPTER_CANDIDATE"] = str(SOURCE)
    argv = [str(PYTHON), "-I", "-B", str(TESTS)]
    run = capture_child(argv, env, out_dir)
    after = {str(path): sha(path) for path in expected_local}
    unchanged = before == after
    if not unchanged:
        raise SystemExit("source/test/controller/runtime hash changed during QA")
    receipt = {
        "scope": "PURE_CALLBACK_STATE_MACHINE_TESTS_ONLY",
        "status": "PURE_QA_PASSED" if run["owned_child_exited"] and run["returncode"] == 0 and not run["timed_out"] and not run["stream_overflow"] and run["streams_complete"] else "PURE_QA_FAILED_OR_INCOMPLETE",
        "admission_sha256": args.admission_sha256.lower(),
        "pins_before": before,
        "pins_after": after,
        "pins_unchanged": unchanged,
        "run": run,
        "provider_tests_executed": False,
        "native_or_gpu_calls": False,
    }
    write_new(out_dir / "receipt.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": receipt["status"], "result": run["returncode"], "pid": run["pid"], "elapsed_seconds": run["elapsed_seconds"], "receipt": str(out_dir / "receipt.json")}))
    return 0 if receipt["status"] == "PURE_QA_PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
