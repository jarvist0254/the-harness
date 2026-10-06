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

ROOT = Path(r"E:\the_harness\records\root_continuation_20261004\external_cuda_capability_query_20261004T2005Z")
SRC = ROOT / "cuda_driver_capability_query.cpp"
HEADER_ROOT = Path(r"E:\the_harness\records\toolchains\cuda_driver_headers_20261004")
CUDA_H = HEADER_ROOT / "include" / "cuda.h"
TYPEDEFS_H = HEADER_ROOT / "include" / "cudaTypedefs.h"
DISTRO = "Ubuntu-24.04"
WSL = r"C:\windows\system32\wsl.exe"
WSL_SHA256 = "7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757"
WSL_ROOT = "/mnt/e/the_harness/records/root_continuation_20261004/external_cuda_capability_query_20261004T2005Z"
WSL_HEADER = "/mnt/e/the_harness/records/toolchains/cuda_driver_headers_20261004/include"
WSL_SOURCE = WSL_ROOT + "/cuda_driver_capability_query.cpp"
WSL_BINARY = WSL_ROOT + "/out/cuda_driver_capability_query"
COMPILER = "/usr/bin/c++"
HASH_TOOL = "/usr/bin/sha256sum"
LIBRARY = "/usr/lib/wsl/lib/libcuda.so.1"
EXPECTED = {
    "source_sha256": "d22e00d620d17edf1d6ab0271c977e02b480a92bc75074e41df77a263bc8c9f2",
    "cuda_h_sha256": "7a79d67ca888061b1dfbe4739b51ad64f85a2f3ad874947ce09b2c635b4c7072",
    "typedefs_h_sha256": "77eb4072ae5da75bec31c4cf6291967e8ecbd6981ece0d47b07dbbabf781782c",
    "library_sha256": "00d5773a96ab7e18d087880b8ce02741863da15c487b434999f7932f3cbe1383",
}
# The compiler process itself is bounded to 85 seconds, then gets 5 seconds
# to terminate; the capability child is bounded to 30 + 5 seconds. Outer WSL
# client deadlines add only startup/reap margin and never terminate WSL itself.
COMPILE_WORKER_S = 85
COMPILE_KILL_GRACE_S = 5
COMPILE_OUTER_S = 100
QUERY_WORKER_S = 30
QUERY_KILL_GRACE_S = 5
QUERY_OUTER_S = 45
MAX_CAPTURE = {"compile": 128 * 1024, "query": 256 * 1024, "small": 32 * 1024}
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as f:
        f.write(data)


def run_owned(label: str, argv: list[str], outer_s: int, cap: int) -> dict:
    started_at = utc_now()
    started = time.monotonic()
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW,
                            cwd=str(ROOT), shell=False)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()
    lock = threading.Lock()

    def drain(stream, name):
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            with lock:
                room = cap - len(buffers[name])
                if room > 0:
                    buffers[name].extend(chunk[:room])
                if len(chunk) > room:
                    overflow.set()

    readers = [threading.Thread(target=drain, args=(proc.stdout, "stdout"), daemon=True),
               threading.Thread(target=drain, args=(proc.stderr, "stderr"), daemon=True)]
    for thread in readers:
        thread.start()

    timed_out = False
    outer_killed = False
    while proc.poll() is None:
        if overflow.is_set():
            proc.kill()  # only the retained process created by this controller
            outer_killed = True
            break
        if time.monotonic() - started >= outer_s:
            timed_out = True
            proc.kill()  # only the retained process created by this controller
            outer_killed = True
            break
        time.sleep(0.05)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        # Keep evidence and stop. Never enumerate or kill unrelated PIDs.
        outer_killed = True
    for thread in readers:
        thread.join(timeout=5)
    ended = time.monotonic()
    return {"label": label, "argv": argv, "pid": proc.pid,
            "started_utc": started_at, "elapsed_seconds": round(ended - started, 3),
            "returncode": proc.poll(), "outer_timeout": timed_out,
            "outer_killed_owned_wsl_client": outer_killed,
            "stream_overflow": overflow.is_set(),
            "owned_client_exited": proc.poll() is not None,
            "stdout": bytes(buffers["stdout"]), "stderr": bytes(buffers["stderr"])}


