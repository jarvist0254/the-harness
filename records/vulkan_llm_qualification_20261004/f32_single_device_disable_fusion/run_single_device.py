"""Bounded single-device diagnostic for the already-admitted F32/KV-F32 fixture."""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
SOURCE = Path(r"E:\the_harness\records\factory_runs\20261004\coherent_repair_kv_20261004T130000Z\grok_kv_f32\llama_logits_kv_f32.cpp")
EXE = Path(r"E:\the_harness\records\vulkan_llm_qualification_20261004\fixture_kv_f32\llama_logits_kv_f32.exe")
MODEL = Path(r"E:\the_harness\records\models\qwen3_06b_f32_derived\Qwen3-0.6B-Q8_0-dequant-F32.gguf")
WORKING_DIRECTORY = Path(r"E:\the_harness\records\build_vulkan_real\build\bin")
EXPECTED = {
    "source": "2aff3925329a8ca6ca4834f665a8ed07acb1d3e341f73908dfecb3989057c371",
    "exe": "d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4",
    "model": "bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80",
    "model_bytes": 2390150816,
    "python": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
}
ENV_DELTA = {"GGML_VK_DISABLE_F16": "1", "GGML_VK_DISABLE_FUSION": "1"}
DEVICE_MAP = {"NV": "Vulkan0", "AMD": "Vulkan1"}
TIMEOUT_SECONDS = 60.0
CAPTURE_LIMIT = 2 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def global_memory_snapshot():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        return {"status": "NOT_CHECKED", "winerror": ctypes.get_last_error()}
    return {
        "status": "MEASURED",
        "memory_load_percent": int(state.dwMemoryLoad),
        "total_physical_bytes": int(state.ullTotalPhys),
        "available_physical_bytes": int(state.ullAvailPhys),
        "total_pagefile_bytes": int(state.ullTotalPageFile),
        "available_pagefile_bytes": int(state.ullAvailPageFile),
        "total_virtual_bytes": int(state.ullTotalVirtual),
        "available_virtual_bytes": int(state.ullAvailVirtual),
    }


def reader(pipe, path, state):
    data = bytearray()
    observed = 0
    try:
        while True:
            chunk = pipe.read(65536)
            if not chunk:
                break
            observed += len(chunk)
            if len(data) < CAPTURE_LIMIT:
                data.extend(chunk[:CAPTURE_LIMIT - len(data)])
    except Exception as exc:
        state["reader_error"] = type(exc).__name__
    try:
        path.write_bytes(bytes(data))
    except Exception as exc:
        state["write_error"] = type(exc).__name__
    state["captured_bytes"] = len(data)
    state["observed_bytes"] = observed
    state["truncated"] = observed > CAPTURE_LIMIT


