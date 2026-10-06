"""One admitted mixed-device Vulkan F32/KV-F32 diagnostic; no source changes."""
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
CASE = BASE / "baseline"
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
SOURCE = Path(r"E:\the_harness\records\factory_runs\20261004\coherent_repair_kv_20261004T130000Z\grok_kv_f32\llama_logits_kv_f32.cpp")
EXE = Path(r"E:\the_harness\records\vulkan_llm_qualification_20261004\fixture_kv_f32\llama_logits_kv_f32.exe")
MODEL = Path(r"E:\the_harness\records\models\qwen3_06b_f32_derived\Qwen3-0.6B-Q8_0-dequant-F32.gguf")
CWD = Path(r"E:\the_harness\records\build_vulkan_real\build\bin")
EXPECTED = {
    "source": "2aff3925329a8ca6ca4834f665a8ed07acb1d3e341f73908dfecb3989057c371",
    "exe": "d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4",
    "model": "bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80",
    "model_bytes": 2390150816,
    "python": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
}
ENV_DELTA = {
    "GGML_VK_DISABLE_F16": "1",
    "GGML_VK_DISABLE_FUSION": "1",
    "GGML_VK_DISABLE_COOPMAT": "1",
    "GGML_VK_DISABLE_COOPMAT2": "1",
}
DEVICES = ["Vulkan0", "Vulkan1"]
TIMEOUT = 60.0
CAPTURE_LIMIT = 2 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def read_pipe(pipe, path, state):
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
        path.write_bytes(data)
    except Exception as exc:
        state["write_error"] = type(exc).__name__
    state.update(captured_bytes=len(data), observed_bytes=observed, truncated=observed > CAPTURE_LIMIT)


def parse_json(path):
    if not path.is_file():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict) and "status" in obj and "devices" in obj and "fail_count" in obj:
            return obj
    return None


