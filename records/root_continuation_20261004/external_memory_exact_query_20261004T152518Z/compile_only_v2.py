"""Corrected compile-only launcher with separate direct cl.exe and link.exe calls."""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
ATTEMPT = BASE / "attempt_004"
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
VS_ROOT = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community")
TOOL_ROOT = VS_ROOT / "VC/Tools/MSVC/14.51.36231"
VCVARS = VS_ROOT / "VC/Auxiliary/Build/vcvars64.bat"
CL = TOOL_ROOT / "bin/Hostx64/x64/cl.exe"
LINK = TOOL_ROOT / "bin/Hostx64/x64/link.exe"
CMD = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/cmd.exe"
SDK = Path(r"E:\the_harness\records\build_vulkan_real\toolchain\sdk")
INCLUDE = SDK / "Include"
CORE_HEADER = INCLUDE / "vulkan/vulkan_core.h"
MAIN_HEADER = INCLUDE / "vulkan/vulkan.h"
LIBDIR = SDK / "Lib"
VULKAN_LIB = LIBDIR / "vulkan-1.lib"
SOURCE = BASE / "external_memory_query.cpp"
OBJ = ATTEMPT / "external_memory_query.obj"
EXE = ATTEMPT / "external_memory_query.exe"
TIMEOUT_SECONDS = 60.0
CAPTURE_LIMIT = 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def pipe_reader(pipe, path, state):
    saved = bytearray()
    total = 0
    try:
        while True:
            chunk = pipe.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if len(saved) < CAPTURE_LIMIT:
                saved.extend(chunk[:CAPTURE_LIMIT - len(saved)])
    except Exception as exc:
        state["read_error"] = type(exc).__name__
    try:
        path.write_bytes(saved)
    except Exception as exc:
        state["write_error"] = type(exc).__name__
    state.update(captured_bytes=len(saved), observed_bytes=total, truncated=total > CAPTURE_LIMIT)


def run_tool(command, cwd, env, stdout_path, stderr_path):
    out_state, err_state = {}, {}
    started = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                            creationflags=CREATE_NO_WINDOW, close_fds=True)
    pid = proc.pid
    out_thread = threading.Thread(target=pipe_reader, args=(proc.stdout, stdout_path, out_state), daemon=True)
    err_thread = threading.Thread(target=pipe_reader, args=(proc.stderr, stderr_path, err_state), daemon=True)
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
    return {
        "pid": pid, "return_code": proc.returncode, "process_present_after_wait": proc.poll() is None,
        "timed_out": timed_out, "drain_failed": drain_failed,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "stdout": {"path": stdout_path.name, **out_state, "sha256": digest(stdout_path) if stdout_path.is_file() else None},
        "stderr": {"path": stderr_path.name, **err_state, "sha256": digest(stderr_path) if stderr_path.is_file() else None},
        "streams_drained": not out_thread.is_alive() and not err_thread.is_alive(),
    }


