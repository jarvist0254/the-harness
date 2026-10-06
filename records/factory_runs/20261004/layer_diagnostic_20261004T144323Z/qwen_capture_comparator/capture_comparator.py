import json
import hashlib
import math
import os
import struct
from typing import Any, Dict, List, Optional

class CaptureError(Exception):
    pass

def _strict_pairs(pairs: List[tuple]) -> dict:
    seen = set()
    for k, v in pairs:
        if k in seen:
            raise CaptureError(f"Duplicate JSON key: {k}")
        seen.add(k)
    return dict(pairs)

def _parse_json(data: bytes) -> Any:
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        raise CaptureError("Manifest not valid UTF-8")
    return json.loads(text, object_pairs_hook=_strict_pairs)

def _is_64hex(v: Any) -> bool:
    if not isinstance(v, str) or len(v) != 64:
        return False
    try:
        int(v, 16)
        return True
    except ValueError:
        return False

def _validate_origin(o: dict, role: str, exp: dict) -> None:
    if o.get('pinned_commit') != '0faee5004297c3bcfa40b7bf11750127b8c1fd7d':
        raise CaptureError("Bad pinned_commit")
    for f in ('source_sha256', 'executable_sha256', 'workload_sha256'):
        v = o.get(f)
        if not _is_64hex(v):
            raise CaptureError(f"Bad {f}")
        if f in exp and v != exp[f]:
            raise CaptureError(f"Mismatch {f}")
    ms = o.get('model_sha256')
    mb = o.get('model_bytes')
    valid_models = {
        '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031': 639446688,
        'bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80': 2390150816
    }
    if ms not in valid_models:
        raise CaptureError("Bad model_sha256")
    if mb != valid_models[ms]:
        raise CaptureError("Bad model_bytes")
    if 'model_sha256' in exp and ms != exp['model_sha256']:
        raise CaptureError("Mismatch model_sha256")
    if 'model_bytes' in exp and mb != exp['model_bytes']:
        raise CaptureError("Mismatch model_bytes")
    if role == 'CPU_REFERENCE':
        if o.get('role') != 'CPU_REFERENCE': raise CaptureError("Bad CPU role")
        if o.get('devices') != []: raise CaptureError("CPU devices must be []")
        if o.get('vulkan_disable_f16') is not False: raise CaptureError("CPU vulkan_disable_f16")
        if o.get('vulkan_disable_fusion') is not False: raise CaptureError("CPU vulkan_disable_fusion")
    elif role == 'VULKAN_DIAGNOSTIC':
        if o.get('role') != 'VULKAN_DIAGNOSTIC': raise CaptureError("Bad GPU role")
        devs = o.get('devices')
        if not isinstance(devs, list) or len(devs) not in (1, 2): raise CaptureError("GPU devices count")
        if len(set(devs)) != len(devs): raise CaptureError("GPU devices not unique")
        for d in devs:
            if not isinstance(d, str) or d not in ('Vulkan0', 'Vulkan1'): raise CaptureError("Bad device name")
        if 'devices' in exp and devs != exp['devices']: raise CaptureError("Mismatch devices")
        if o.get('vulkan_disable_f16') is not True: raise CaptureError("GPU vulkan_disable_f16")
        if o.get('vulkan_disable_fusion') is not True: raise CaptureError("GPU vulkan_disable_fusion")
    else:
        raise CaptureError("Unknown role")
    toks = o.get('tokens')
    if not isinstance(toks, list) or not all(isinstance(t, int) and not isinstance(t, bool) and 0 <= t <= 15 for t in toks):
        raise CaptureError("Bad tokens")
    for k, v in [('n_ctx_requested', 128), ('n_ctx_actual', 256), ('n_batch', 32), ('n_ubatch', 32), ('n_threads', 4)]:
        if o.get(k) != v: raise CaptureError(f"Bad {k}")
    if o.get('kv_type_k') != 'F32' or o.get('kv_type_v') != 'F32': raise CaptureError("Bad kv_type")
    if o.get('flash_attention') is not False: raise CaptureError("Bad flash_attention")

