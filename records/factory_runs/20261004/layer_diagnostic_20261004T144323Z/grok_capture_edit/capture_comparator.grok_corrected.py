from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

class CaptureError(Exception):
    pass

_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_MAX_MANIFEST = 131072
_MAX_TENSOR = 16777216
_MAX_PASS = 67108864
_MAX_NODES = 144
_MAX_SUMMARY = 131072
_COMMIT = "0faee5004297c3bcfa40b7bf11750127b8c1fd7d"
_MODELS = {
    "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031": 639446688,
    "bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80": 2390150816,
}
_EXPECTED_KEYS = frozenset({
    "source_sha256", "executable_sha256", "model_sha256", "model_bytes", "workload_sha256", "devices",
})
_MANIFEST_KEYS = frozenset({
    "schema", "status", "diagnostic_intrusive", "qualification", "origin", "captures",
})
_ORIGIN_KEYS = frozenset({
    "pinned_commit", "source_sha256", "executable_sha256", "model_sha256", "model_bytes",
    "workload_sha256", "role", "devices", "tokens", "n_ctx_requested", "n_ctx_actual",
    "n_batch", "n_ubatch", "n_threads", "kv_type_k", "kv_type_v", "flash_attention",
    "vulkan_disable_f16", "vulkan_disable_fusion",
})
_NODE_KEYS = frozenset({
    "ordinal", "name", "op", "dtype", "dims", "strides", "nbytes", "sha256", "file",
})
_PREFIXES = ("attn_norm-", "ffn_inp-", "ffn_norm-", "ffn_out-", "l_out-")
_INT_ORIGIN = (
    ("n_ctx_requested", 128), ("n_ctx_actual", 256), ("n_batch", 32), ("n_ubatch", 32), ("n_threads", 4),
)

def _is_int(v: Any) -> bool:
    return type(v) is int

def _hex64(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)

def _strict_pairs(pairs: List[tuple]) -> dict:
    seen = set()
    out = {}
    for key, value in pairs:
        if key in seen:
            raise CaptureError("Duplicate JSON key: " + str(key))
        seen.add(key)
        out[key] = value
    return out

def _exact_keys(obj: Any, keys: frozenset, label: str) -> dict:
    if type(obj) is not dict or set(obj) != keys:
        raise CaptureError("Strict fields rejected: " + label)
    return obj

def _canonical_name(name: Any) -> bool:
    if type(name) is not str:
        return False
    if name in ("result_norm", "result_output"):
        return True
    for prefix in _PREFIXES:
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            if suffix.isdigit() and str(int(suffix)) == suffix and 0 <= int(suffix) <= 27:
                return True
    return False

def _lexical_absolute(path_str: str) -> Path:
    if type(path_str) is not str or path_str == "":
        raise CaptureError("Bad path")
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    parts = path.parts
    if len(parts) < 1:
        raise CaptureError("Bad path")
    for part in parts[1:]:
        if part in (".", "..") or part == "" or "/" in part or "\\" in part or ":" in part:
            raise CaptureError("Bad path component")
    return path