def parse_runtime_json(stdout_path):
    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict) and "status" in obj and "devices" in obj and "fail_count" in obj:
            return obj
    return None


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in DEVICE_MAP:
        print("usage: run_single_device.py NV|AMD", file=sys.stderr)
        return 2
    if os.name != "nt" or sys.version_info[:2] != (3, 10) or Path(sys.executable).resolve() != PYTHON.resolve():
        print("NOT_CHECKED: unexpected runtime", file=sys.stderr)
        return 2
    label = sys.argv[1]
    device = DEVICE_MAP[label]
    case_dir = BASE / label
    if not case_dir.is_dir() or any(case_dir.iterdir()):
        print("NOT_CHECKED: output directory missing or not fresh", file=sys.stderr)
        return 2
    inputs = {"source": SOURCE, "exe": EXE, "model": MODEL, "python": PYTHON, "runner": Path(__file__)}
    hashes_before = {name: sha256(path) for name, path in inputs.items()}
    expected_current = {key: EXPECTED[key] for key in ("source", "exe", "model", "python")}
    actual_current = {key: hashes_before[key] for key in expected_current}
    if actual_current != expected_current or MODEL.stat().st_size != EXPECTED["model_bytes"]:
        write_json(case_dir / "static_gate_failure.json", {"expected": expected_current, "actual": actual_current, "model_bytes": MODEL.stat().st_size})
        return 2
    backend_flag_keys = ("GGML_VK_DISABLE_F16", "GGML_VK_DISABLE_FUSION", "GGML_VK_DISABLE_COOPMAT", "GGML_VK_DISABLE_COOPMAT2")
    parent_env_before = {key: os.environ.get(key) for key in backend_flag_keys}
    if parent_env_before["GGML_VK_DISABLE_COOPMAT"] is not None or parent_env_before["GGML_VK_DISABLE_COOPMAT2"] is not None:
        write_json(case_dir / "static_gate_failure.json", {"reason": "unexpected_cooperative_matrix_parent_environment", "flag_state": {key: ("unset" if val is None else "set") for key, val in parent_env_before.items()}})
        return 2
    static_manifest = {
        "experiment": "single-device derived-F32 full-model CPU-reference diagnostic; no code change",
        "source_path": str(SOURCE),
        "source_sha256": hashes_before["source"],
        "binary_path": str(EXE),
        "binary_sha256": hashes_before["exe"],
        "model_path": str(MODEL),
        "model_sha256": hashes_before["model"],
        "model_bytes": MODEL.stat().st_size,
        "pinned_commit": "0faee5004297c3bcfa40b7bf11750127b8c1fd7d",
        "device_order": [device],
        "tokens": list(range(16)),
        "requested_n_ctx": 128,
        "actual_n_ctx": 256,
        "n_batch": 32,
        "n_ubatch": 32,
        "n_threads": 4,
        "atol": 0.01,
        "rtol": 0.01,
        "kv_requested": "f32",
        "kv_type_k": "f32",
        "kv_type_v": "f32",
        "inject_corruption": False,
        "flash_attn": "disabled",
        "child_environment_delta": ENV_DELTA,
        "parent_backend_flag_state": {key: ("unset" if value is None else "set") for key, value in parent_env_before.items()},
        "working_directory": str(WORKING_DIRECTORY),
        "args": ["--model", str(MODEL), "--expected-sha256", EXPECTED["model"], "--devices", device, "--kv-f32"],
        "input_hashes_before": hashes_before,
        "authorization": "ROOT_ADMITTED_SINGLE_DEVICE_BASELINES_WITH_F16_AND_FUSION_DISABLED",
    }
    static_canonical = json.dumps(static_manifest, sort_keys=True, separators=(",", ":"))
    static_hash = hashlib.sha256(static_canonical.encode("utf-8")).hexdigest()
    composite = {
        "static_manifest_sha256": static_hash,
        "cpp_workload_sha256": "runtime-populated",
        "selected_device": device,
        "environment_delta": ENV_DELTA,
        "source_sha256": hashes_before["source"],
        "binary_sha256": hashes_before["exe"],
        "model_sha256": hashes_before["model"],
    }
    composite_canonical = json.dumps(composite, sort_keys=True, separators=(",", ":"))
    composite_hash = hashlib.sha256(composite_canonical.encode("utf-8")).hexdigest()
    write_json(case_dir / "static_manifest.json", static_manifest)
    write_json(case_dir / "root_admission_snapshot.json", {
        "admission": "Root chat admission; bounded single-device F32/KV-F32 diagnostics",
        "source_sha256": EXPECTED["source"],
        "binary_sha256": EXPECTED["exe"],
        "model_sha256": EXPECTED["model"],
        "model_bytes": EXPECTED["model_bytes"],
        "device": device,
        "runtime_env_delta": ENV_DELTA,
        "tokens": list(range(16)),
        "requested_context": 128,
        "actual_context": 256,
        "batch": 32,
        "ubatch": 32,
        "threads": 4,
        "atol": 0.01,
        "rtol": 0.01,
        "outer_timeout_seconds": 60,
        "stop_if": ["timeout", "native API uncertainty", "less than 29/29 layer offload", "wrong device/KV types", "input hash change"],
        "numeric_parity_failure": "valid diagnostic; continue to the other independent single-device baseline only if execution gates and cleanup are sound",
        "reverse_or_corruption_controls": "not admitted in this task"
    })

    command = [str(EXE), "--model", str(MODEL), "--expected-sha256", EXPECTED["model"], "--devices", device, "--kv-f32"]
    child_env = os.environ.copy()
    child_env.update(ENV_DELTA)
    memory_before = global_memory_snapshot()
    stdout_path = case_dir / "stdout.raw.log"
    stderr_path = case_dir / "stderr.raw.log"
    stdout_state, stderr_state = {}, {}
    started = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(WORKING_DIRECTORY), env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, creationflags=CREATE_NO_WINDOW, close_fds=True)
    pid = proc.pid
    out_thread = threading.Thread(target=reader, args=(proc.stdout, stdout_path, stdout_state), daemon=True)
    err_thread = threading.Thread(target=reader, args=(proc.stderr, stderr_path, stderr_state), daemon=True)
    out_thread.start()
    err_thread.start()
    timed_out = False
    cleanup_wait_failed = False
    try:
        proc.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()  # Uses only this owned Popen process handle.
        try:
            proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            cleanup_wait_failed = True
    out_thread.join(timeout=8.0)
    err_thread.join(timeout=8.0)
    elapsed = time.monotonic() - started
    memory_after = global_memory_snapshot()
    parent_env_after = {key: os.environ.get(key) for key in backend_flag_keys}
    hashes_after = {name: sha256(path) for name, path in inputs.items()}
    runtime_json = parse_runtime_json(stdout_path) if stdout_path.is_file() else None
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    offload_lines = [line.strip() for line in stderr_text.splitlines() if "offloaded " in line and "layers to GPU" in line]
    model_buffer_lines = [line.strip() for line in stderr_text.splitlines() if "model buffer size" in line]
    kv_lines = [line.strip() for line in stderr_text.splitlines() if "KV buffer size" in line or "K (f32)" in line or "V (f32)" in line]
    layer_assignment_lines = [line.strip() for line in stderr_text.splitlines() if "load_tensors: layer " in line and "assigned to device " + device in line]
    device_free_lines = [line.strip() for line in stderr_text.splitlines() if "using device Vulkan" in line and "free" in line]
    expected_device_detail = None
    if isinstance(runtime_json, dict):
        expected_device_detail = next((d for d in runtime_json.get("device_details", []) if d.get("name") == device), None)
    requested = runtime_json.get("requested", {}) if isinstance(runtime_json, dict) else {}
    selected_model_buffer = any((device + " model buffer size") in line for line in model_buffer_lines)
    selected_kv_buffer = any((device + " KV buffer size") in line for line in kv_lines)
    kv_f32_log_reported = any("K (f32):" in line and "V (f32):" in line for line in kv_lines)
    offload_29 = "load_tensors: offloaded 29/29 layers to GPU" in stderr_text
    runtime_json_ok = bool(
        runtime_json
        and runtime_json.get("model") == str(MODEL)
        and runtime_json.get("sha256") == EXPECTED["model"]
        and runtime_json.get("file_size") == EXPECTED["model_bytes"]
        and runtime_json.get("devices") == [device]
        and runtime_json.get("device_population") == 1
        and runtime_json.get("vendor_population") == "SINGLE_VENDOR"
        and runtime_json.get("n_layer") == 28
        and runtime_json.get("n_vocab") == 151936
        and runtime_json.get("tokens") == list(range(16))
        and runtime_json.get("n_ctx_actual") == 256
        and runtime_json.get("n_batch_actual") == 32
        and runtime_json.get("n_ubatch_actual") == 32
        and runtime_json.get("kv_requested") == "f32"
        and runtime_json.get("kv_actual_k") == "f32"
        and runtime_json.get("kv_actual_v") == "f32"
        and runtime_json.get("all_finite_cpu") is True
        and runtime_json.get("all_finite_gpu") is True
        and runtime_json.get("status") in ("NUMERIC_PARITY_PASS", "NUMERIC_PARITY_FAIL")
        and requested.get("n_ctx") == 128
        and requested.get("n_batch") == 32
        and requested.get("n_ubatch") == 32
        and requested.get("n_threads") == 4
        and requested.get("kv") == "f32"
        and requested.get("flash_attn") == "disabled"
        and expected_device_detail is not None
        and expected_device_detail.get("backend") == "Vulkan"
        and expected_device_detail.get("description") == ("NVIDIA GeForce RTX 5070 Ti" if label == "NV" else "AMD Radeon(TM) Graphics")
    )
    no_truncation = not stdout_state.get("truncated") and not stderr_state.get("truncated")
    hygiene_ok = (
        not timed_out and not cleanup_wait_failed and proc.returncode in (0, 1)
        and not out_thread.is_alive() and not err_thread.is_alive()
        and stdout_state.get("write_error") is None and stderr_state.get("write_error") is None
        and no_truncation and hashes_before == hashes_after
        and parent_env_before == parent_env_after
    )
    layer_ownership_ok = len(layer_assignment_lines) == 29
    execution_gate = hygiene_ok and runtime_json_ok and offload_29 and selected_model_buffer and selected_kv_buffer and kv_f32_log_reported and layer_ownership_ok
    numeric_status = runtime_json.get("status") if runtime_json else None
    composite["cpp_workload_sha256"] = runtime_json.get("workload_sha256") if runtime_json else None
    composite["runtime_status"] = numeric_status
    composite_canonical = json.dumps(composite, sort_keys=True, separators=(",", ":"))
    composite_hash_actual = hashlib.sha256(composite_canonical.encode("utf-8")).hexdigest()
    receipt = {
        "run_status": "EXECUTION_GATES_MET" if execution_gate else ("TIMEOUT" if timed_out else "EXECUTION_GATE_FAILED"),
        "numeric_status": numeric_status,
        "runtime_exit_code": proc.returncode,
        "error": runtime_json.get("error") if runtime_json else None,
        "command": command,
        "cwd": str(WORKING_DIRECTORY),
        "child_environment_delta": ENV_DELTA,
        "parent_environment_target_keys_unchanged": parent_env_before == parent_env_after,
        "parent_backend_flag_state": {key: ("unset" if value is None else "set") for key, value in parent_env_before.items()},
        "device": device,
        "device_detail": expected_device_detail,
        "timeout_seconds": TIMEOUT_SECONDS,
        "timed_out": timed_out,
        "cleanup_wait_failed": cleanup_wait_failed,
        "pid": pid,
        "process_present_after_wait": proc.poll() is None,
        "elapsed_seconds": round(elapsed, 6),
        "memory_before": memory_before,
        "memory_after": memory_after,
        "input_hashes_before": hashes_before,
        "input_hashes_after": hashes_after,
        "input_hashes_unchanged": hashes_before == hashes_after,
        "stdout": {"path": stdout_path.name, **stdout_state, "sha256": sha256(stdout_path) if stdout_path.is_file() else None},
        "stderr": {"path": stderr_path.name, **stderr_state, "sha256": sha256(stderr_path) if stderr_path.is_file() else None},
        "cpp_workload_sha256": runtime_json.get("workload_sha256") if runtime_json else None,
        "static_manifest_sha256": static_hash,
        "composite_experiment_sha256": composite_hash_actual,
        "runtime_json": runtime_json,
        "offload_lines": offload_lines,
        "offloaded_29_of_29": offload_29,
        "model_buffer_lines": model_buffer_lines,
        "selected_model_buffer_reported": selected_model_buffer,
        "layer_assignment_lines": layer_assignment_lines,
        "selected_device_29_layer_assignments": len(layer_assignment_lines),
        "selected_device_layer_ownership_ok": layer_ownership_ok,
        "kv_buffer_lines": kv_lines,
        "selected_kv_buffer_reported": selected_kv_buffer,
        "kv_f32_log_reported": kv_f32_log_reported,
        "device_free_before_allocation_lines": device_free_lines,
        "post_run_per_device_free_memory": "NOT_CHECKED",
        "execution_gates_met": execution_gate,
        "limitations": ["single-device diagnostic, not mixed-vendor execution", "numeric PASS/FAIL is not production qualification", "model/device memory-free logs are runtime-reported, not physical residency proof", "whole-tree or production admission not established"],
    }
    write_json(case_dir / "composite_experiment.json", {"canonical": composite_canonical, "sha256": composite_hash_actual, "runtime_cpp_workload_sha256": receipt["cpp_workload_sha256"]})
    write_json(case_dir / "run_receipt.json", receipt)
    print(json.dumps({"device": device, "run_status": receipt["run_status"], "numeric_status": numeric_status, "exit": proc.returncode, "execution_gates_met": execution_gate, "elapsed_seconds": receipt["elapsed_seconds"], "composite_sha256": composite_hash_actual}))
    if not execution_gate:
        return 2 if timed_out or cleanup_wait_failed or proc.returncode not in (0, 1) else 1
    return 0 if numeric_status == "NUMERIC_PARITY_PASS" and proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