def _validate_node(n: dict, idx: int, seen: set) -> None:
    if n.get('ordinal') != idx or isinstance(n.get('ordinal'), bool):
        raise CaptureError(f"Bad ordinal {idx}")
    name = n.get('name')
    valid_prefixes = ('attn_norm-', 'ffn_inp-', 'ffn_norm-', 'ffn_out-', 'l_out-')
    ok = name in ('result_norm', 'result_output')
    if not ok and isinstance(name, str):
        for p in valid_prefixes:
            if name.startswith(p):
                suf = name[len(p):]
                if suf.isdigit() and 0 <= int(suf) <= 27:
                    ok = True
                    break
    if not ok:
        raise CaptureError(f"Bad node name {name}")
    if name in seen:
        raise CaptureError(f"Duplicate name {name}")
    seen.add(name)
    if not isinstance(n.get('op'), str) or not n['op']:
        raise CaptureError("Bad op")
    if n.get('dtype') != 'F32_LE':
        raise CaptureError("Bad dtype")
    dims = n.get('dims')
    if not isinstance(dims, list) or len(dims) != 4:
        raise CaptureError("Bad dims")
    for d in dims:
        if not isinstance(d, int) or isinstance(d, bool) or d <= 0:
            raise CaptureError("Bad dim value")
    strides = n.get('strides')
    exp_strides = [4, 4*dims[0], 4*dims[0]*dims[1], 4*dims[0]*dims[1]*dims[2]]
    if strides != exp_strides:
        raise CaptureError("Bad strides")
    nbytes = n.get('nbytes')
    exp_nbytes = dims[0]*dims[1]*dims[2]*dims[3]*4
    if nbytes != exp_nbytes or isinstance(nbytes, bool):
        raise CaptureError("Bad nbytes")
    if nbytes > 16777216:
        raise CaptureError("Tensor too large")
    sha = n.get('sha256')
    if not _is_64hex(sha):
        raise CaptureError("Bad sha256")
    f = n.get('file')
    if not isinstance(f, str) or os.path.isabs(f) or ':' in f or '..' in f or '/' in f or '\\' in f:
        raise CaptureError("Bad file path")

def _safe_resolve(root: str, fname: str) -> str:
    root_r = os.path.realpath(root)
    full = os.path.join(root_r, fname)
    full_r = os.path.realpath(full)
    if not full_r.startswith(root_r + os.sep) and full_r != root_r:
        raise CaptureError("Path escapes root")
    parts = os.path.normpath(full).split(os.sep)
    for i in range(len(parts)):
        p = os.sep.join(parts[:i+1]) if i > 0 else parts[0]
        if not p:
            continue
        try:
            if os.path.islink(p):
                raise CaptureError("Symlink detected")
            st = os.stat(p)
            if hasattr(st, 'st_file_attributes'):
                if st.st_file_attributes & 0x400:
                    raise CaptureError("Reparse point detected")
        except OSError:
            pass
    return full_r

def _read_tensor(root: str, node: dict) -> bytes:
    path = _safe_resolve(root, node['file'])
    sz = os.path.getsize(path)
    if sz != node['nbytes']:
        raise CaptureError("Size mismatch")
    with open(path, 'rb') as f:
        data = f.read()
    h = hashlib.sha256(data).hexdigest()
    if h != node['sha256']:
        raise CaptureError("SHA256 mismatch")
    fmt = f'<{node["nbytes"]//4}f'
    vals = struct.unpack(fmt, data)
    for v in vals:
        if not math.isfinite(v):
            raise CaptureError("Non-finite value")
    return data