def _reject_component(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise CaptureError("Path inspection failed") from exc
    if stat.S_ISLNK(info.st_mode):
        raise CaptureError("Symlink rejected")
    if getattr(info, "st_file_attributes", 0) & _REPARSE:
        raise CaptureError("Reparse rejected")
    return info

def _inspect_chain(path: Path) -> os.stat_result:
    parts = path.parts
    current = Path(parts[0])
    info = _reject_component(current)
    for part in parts[1:]:
        current = current / part
        info = _reject_component(current)
    return info

def _read_bounded(path: Path, limit: int, exact: Optional[int]) -> bytes:
    info = _inspect_chain(path)
    if not stat.S_ISREG(info.st_mode):
        raise CaptureError("Not a regular file")
    cap = limit if exact is None else exact
    if info.st_size > cap:
        raise CaptureError("File too large")
    try:
        with path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError as exc:
        raise CaptureError("Read failed") from exc
    if len(data) > cap:
        raise CaptureError("File too large")
    if exact is not None and len(data) != exact:
        raise CaptureError("Size mismatch")
    return data

def _validate_expected(expected: Any) -> dict:
    exp = _exact_keys(expected, _EXPECTED_KEYS, "expected")
    for key in ("source_sha256", "executable_sha256", "model_sha256", "workload_sha256"):
        if not _hex64(exp[key]):
            raise CaptureError("Bad expected " + key)
    if exp["model_sha256"] not in _MODELS or not _is_int(exp["model_bytes"]):
        raise CaptureError("Bad expected model pin")
    if exp["model_bytes"] != _MODELS[exp["model_sha256"]]:
        raise CaptureError("Bad expected model_bytes")
    devices = exp["devices"]
    if type(devices) is not list or len(devices) not in (1, 2):
        raise CaptureError("Bad expected devices")
    if len(set(devices)) != len(devices):
        raise CaptureError("Bad expected devices")
    for device in devices:
        if type(device) is not str or device not in ("Vulkan0", "Vulkan1"):
            raise CaptureError("Bad expected devices")
    return exp

def _validate_origin(origin: Any, role: str, expected: dict) -> dict:
    item = _exact_keys(origin, _ORIGIN_KEYS, "origin")
    if item["pinned_commit"] != _COMMIT or item["role"] != role:
        raise CaptureError("Bad origin identity")
    for key in ("source_sha256", "executable_sha256", "workload_sha256"):
        if not _hex64(item[key]) or item[key] != expected[key]:
            raise CaptureError("Pin mismatch " + key)
    model = item["model_sha256"]
    if not _hex64(model) or model not in _MODELS or not _is_int(item["model_bytes"]):
        raise CaptureError("Bad model pin")
    if item["model_bytes"] != _MODELS[model] or model != expected["model_sha256"] or item["model_bytes"] != expected["model_bytes"]:
        raise CaptureError("Model pin mismatch")
    tokens = item["tokens"]
    if type(tokens) is not list or tokens != list(range(16)) or any(type(token) is not int for token in tokens):
        raise CaptureError("Bad tokens")
    for key, value in _INT_ORIGIN:
        if not _is_int(item[key]) or item[key] != value:
            raise CaptureError("Bad " + key)
    if item["kv_type_k"] != "F32" or item["kv_type_v"] != "F32" or item["flash_attention"] is not False:
        raise CaptureError("Bad kv or flash_attention")
    if role == "CPU_REFERENCE":
        if type(item["devices"]) is not list or item["devices"] != []:
            raise CaptureError("CPU devices must be []")
        if item["vulkan_disable_f16"] is not False or item["vulkan_disable_fusion"] is not False:
            raise CaptureError("CPU vulkan flags")
    elif role == "VULKAN_DIAGNOSTIC":
        if item["devices"] != expected["devices"]:
            raise CaptureError("GPU devices must exactly match expected order")
        if item["vulkan_disable_f16"] is not True or item["vulkan_disable_fusion"] is not True:
            raise CaptureError("GPU vulkan flags")
    else:
        raise CaptureError("Unknown role")
    return item

def _validate_node(node: Any, index: int, seen: set) -> dict:
    item = _exact_keys(node, _NODE_KEYS, "node")
    if not _is_int(item["ordinal"]) or item["ordinal"] != index:
        raise CaptureError("Bad ordinal")
    if not _canonical_name(item["name"]) or item["name"] in seen:
        raise CaptureError("Bad node name")
    seen.add(item["name"])
    if type(item["op"]) is not str or item["op"] == "" or item["dtype"] != "F32_LE":
        raise CaptureError("Bad op or dtype")
    dims = item["dims"]
    if type(dims) is not list or len(dims) != 4 or any((not _is_int(dim) or dim <= 0) for dim in dims):
        raise CaptureError("Bad dims")
    strides = [4, 4 * dims[0], 4 * dims[0] * dims[1], 4 * dims[0] * dims[1] * dims[2]]
    got = item["strides"]
    if type(got) is not list or len(got) != 4 or any(not _is_int(part) for part in got) or got != strides:
        raise CaptureError("Bad strides")
    nbytes = dims[0] * dims[1] * dims[2] * dims[3] * 4
    if not _is_int(item["nbytes"]) or item["nbytes"] != nbytes or item["nbytes"] > _MAX_TENSOR:
        raise CaptureError("Bad nbytes")
    if not _hex64(item["sha256"]):
        raise CaptureError("Bad sha256")
    file_name = item["file"]
    if type(file_name) is not str or file_name in ("", ".", "..") or any(ch in file_name for ch in "/\\:\0"):
        raise CaptureError("Bad file path")
    return item

def _load_root(root: str, role: str, expected: dict) -> Tuple[List[dict], List[bytes]]:
    root_path = _lexical_absolute(root)
    root_info = _inspect_chain(root_path)
    if not stat.S_ISDIR(root_info.st_mode):
        raise CaptureError("Root not directory")
    raw = _read_bounded(root_path / "manifest.json", _MAX_MANIFEST, None)
    if len(raw) > _MAX_MANIFEST:
        raise CaptureError("Manifest too large")
    try:
        text = raw.decode("utf-8")
        parsed = json.loads(text, object_pairs_hook=_strict_pairs)
    except CaptureError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise CaptureError("Manifest JSON invalid") from exc
    manifest = _exact_keys(parsed, _MANIFEST_KEYS, "manifest")
    if manifest["schema"] != "LLAMA_CAPTURE_V1" or manifest["status"] != "COMPLETE":
        raise CaptureError("Bad schema or status")
    if manifest["diagnostic_intrusive"] is not True or manifest["qualification"] != "DIAGNOSTIC_ONLY":
        raise CaptureError("Not diagnostic-only intrusive")
    _validate_origin(manifest["origin"], role, expected)
    captures = manifest["captures"]
    if type(captures) is not list or len(captures) == 0 or len(captures) > _MAX_NODES:
        raise CaptureError("Bad captures")
    seen: set = set()
    nodes: List[dict] = []
    total = 0
    for index, node in enumerate(captures):
        item = _validate_node(node, index, seen)
        total += item["nbytes"]
        if total > _MAX_PASS:
            raise CaptureError("Pass too large")
        nodes.append(item)
    tensors: List[bytes] = []
    for item in nodes:
        data = _read_bounded(root_path / item["file"], _MAX_TENSOR, item["nbytes"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise CaptureError("SHA256 mismatch")
        try:
            values = struct.unpack("<%df" % (len(data) // 4), data)
        except struct.error as exc:
            raise CaptureError("Tensor unpack failed") from exc
        if any(not math.isfinite(value) for value in values):
            raise CaptureError("Non-finite value")
        tensors.append(data)
    return nodes, tensors

def _tolerances(atol: Any, rtol: Any) -> Tuple[float, float]:
    if type(atol) is bool or type(rtol) is bool or not isinstance(atol, (int, float)) or not isinstance(rtol, (int, float)):
        raise CaptureError("Bad tolerance type")
    if not math.isfinite(float(atol)) or not math.isfinite(float(rtol)) or float(atol) != 0.01 or float(rtol) != 0.01:
        raise CaptureError("Tolerance must be exactly 0.01")
    return 0.01, 0.01

def _compare_nodes(cpu_nodes: List[dict], gpu_nodes: List[dict], cpu_tensors: List[bytes], gpu_tensors: List[bytes]) -> dict:
    if len(cpu_nodes) != len(gpu_nodes):
        raise CaptureError("Structural mismatch node count")
    for cpu_node, gpu_node in zip(cpu_nodes, gpu_nodes):
        for key in ("ordinal", "name", "op", "dtype", "dims", "strides", "nbytes"):
            if cpu_node[key] != gpu_node[key]:
                raise CaptureError("Structural mismatch " + key)
    reports: List[dict] = []
    first_noise = None
    first_threshold = None
    threshold_stats = None
    result = "DIAGNOSTIC_MATCH"
    for index, (cpu_node, cpu_raw, gpu_raw) in enumerate(zip(cpu_nodes, cpu_tensors, gpu_tensors)):
        count = len(cpu_raw) // 4
        cpu_values = struct.unpack("<%df" % count, cpu_raw)
        gpu_values = struct.unpack("<%df" % count, gpu_raw)
        max_abs = 0.0
        sum_sq = 0.0
        exact = 0
        failed = 0
        samples: List[dict] = []
        for element, (cpu_value, gpu_value) in enumerate(zip(cpu_values, gpu_values)):
            if not math.isfinite(cpu_value) or not math.isfinite(gpu_value):
                raise CaptureError("Non-finite value")
            diff = abs(cpu_value - gpu_value)
            if diff > max_abs:
                max_abs = diff
            sum_sq += diff * diff
            if diff != 0.0:
                exact += 1
                if first_noise is None:
                    first_noise = {"ordinal": index, "name": cpu_node["name"]}
            tol = 0.01 + 0.01 * abs(cpu_value)
            if diff > tol:
                failed += 1
                if first_threshold is None:
                    first_threshold = {"ordinal": index, "name": cpu_node["name"]}
                if threshold_stats is None and len(samples) < 8:
                    samples.append({"index": element, "cpu": cpu_value, "gpu": gpu_value, "diff": diff})
        rmse = math.sqrt(sum_sq / count)
        report = {
            "ordinal": index,
            "name": cpu_node["name"],
            "max_abs": max_abs,
            "rmse": rmse,
            "exact_mismatch_count": exact,
            "failed_count": failed,
        }
        reports.append(report)
        if failed and threshold_stats is None:
            threshold_stats = {
                "max_abs": max_abs,
                "rmse": rmse,
                "failed_count": failed,
                "exact_mismatch_count": exact,
                "samples": samples,
            }
            result = "DIAGNOSTIC_DIVERGENCE"
        elif failed:
            result = "DIAGNOSTIC_DIVERGENCE"
    out = {
        "result": result,
        "comparator": "COMPARATOR_ONLY",
        "control": "COMPARATOR_ONLY",
        "nodes": reports,
        "first_noise": first_noise,
        "first_threshold_violation": first_threshold,
    }
    if first_threshold is not None and threshold_stats is not None:
        out["first_divergent_ordinal"] = first_threshold["ordinal"]
        out["stats"] = threshold_stats
    blob = json.dumps(out, separators=(",", ":")).encode("utf-8")
    if len(blob) > _MAX_SUMMARY:
        if "stats" in out:
            out["stats"]["samples"] = []
            blob = json.dumps(out, separators=(",", ":")).encode("utf-8")
        if len(blob) > _MAX_SUMMARY:
            raise CaptureError("Summary exceeds 128KiB")
    return out

def compare_artifacts(cpu_root: str, gpu_root: str, *, expected: dict, atol: float = 0.01, rtol: float = 0.01) -> dict:
    _tolerances(atol, rtol)
    pins = _validate_expected(expected)
    cpu_nodes, cpu_tensors = _load_root(cpu_root, "CPU_REFERENCE", pins)
    gpu_nodes, gpu_tensors = _load_root(gpu_root, "VULKAN_DIAGNOSTIC", pins)
    return _compare_nodes(cpu_nodes, gpu_nodes, cpu_tensors, gpu_tensors)
