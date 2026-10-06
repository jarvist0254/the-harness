"""Bounded, compile-only MSVC launcher for external_memory_query.cpp."""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
VS_ROOT = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community")
VCVARS = VS_ROOT / "VC/Auxiliary/Build/vcvars64.bat"
CL = VS_ROOT / "VC/Tools/MSVC/14.51.36231/bin/Hostx64/x64/cl.exe"
SDK = Path(r"E:\the_harness\records\build_vulkan_real\toolchain\sdk")
INCLUDE = SDK / "Include"
CORE_HEADER = INCLUDE / "vulkan/vulkan_core.h"
LIBDIR = SDK / "Lib"
VULKAN_LIB = LIBDIR / "vulkan-1.lib"
SOURCE = BASE / "external_memory_query.cpp"
EXE = BASE / "external_memory_query.exe"
TIMEOUT_SECONDS = 60.0
CAPTURE_LIMIT = 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def reader(pipe, path, state):
    captured = bytearray()
    observed = 0
    try:
        while True:
            block = pipe.read(65536)
            if not block:
                break
            observed += len(block)
            if len(captured) < CAPTURE_LIMIT:
                captured.extend(block[:CAPTURE_LIMIT - len(captured)])
    except Exception as exc:
        state["read_error"] = type(exc).__name__
    try:
        path.write_bytes(captured)
    except Exception as exc:
        state["write_error"] = type(exc).__name__
    state.update(captured_bytes=len(captured), observed_bytes=observed, truncated=observed > CAPTURE_LIMIT)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    if os.name != "nt" or Path(os.sys.executable).resolve() != PYTHON.resolve():
        print("NOT_CHECKED: unexpected compile-controller Python", file=os.sys.stderr)
        return 2
    if EXE.exists():
        print("NOT_CHECKED: refusing to overwrite an existing output executable", file=os.sys.stderr)
        return 2
    inputs = {"controller_python": PYTHON, "vcvars64": VCVARS, "compiler": CL, "source": SOURCE,
              "core_header": CORE_HEADER, "vulkan_library": VULKAN_LIB}
    before = {name: digest(path) for name, path in inputs.items()}
    bootstrap_command = f'call "{VCVARS}" x64 >nul && set'
    compiler_args = [str(CL), "/nologo", "/std:c++17", "/EHsc", "/W4",
                     f"/I{INCLUDE}", str(SOURCE), "/link", f"/LIBPATH:{LIBDIR}",
                     "vulkan-1.lib", f"/OUT:{EXE}"]
    record = {
        "scope": "compile only; native executable must not be run before separate root admission",
        "environment_bootstrap_command": ["cmd.exe", "/d", "/c", bootstrap_command],
        "compiler_command": compiler_args,
        "cwd": str(BASE), "timeout_seconds": TIMEOUT_SECONDS, "capture_limit_per_stream_bytes": CAPTURE_LIMIT,
        "input_paths": {name: str(path) for name, path in inputs.items()}, "input_hashes_before": before,
        "compiler": "MSVC 14.51.36231 x64 from existing VS 18 Community install",
        "sdk": str(SDK), "sdk_source": "existing copy-only extracted LunarG SDK recorded under build_vulkan_real/toolchain",
        "link_libraries": [str(VULKAN_LIB)],
        "compile_target": str(EXE),
        "runtime_status": "NOT_RUN_BY_THIS_SCRIPT",
    }
    write_json(BASE / "compile_manifest.json", record)
    stdout_path, stderr_path = BASE / "compile.stdout.log", BASE / "compile.stderr.log"
    stdout_state, stderr_state = {}, {}
    bootstrap_started = time.monotonic()
    bootstrap = subprocess.Popen(["cmd.exe", "/d", "/c", bootstrap_command], cwd=str(BASE),
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 shell=False, creationflags=CREATE_NO_WINDOW, close_fds=True)
    bootstrap_pid = bootstrap.pid
    try:
        environment_output, bootstrap_error = bootstrap.communicate(timeout=TIMEOUT_SECONDS)
        bootstrap_timed_out = False
    except subprocess.TimeoutExpired:
        bootstrap.kill()
        try:
            environment_output, bootstrap_error = bootstrap.communicate(timeout=8.0)
            bootstrap_drain_failed = False
        except subprocess.TimeoutExpired:
            environment_output, bootstrap_error = b"", b""
            bootstrap_drain_failed = True
        bootstrap_timed_out = True
    bootstrap_elapsed = time.monotonic() - bootstrap_started
    if bootstrap_error:
        (BASE / "bootstrap.stderr.log").write_bytes(bootstrap_error[:CAPTURE_LIMIT])
    if bootstrap_timed_out or bootstrap.returncode != 0 or len(environment_output) > CAPTURE_LIMIT:
        failure = {
            "compile_status": "TIMEOUT" if bootstrap_timed_out else "TOOLCHAIN_ENVIRONMENT_FAIL",
            "runtime_status": "NOT_RUN", "bootstrap_pid": bootstrap_pid,
            "bootstrap_return_code": bootstrap.returncode, "bootstrap_timed_out": bootstrap_timed_out,
            "bootstrap_drain_failed": locals().get("bootstrap_drain_failed", False),
            "bootstrap_elapsed_seconds": round(bootstrap_elapsed, 6),
            "bootstrap_output_bytes": len(environment_output), "compile_executed": False,
            "input_hashes_before": before, "input_hashes_after": {name: digest(path) for name, path in inputs.items()},
        }
        write_json(BASE / "compile_receipt.json", failure)
        return 1
    build_env = {}
    for raw_line in environment_output.decode("mbcs", errors="replace").splitlines():
        if "=" in raw_line:
            key, value = raw_line.split("=", 1)
            if key and not key.startswith("="):
                build_env[key] = value
    if not build_env.get("PATH") or not build_env.get("INCLUDE") or not build_env.get("LIB"):
        write_json(BASE / "compile_receipt.json", {"compile_status": "TOOLCHAIN_ENVIRONMENT_FAIL", "runtime_status": "NOT_RUN", "compile_executed": False, "reason": "MSVC environment output lacked PATH/INCLUDE/LIB"})
        return 1
    started = time.monotonic()
    proc = subprocess.Popen(compiler_args, cwd=str(BASE), env=build_env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                            creationflags=CREATE_NO_WINDOW, close_fds=True)
    pid = proc.pid
    out_thread = threading.Thread(target=reader, args=(proc.stdout, stdout_path, stdout_state), daemon=True)
    err_thread = threading.Thread(target=reader, args=(proc.stderr, stderr_path, stderr_state), daemon=True)
    out_thread.start(); err_thread.start()
    timed_out = drain_failed = False
    try:
        proc.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        try:
            proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            drain_failed = True
    out_thread.join(timeout=8.0); err_thread.join(timeout=8.0)
    after = {name: digest(path) for name, path in inputs.items()}
    elapsed = time.monotonic() - started
    success = (not timed_out and not drain_failed and proc.returncode == 0 and EXE.is_file()
               and before == after and not out_thread.is_alive() and not err_thread.is_alive()
               and not stdout_state.get("write_error") and not stderr_state.get("write_error")
               and not stdout_state.get("truncated") and not stderr_state.get("truncated"))
    receipt = {
        "compile_status": "COMPILE_PASS" if success else ("TIMEOUT" if timed_out else "COMPILE_FAIL"),
        "runtime_status": "NOT_RUN", "bootstrap_pid": bootstrap_pid,
        "bootstrap_return_code": bootstrap.returncode, "bootstrap_elapsed_seconds": round(bootstrap_elapsed, 6),
        "bootstrap_output_bytes": len(environment_output), "pid": pid, "return_code": proc.returncode,
        "process_present_after_wait": proc.poll() is None, "timed_out": timed_out,
        "drain_failed": drain_failed, "elapsed_seconds": round(elapsed, 6),
        "input_hashes_before": before, "input_hashes_after": after,
        "input_hashes_unchanged": before == after,
        "stdout": {"path": stdout_path.name, **stdout_state, "sha256": digest(stdout_path) if stdout_path.is_file() else None},
        "stderr": {"path": stderr_path.name, **stderr_state, "sha256": digest(stderr_path) if stderr_path.is_file() else None},
        "output_executable": str(EXE) if EXE.is_file() else None,
        "output_executable_sha256": digest(EXE) if EXE.is_file() else None,
        "output_executable_bytes": EXE.stat().st_size if EXE.is_file() else None,
        "native_execution_performed": False,
    }
    write_json(BASE / "compile_receipt.json", receipt)
    print(json.dumps({"compile_status": receipt["compile_status"], "exit": proc.returncode,
                      "elapsed_seconds": receipt["elapsed_seconds"], "exe_sha256": receipt["output_executable_sha256"]}))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