def _load_root(root: str, role: str, expected: dict) -> tuple:
    if not os.path.isdir(root):
        raise CaptureError("Root not dir")
    mpath = _safe_resolve(root, 'manifest.json')
    if os.path.getsize(mpath) > 131072:
        raise CaptureError("Manifest too large")
    with open(mpath, 'rb') as f:
        raw = f.read()
    m = _parse_json(raw)
    if m.get('schema') != 'LLAMA_CAPTURE_V1':
        raise CaptureError("Bad schema")
    if m.get('status') != 'COMPLETE':
        raise CaptureError("Bad status")
    if m.get('diagnostic_intrusive') is not True:
        raise CaptureError("Not intrusive")
    if m.get('qualification') != 'DIAGNOSTIC_ONLY':
        raise CaptureError("Bad qualification")
    o = m.get('origin')
    if not isinstance(o, dict):
        raise CaptureError("Missing origin")
    _validate_origin(o, role, expected)
    caps = m.get('captures')
    if not isinstance(caps, list) or len(caps) == 0:
        raise CaptureError("Empty captures")
    if len(caps) > 144:
        raise CaptureError("Too many nodes")
    total = sum(c.get('nbytes', 0) for c in caps if isinstance(c.get('nbytes'), int))
    if total > 67108864:
        raise CaptureError("Pass too large")
    seen = set()
    for i, c in enumerate(caps):
        _validate_node(c, i, seen)
    tensors = []
    for c in caps:
        tensors.append(_read_tensor(root, c))
    return caps, tensors

def compare_artifacts(cpu_root: str, gpu_root: str, *args, expected: Optional[dict] = None, atol: float = 0.01, rtol: float = 0.01, **kwargs) -> dict:
    if expected is None:
        expected = {}
    if not isinstance(expected, dict):
        raise CaptureError("expected must be dict")
    if isinstance(atol, bool) or isinstance(rtol, bool):
        raise CaptureError("Tolerance cannot be bool")
    if not isinstance(atol, (int, float)) or not isinstance(rtol, (int, float)):
        raise CaptureError("Tolerance must be numeric")
    if atol < 0 or rtol < 0 or not math.isfinite(atol) or not math.isfinite(rtol):
        raise CaptureError("Tolerance must be finite non-negative")
    atol, rtol = float(atol), float(rtol)
    cpu_nodes, cpu_tensors = _load_root(cpu_root, 'CPU_REFERENCE', expected)
    gpu_nodes, gpu_tensors = _load_root(gpu_root, 'VULKAN_DIAGNOSTIC', expected)
    if len(cpu_nodes) != len(gpu_nodes):
        return {'result': 'DIAGNOSTIC_DIVERGENCE', 'reason': 'node_count_mismatch'}
    for i, (cn, gn) in enumerate(zip(cpu_nodes, gpu_nodes)):
        if cn['name'] != gn['name'] or cn['op'] != gn['op'] or cn['dims'] != gn['dims'] or cn['dtype'] != gn['dtype'] or cn['strides'] != gn['strides']:
            return {'result': 'DIAGNOSTIC_DIVERGENCE', 'first_divergent_ordinal': i, 'reason': 'metadata_mismatch'}
    result = 'DIAGNOSTIC_MATCH'
    first_div = None
    stats = {}
    for i, (ct, gt) in enumerate(zip(cpu_tensors, gpu_tensors)):
        nf = len(ct) // 4
        cv = struct.unpack(f'<{nf}f', ct)
        gv = struct.unpack(f'<{nf}f', gt)
        max_abs = 0.0
        sum_sq = 0.0
        failed = 0
        samples = []
        for j in range(nf):
            c_val, g_val = cv[j], gv[j]
            diff = abs(c_val - g_val)
            if diff > max_abs:
                max_abs = diff
            sum_sq += diff * diff
            tol = atol + rtol * abs(c_val)
            if diff > tol:
                failed += 1
                if len(samples) < 8:
                    samples.append({'index': j, 'cpu': c_val, 'gpu': g_val, 'diff': diff})
        rmse = math.sqrt(sum_sq / nf) if nf > 0 else 0.0
        if failed > 0:
            result = 'DIAGNOSTIC_DIVERGENCE'
            if first_div is None:
                first_div = i
                stats = {'max_abs': max_abs, 'rmse': rmse, 'failed_count': failed, 'samples': samples}
    out = {'result': result, 'comparator': 'COMPARATOR_ONLY'}
    if first_div is not None:
        out['first_divergent_ordinal'] = first_div
        out['stats'] = stats
    return out