def save_command_logs(run_dir: Path, index: int, result: dict) -> dict:
    out_path = run_dir / f"{index:02d}_{result['label']}.stdout.bin"
    err_path = run_dir / f"{index:02d}_{result['label']}.stderr.bin"
    write_new(out_path, result.pop("stdout"))
    write_new(err_path, result.pop("stderr"))
    result["stdout_path"] = str(out_path)
    result["stdout_sha256"] = sha256_file(out_path)
    result["stdout_bytes"] = out_path.stat().st_size
    result["stderr_path"] = str(err_path)
    result["stderr_sha256"] = sha256_file(err_path)
    result["stderr_bytes"] = err_path.stat().st_size
    return result


def wsl_argv(args: list[str]) -> list[str]:
    return [WSL, "-d", DISTRO, "--exec", *args]


def linux_bounded(args: list[str], deadline_s: int, grace_s: int = 5) -> list[str]:
    return ["/usr/bin/timeout", "--signal=TERM", f"--kill-after={grace_s}s",
            f"{deadline_s}s", *args]


def parse_sha256sum(text: str) -> dict[str, str]:
    found = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError("unexpected sha256sum output")
        found[parts[1].lstrip(" *")] = parts[0].lower()
    return found


def require_admission(path: Path, expected_hash: str, phase: str) -> dict:
    raw = path.read_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != expected_hash.lower():
        raise ValueError("admission SHA-256 mismatch")
    admission = json.loads(raw.decode("utf-8"))
    if admission.get("admitted") is not True or admission.get("phase") != phase:
        raise ValueError("root admission does not authorize this phase")
    controller_hash = sha256_file(Path(__file__).resolve())
    if admission.get("controller_sha256") != controller_hash:
        raise ValueError("controller pin mismatch")
    for key, expected in EXPECTED.items():
        if admission.get(key) != expected:
            raise ValueError(f"admission pin mismatch: {key}")
    return {"path": str(path), "sha256": actual_hash, "payload": admission}