def main():
    if len(sys.argv) != 1 or os.name != "nt" or sys.version_info[:2] != (3, 10) or Path(sys.executable).resolve() != PYTHON.resolve():
        print("NOT_CHECKED: expected pinned Windows Python 3.10 controller", file=sys.stderr)
        return 2
    if not CASE.is_dir() or any(CASE.iterdir()):
        print("NOT_CHECKED: expected fresh baseline output directory", file=sys.stderr)
        return 2
    inputs = {"source": SOURCE, "exe": EXE, "model": MODEL, "python": PYTHON, "runner": Path(__file__)}
    before = {key: sha256(path) for key, path in inputs.items()}
    expected = {key: EXPECTED[key] for key in ("source", "exe", "model", "python")}
    if {key: before[key] for key in expected} != expected or MODEL.stat().st_size != EXPECTED["model_bytes"]:
        write_json(CASE / "static_gate_failure.json", {"expected": expected, "actual": before, "model_bytes": MODEL.stat().st_size})
        return 2
    env_keys = tuple(ENV_DELTA) + ("GGML_VK_DISABLE_GRAPH_OPTIMIZE",)
    parent_before = {key: os.environ.get(key) for key in env_keys}
    if any(parent_before.get(key) is not None for key in ENV_DELTA):
        write_json(CASE / "static_gate_failure.json", {"reason": "parent_backend_flags_must_be_unset", "parent_flags": parent_before})
        return 2
    args = [str(EXE), "--model", str(MODEL), "--expected-sha256", EXPECTED["model"], "--devices", ",".join(DEVICES), "--kv-f32"]
    manifest = {
        "experiment": "root-admitted mixed-device F32/KV-F32 diagnostic with cooperative matrices disabled; no source edit",
        "authorization": "ROOT_ADMITTED_MIXED_F32_KV_F32_DISABLE_COOPMAT_AND_COOPMAT2_BASELINE",
        "source_sha256": before["source"], "binary_sha256": before["exe"], "model_sha256": before["model"],
        "python_sha256": before["python"], "model_bytes": MODEL.stat().st_size,
        "pinned_commit": "0faee5004297c3bcfa40b7bf11750127b8c1fd7d",
        "devices": DEVICES, "tokens": list(range(16)), "requested_context": 128, "actual_context": 256,
        "batch": 32, "ubatch": 32, "threads": 4, "atol": 0.01, "rtol": 0.01,
        "kv": "f32", "flash_attn": "disabled", "inject_corruption": False,
        "child_environment_delta": ENV_DELTA,
        "parent_backend_flag_state": {key: ("unset" if value is None else "set") for key, value in parent_before.items()},
        "args": args, "cwd": str(CWD), "timeout_seconds": TIMEOUT,
        "stop_conditions": ["timeout or native API uncertainty", "wrong model/device/KV metadata", "less than 29/29 offload", "input hash change"],
        "conditional_followups": "reverse and comparator control only if this baseline fully passes parity and execution gates",
        "input_hashes_before": before,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_json(CASE / "root_admission_snapshot.json", {
        "admission": manifest["authorization"], "source_sha256": before["source"], "binary_sha256": before["exe"],
        "model_sha256": before["model"], "devices": DEVICES, "environment_delta": ENV_DELTA,
        "parameters": {k: manifest[k] for k in ("tokens", "requested_context", "actual_context", "batch", "ubatch", "threads", "atol", "rtol", "kv", "flash_attn")},
        "deadline_seconds": TIMEOUT, "only_if_baseline_passes": ["reverse order", "comparator logit corruption"],
        "note": "Copied locally from root task authorization; not a cryptographic root signature.",
    })
    write_json(CASE / "static_manifest.json", manifest)
    composite = {"static_manifest_sha256": manifest_hash, "source_sha256": before["source"], "binary_sha256": before["exe"], "model_sha256": before["model"], "environment_delta": ENV_DELTA, "devices": DEVICES, "cpp_workload_sha256": "populated_after_run"}
    out_path, err_path = CASE / "stdout.raw.log", CASE / "stderr.raw.log"
    out_state, err_state = {}, {}
    child_env = os.environ.copy()
    child_env.update(ENV_DELTA)
    started = time.monotonic()
    proc = subprocess.Popen(args, cwd=str(CWD), env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, creationflags=CREATE_NO_WINDOW, close_fds=True)
    pid = proc.pid
    out_thread = threading.Thread(target=read_pipe, args=(proc.stdout, out_path, out_state), daemon=True)
    err_thread = threading.Thread(target=read_pipe, args=(proc.stderr, err_path, err_state), daemon=True)
    out_thread.start(); err_thread.start()
    timed_out = cleanup_wait_failed = False
    try:
        proc.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        try:
            proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            cleanup_wait_failed = True
    out_thread.join(timeout=8.0); err_thread.join(timeout=8.0)
    elapsed = time.monotonic() - started
    after = {key: sha256(path) for key, path in inputs.items()}
    parent_after = {key: os.environ.get(key) for key in env_keys}
    runtime = parse_json(out_path)
    stderr = err_path.read_text(encoding="utf-8", errors="replace") if err_path.is_file() else ""
    offload_lines = [line.strip() for line in stderr.splitlines() if "offloaded " in line and "layers to GPU" in line]
    assignment_lines = [line.strip() for line in stderr.splitlines() if "load_tensors: layer " in line and "assigned to device Vulkan" in line]
    model_lines = [line.strip() for line in stderr.splitlines() if "model buffer size" in line]
    kv_lines = [line.strip() for line in stderr.splitlines() if "KV buffer size" in line or "K (f32):" in line or "V (f32):" in line]
    backend_lines = [line.strip() for line in stderr.splitlines() if "matrix cores:" in line or "ggml_vulkan:" in line and "matrix cores:" in line]
    layers_by_device = {dev: sum(f"assigned to device {dev}" in line for line in assignment_lines) for dev in DEVICES}
    device_details = runtime.get("device_details", []) if isinstance(runtime, dict) else []
    detail_by_name = {item.get("name"): item for item in device_details if isinstance(item, dict)}
    requested = runtime.get("requested", {}) if isinstance(runtime, dict) else {}
    runtime_json_ok = bool(
        runtime and runtime.get("model") == str(MODEL) and runtime.get("sha256") == EXPECTED["model"]
        and runtime.get("file_size") == EXPECTED["model_bytes"] and runtime.get("devices") == DEVICES
        and runtime.get("device_population") == 2 and runtime.get("vendor_population") == "MIXED_VENDOR"
        and runtime.get("n_layer") == 28 and runtime.get("n_vocab") == 151936
        and runtime.get("tokens") == list(range(16)) and runtime.get("n_ctx_actual") == 256
        and runtime.get("n_batch_actual") == 32 and runtime.get("n_ubatch_actual") == 32
        and runtime.get("kv_requested") == "f32" and runtime.get("kv_actual_k") == "f32" and runtime.get("kv_actual_v") == "f32"
        and runtime.get("all_finite_cpu") is True and runtime.get("all_finite_gpu") is True
        and runtime.get("status") in ("NUMERIC_PARITY_PASS", "NUMERIC_PARITY_FAIL")
        and requested.get("n_ctx") == 128 and requested.get("n_batch") == 32 and requested.get("n_ubatch") == 32
        and requested.get("n_threads") == 4 and requested.get("kv") == "f32" and requested.get("flash_attn") == "disabled"
        and detail_by_name.get("Vulkan0", {}).get("description") == "NVIDIA GeForce RTX 5070 Ti"
        and detail_by_name.get("Vulkan1", {}).get("description") == "AMD Radeon(TM) Graphics"
    )
    coopmat_disabled_logs = len([line for line in backend_lines if "matrix cores: none" in line.lower()]) >= 2
    layers_ok = len(assignment_lines) == 29 and all(layers_by_device[d] > 0 for d in DEVICES)
    offload_ok = "load_tensors: offloaded 29/29 layers to GPU" in stderr
    model_buffers_ok = all(any(f"{d} model buffer size" in line for line in model_lines) for d in DEVICES)
    kv_buffers_ok = all(any(f"{d} KV buffer size" in line for line in kv_lines) for d in DEVICES)
    kv_f32_log = any("K (f32):" in line and "V (f32):" in line for line in kv_lines)
    streams_ok = all(state.get("write_error") is None and not state.get("truncated") for state in (out_state, err_state)) and not out_thread.is_alive() and not err_thread.is_alive()
    hygiene_ok = not timed_out and not cleanup_wait_failed and proc.returncode in (0, 1) and streams_ok and before == after and parent_before == parent_after
    gates = hygiene_ok and runtime_json_ok and coopmat_disabled_logs and layers_ok and offload_ok and model_buffers_ok and kv_buffers_ok and kv_f32_log
    workload_hash = runtime.get("workload_sha256") if runtime else None
    composite["cpp_workload_sha256"] = workload_hash
    composite["runtime_status"] = runtime.get("status") if runtime else None
    composite_canonical = json.dumps(composite, sort_keys=True, separators=(",", ":"))
    composite_hash = hashlib.sha256(composite_canonical.encode("utf-8")).hexdigest()
    receipt = {
        "run_status": "EXECUTION_GATES_MET" if gates else ("TIMEOUT" if timed_out else "EXECUTION_GATE_FAILED"),
        "numeric_status": runtime.get("status") if runtime else None, "runtime_exit_code": proc.returncode,
        "error": runtime.get("error") if runtime else None, "command": args, "cwd": str(CWD),
        "child_environment_delta": ENV_DELTA, "parent_environment_target_keys_unchanged": parent_before == parent_after,
        "parent_backend_flag_state": {k: ("unset" if v is None else "set") for k, v in parent_before.items()},
        "devices": DEVICES, "device_details": device_details, "pid": pid, "process_present_after_wait": proc.poll() is None,
        "timeout_seconds": TIMEOUT, "timed_out": timed_out, "cleanup_wait_failed": cleanup_wait_failed,
        "elapsed_seconds": round(elapsed, 6), "input_hashes_before": before, "input_hashes_after": after,
        "input_hashes_unchanged": before == after, "stdout": {"path": out_path.name, **out_state, "sha256": sha256(out_path) if out_path.is_file() else None},
        "stderr": {"path": err_path.name, **err_state, "sha256": sha256(err_path) if err_path.is_file() else None},
        "cpp_workload_sha256": workload_hash, "static_manifest_sha256": manifest_hash, "composite_experiment_sha256": composite_hash,
        "runtime_json": runtime, "offload_lines": offload_lines, "offloaded_29_of_29": offload_ok,
        "layer_assignment_lines": assignment_lines, "layers_by_device": layers_by_device,
        "model_buffer_lines": model_lines, "model_buffers_both_devices_reported": model_buffers_ok,
        "kv_buffer_lines": kv_lines, "kv_buffers_both_devices_reported": kv_buffers_ok,
        "f32_kv_log_reported": kv_f32_log, "backend_matrix_lines": backend_lines,
        "cooperative_matrices_reported_disabled": coopmat_disabled_logs,
        "runtime_json_gate": runtime_json_ok, "execution_gates_met": gates,
        "limitations": ["runtime reported placement is not independent physical residency proof", "no P2P or peer-memory claim", "no capacity or production qualification claim", "only this 0.6B F32/KV-F32 diagnostic"],
    }
    write_json(CASE / "composite_experiment.json", {"canonical": composite_canonical, "sha256": composite_hash, "runtime_cpp_workload_sha256": workload_hash})
    write_json(CASE / "run_receipt.json", receipt)
    print(json.dumps({"run_status": receipt["run_status"], "numeric_status": receipt["numeric_status"], "exit": proc.returncode, "execution_gates_met": gates, "elapsed_seconds": receipt["elapsed_seconds"], "composite_sha256": composite_hash}))
    if not gates:
        return 2 if timed_out or cleanup_wait_failed or proc.returncode not in (0, 1) else 1
    return 0 if receipt["numeric_status"] == "NUMERIC_PARITY_PASS" and proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