def main():
    ATTEMPT.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" or Path(os.sys.executable).resolve() != PYTHON.resolve():
        print("NOT_CHECKED: expected pinned Python 3.10 controller")
        return 2
    if any(ATTEMPT.iterdir()):
        print("NOT_CHECKED: refusing to overwrite attempt_003 artifacts")
        return 2
    inputs = {"controller_python": PYTHON, "vcvars64": VCVARS, "compiler": CL, "linker": LINK,
              "source": SOURCE, "main_header": MAIN_HEADER, "core_header": CORE_HEADER, "vulkan_library": VULKAN_LIB,
              "compile_launcher": Path(__file__)}
    before = {name: digest(path) for name, path in inputs.items()}
    bootstrap_command = f'"{CMD}" /d /s /c ""{VCVARS}" x64 >nul && set"'
    compile_command = [str(CL), "/nologo", "/std:c++17", "/EHsc", "/W4", f"/I{INCLUDE}", "/c", str(SOURCE), f"/Fo{OBJ}"]
    link_command = [str(LINK), "/nologo", str(OBJ), "vulkan-1.lib", f"/LIBPATH:{LIBDIR}", f"/OUT:{EXE}"]
    manifest = {
        "scope": "compile and link only; do not run the produced query until separate root admission",
        "environment_bootstrap_command_line": bootstrap_command,
        "compiler_command": compile_command, "linker_command": link_command,
        "cwd": str(ATTEMPT), "timeout_seconds_each_tool": TIMEOUT_SECONDS,
        "capture_limit_per_stream_bytes": CAPTURE_LIMIT,
        "input_paths": {name: str(path) for name, path in inputs.items()}, "input_hashes_before": before,
        "sdk_path": str(SDK), "sdk_provenance": "existing copy-only extracted SDK under build_vulkan_real/toolchain",
        "output_obj": str(OBJ), "output_exe": str(EXE), "runtime_status": "NOT_RUN",
    }
    write_json(ATTEMPT / "compile_manifest.json", manifest)

    setup_started = time.monotonic()
    bootstrap = subprocess.Popen(bootstrap_command, executable=str(CMD), cwd=str(ATTEMPT), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                 creationflags=CREATE_NO_WINDOW, close_fds=True)
    bootstrap_pid = bootstrap.pid
    try:
        env_bytes, setup_error = bootstrap.communicate(timeout=TIMEOUT_SECONDS)
        setup_timeout = False
    except subprocess.TimeoutExpired:
        bootstrap.kill()
        try:
            env_bytes, setup_error = bootstrap.communicate(timeout=8.0)
            setup_drain_failed = False
        except subprocess.TimeoutExpired:
            env_bytes, setup_error = b"", b""
            setup_drain_failed = True
        setup_timeout = True
    setup_elapsed = time.monotonic() - setup_started
    (ATTEMPT / "bootstrap.stderr.log").write_bytes(setup_error[:CAPTURE_LIMIT])
    setup_info = {"pid": bootstrap_pid, "return_code": bootstrap.returncode,
                  "process_present_after_wait": bootstrap.poll() is None,
                  "timed_out": setup_timeout, "elapsed_seconds": round(setup_elapsed, 6),
                  "captured_stdout_bytes": len(env_bytes), "stderr_bytes": min(len(setup_error), CAPTURE_LIMIT),
                  "stderr_truncated": len(setup_error) > CAPTURE_LIMIT}
    if setup_timeout or bootstrap.returncode != 0 or len(env_bytes) > CAPTURE_LIMIT:
        write_json(ATTEMPT / "compile_receipt.json", {
            "compile_status": "TOOLCHAIN_ENVIRONMENT_FAIL", "runtime_status": "NOT_RUN",
            "bootstrap": setup_info, "compile_executed": False,
            "input_hashes_before": before,
            "input_hashes_after": {name: digest(path) for name, path in inputs.items()},
        })
        print(json.dumps({"compile_status": "TOOLCHAIN_ENVIRONMENT_FAIL", "bootstrap_exit": bootstrap.returncode}))
        return 1
    env = {}
    for line in env_bytes.decode("mbcs", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key and not key.startswith("="):
                env[key] = value
    env_casefold = {key.upper(): value for key, value in env.items()}
    required_env_presence = {name: bool(env_casefold.get(name)) for name in ("PATH", "INCLUDE", "LIB")}
    if not all(required_env_presence.values()):
        write_json(ATTEMPT / "compile_receipt.json", {"compile_status": "TOOLCHAIN_ENVIRONMENT_FAIL", "runtime_status": "NOT_RUN", "bootstrap": setup_info, "compile_executed": False, "reason": "MSVC bootstrap omitted required environment fields", "required_environment_fields_present": required_env_presence, "environment_variable_names": sorted(env_casefold)})
        print(json.dumps({"compile_status": "TOOLCHAIN_ENVIRONMENT_FAIL", "required_environment_fields_present": required_env_presence}))
        return 1

    compile_result = run_tool(compile_command, ATTEMPT, env, ATTEMPT / "cl.stdout.log", ATTEMPT / "cl.stderr.log")
    if compile_result["timed_out"] or compile_result["drain_failed"] or compile_result["return_code"] != 0 or not compile_result["streams_drained"]:
        after = {name: digest(path) for name, path in inputs.items()}
        write_json(ATTEMPT / "compile_receipt.json", {"compile_status": "COMPILE_FAIL" if not compile_result["timed_out"] else "TIMEOUT", "runtime_status": "NOT_RUN", "bootstrap": setup_info, "compile": compile_result, "input_hashes_before": before, "input_hashes_after": after, "input_hashes_unchanged": before == after, "link_executed": False})
        print(json.dumps({"compile_status": "COMPILE_FAIL", "cl_exit": compile_result["return_code"], "timed_out": compile_result["timed_out"]}))
        return 1

    link_result = run_tool(link_command, ATTEMPT, env, ATTEMPT / "link.stdout.log", ATTEMPT / "link.stderr.log")
    after = {name: digest(path) for name, path in inputs.items()}
    success = (not link_result["timed_out"] and not link_result["drain_failed"] and link_result["return_code"] == 0
               and link_result["streams_drained"] and before == after and EXE.is_file())
    receipt = {
        "compile_status": "COMPILE_PASS" if success else ("TIMEOUT" if link_result["timed_out"] else "LINK_FAIL"),
        "runtime_status": "NOT_RUN", "bootstrap": setup_info, "compile": compile_result, "link": link_result,
        "input_hashes_before": before, "input_hashes_after": after, "input_hashes_unchanged": before == after,
        "output_obj": str(OBJ) if OBJ.is_file() else None,
        "output_obj_bytes": OBJ.stat().st_size if OBJ.is_file() else None,
        "output_executable": str(EXE) if EXE.is_file() else None,
        "output_executable_bytes": EXE.stat().st_size if EXE.is_file() else None,
        "output_executable_sha256": digest(EXE) if EXE.is_file() else None,
        "native_execution_performed": False,
    }
    write_json(ATTEMPT / "compile_receipt.json", receipt)
    print(json.dumps({"compile_status": receipt["compile_status"], "cl_exit": compile_result["return_code"],
                      "link_exit": link_result["return_code"], "exe_sha256": receipt["output_executable_sha256"]}))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