def main() -> int:
    ap = argparse.ArgumentParser(description="Bounded CUDA query compile/run controller; execution requires a pin-bound root admission.")
    ap.add_argument("--phase", choices=("compile", "query"), required=True)
    ap.add_argument("--admission", type=Path, required=True)
    ap.add_argument("--admission-sha256", required=True)
    ap.add_argument("--binary-sha256", help="required for query phase")
    ns = ap.parse_args()
    if len(ns.admission_sha256) != 64:
        raise SystemExit("refusing: admission SHA must be 64 hex characters")
    admission = require_admission(ns.admission, ns.admission_sha256, ns.phase)
    wsl_path = Path(WSL)
    if not wsl_path.is_file() or sha256_file(wsl_path) != WSL_SHA256:
        raise SystemExit("refusing: WSL client pin mismatch")
    if ns.phase == "query" and (not ns.binary_sha256 or len(ns.binary_sha256) != 64):
        raise SystemExit("refusing: query requires the reviewed compiled binary SHA-256")

    for key, path in (("source_sha256", SRC), ("cuda_h_sha256", CUDA_H), ("typedefs_h_sha256", TYPEDEFS_H)):
        if not path.is_file() or sha256_file(path) != EXPECTED[key]:
            raise SystemExit(f"refusing: local pin mismatch for {key}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "runs" / f"{ns.phase}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = run_dir / f"{ns.phase}_receipt.json"
    results = []
    failure = None
    query_status = None

    hash_targets = [WSL_SOURCE, WSL_HEADER + "/cuda.h", WSL_HEADER + "/cudaTypedefs.h", COMPILER, LIBRARY]
    before_map = None
    if ns.phase == "query":
        hash_targets.append(WSL_BINARY)
    hash_cmd = wsl_argv(linux_bounded([HASH_TOOL, *hash_targets], 5, 2))
    before_hash = run_owned("pins_before", hash_cmd, 12, MAX_CAPTURE["small"])
    before_hash = save_command_logs(run_dir, 1, before_hash)
    results.append(before_hash)
    if before_hash["returncode"] != 0 or before_hash["outer_timeout"] or before_hash["stream_overflow"]:
        failure = "PIN_PREFLIGHT_FAILED"
    else:
        before_raw = Path(before_hash["stdout_path"]).read_text(encoding="utf-8", errors="strict")
        try:
            before_map = parse_sha256sum(before_raw)
            required_map = {WSL_SOURCE: EXPECTED["source_sha256"],
                            WSL_HEADER + "/cuda.h": EXPECTED["cuda_h_sha256"],
                            WSL_HEADER + "/cudaTypedefs.h": EXPECTED["typedefs_h_sha256"],
                            LIBRARY: EXPECTED["library_sha256"]}
            for path, digest in required_map.items():
                if before_map.get(path) != digest:
                    raise ValueError(f"WSL-visible pin mismatch for {path}")
            if COMPILER not in before_map:
                raise ValueError("compiler hash missing")
            if ns.phase == "query" and before_map.get(WSL_BINARY) != ns.binary_sha256.lower():
                raise ValueError("compiled binary pin mismatch")
        except Exception as e:
            failure = "PIN_PREFLIGHT_MISMATCH: " + str(e)

    compiler_version = None
    if failure is None:
        version_cmd = wsl_argv(linux_bounded([COMPILER, "--version"], 5, 2))
        version_res = run_owned("compiler_version", version_cmd, 12, MAX_CAPTURE["small"])
        version_res = save_command_logs(run_dir, 2, version_res)
        results.append(version_res)
        if version_res["returncode"] != 0 or version_res["outer_timeout"] or version_res["stream_overflow"]:
            failure = "COMPILER_VERSION_QUERY_FAILED"
        else:
            compiler_version = Path(version_res["stdout_path"]).read_text(encoding="utf-8", errors="replace")

    if failure is None and ns.phase == "compile":
        out_dir = ROOT / "out"
        out_dir.mkdir(exist_ok=True)
        if (out_dir / "cuda_driver_capability_query").exists():
            failure = "OUTPUT_ALREADY_EXISTS_REFUSE_OVERWRITE"
        else:
            compile_args = [COMPILER, "-std=c++17", "-I" + WSL_HEADER, WSL_SOURCE,
                            "-ldl", "-o", WSL_BINARY]
            compile_cmd = wsl_argv(linux_bounded(compile_args, COMPILE_WORKER_S, COMPILE_KILL_GRACE_S))
            comp = run_owned("compile", compile_cmd, COMPILE_OUTER_S, MAX_CAPTURE["compile"])
            comp = save_command_logs(run_dir, 3, comp)
            results.append(comp)
            if comp["returncode"] != 0 or comp["outer_timeout"] or comp["stream_overflow"]:
                failure = "COMPILE_FAILED_OR_BOUNDED_STOP"

    if failure is None and ns.phase == "query":
        query_cmd = wsl_argv(linux_bounded([WSL_BINARY], QUERY_WORKER_S, QUERY_KILL_GRACE_S))
        q = run_owned("query", query_cmd, QUERY_OUTER_S, MAX_CAPTURE["query"])
        q = save_command_logs(run_dir, 3, q)
        results.append(q)
        if q["outer_timeout"] or q["stream_overflow"]:
            failure = "QUERY_BOUNDED_STOP"
        else:
            try:
                raw = Path(q["stdout_path"]).read_bytes()
                if len(raw) > 128 * 1024:
                    raise ValueError("query JSON exceeded 128 KiB contract")
                parsed = json.loads(raw.decode("utf-8"))
                expected_status = {0: "QUERY_COMPLETE", 1: "QUERY_ERROR", 2: "NOT_CHECKED"}.get(q["returncode"])
                if expected_status is None or parsed.get("status") != expected_status:
                    raise ValueError("exit status and JSON status disagree")
                if parsed.get("scope") != "CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY" or parsed.get("p2p_claim") != "UNPROVEN":
                    raise ValueError("query output scope/P2P label mismatch")
                query_status = parsed.get("status")
            except Exception as e:
                failure = "QUERY_OUTPUT_CONTRACT_FAILED: " + str(e)

    # Record post-run input/library/compiler identity even after a command failure.
    post_targets = [WSL_SOURCE, WSL_HEADER + "/cuda.h", WSL_HEADER + "/cudaTypedefs.h", COMPILER, LIBRARY]
    if (ROOT / "out" / "cuda_driver_capability_query").is_file():
        post_targets.append(WSL_BINARY)
    post_cmd = wsl_argv(linux_bounded([HASH_TOOL, *post_targets], 5, 2))
    post = run_owned("pins_after", post_cmd, 12, MAX_CAPTURE["small"])
    post = save_command_logs(run_dir, 4, post)
    results.append(post)
    if post["returncode"] != 0 or post["outer_timeout"] or post["stream_overflow"]:
        failure = failure or "POST_PIN_CHECK_FAILED"
    elif before_map is not None:
        try:
            after_raw = Path(post["stdout_path"]).read_text(encoding="utf-8", errors="strict")
            after_map = parse_sha256sum(after_raw)
            for path in (WSL_SOURCE, WSL_HEADER + "/cuda.h", WSL_HEADER + "/cudaTypedefs.h", COMPILER, LIBRARY):
                if after_map.get(path) != before_map.get(path):
                    raise ValueError(f"before/after pin changed for {path}")
            if ns.phase == "query" and after_map.get(WSL_BINARY) != before_map.get(WSL_BINARY):
                raise ValueError("query executable changed during query phase")
            if ns.phase == "compile" and post_targets[-1] == WSL_BINARY:
                results[-1]["compiled_binary_sha256"] = after_map.get(WSL_BINARY)
        except Exception as e:
            failure = failure or "POST_PIN_MISMATCH: " + str(e)

    receipt = {"schema": "cuda-driver-query-execution-receipt-v1", "phase": ns.phase,
               "admission": {k: v for k, v in admission.items() if k != "payload"},
               "admitted_pins": admission["payload"], "source_and_header_expected_pins": EXPECTED,
               "compiler_path": COMPILER, "compiler_version_stdout": compiler_version,
               "controller_path": str(Path(__file__).resolve()),
               "controller_sha256": sha256_file(Path(__file__).resolve()),
               "wsl_client_path": WSL, "wsl_client_sha256": WSL_SHA256,
               "runtime_library_path": LIBRARY, "wsl_distro": DISTRO,
               "worker_bounds_seconds": {"compile": COMPILE_WORKER_S, "compile_kill_grace": COMPILE_KILL_GRACE_S,
                                         "query": QUERY_WORKER_S, "query_kill_grace": QUERY_KILL_GRACE_S},
               "outer_wsl_client_bounds_seconds": {"compile": COMPILE_OUTER_S, "query": QUERY_OUTER_S},
               "results": results, "query_status": query_status, "failure": failure,
               "receipt_written_utc": utc_now(), "controller_pid": os.getpid()}
    write_new(receipt_path, (json.dumps(receipt, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))
    print(json.dumps({"phase": ns.phase, "status": "RECORDED" if failure is None else "STOPPED", "failure": failure,
                      "receipt": str(receipt_path), "run_dir": str(run_dir)}, ensure_ascii=True))
    return 0 if failure is None else 1

if __name__ == "__main__":
    raise SystemExit(main())
