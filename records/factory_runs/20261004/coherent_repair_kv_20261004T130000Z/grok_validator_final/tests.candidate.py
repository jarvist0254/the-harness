import copy, hashlib, importlib.util, inspect, json, math, threading
from datetime import datetime, timezone

PATH = r'E:\the_harness\records\factory_runs\20261004\coherent_repair_kv_20261004T130000Z\grok_validator_focus\qualification_validator.grok_corrected.py'
spec = importlib.util.spec_from_file_location('qualification_validator_grok_corrected', PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def _sha(blob):
    if isinstance(blob, str):
        blob = blob.encode()
    return hashlib.sha256(blob).hexdigest()

def _walk(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'sha256' or k.endswith('_sha256'):
                found.append(v)
            else:
                _walk(v, found)
    elif isinstance(obj, list):
        for i in obj:
            _walk(i, found)

def _status(r):
    if isinstance(r, dict):
        return r.get('status'), list(r.get('reasons') or [])
    return r[0], list(r[1])

def _payloads(encoding, refs, values):
    ref_b = json.dumps(refs, separators=(',', ':')).encode()
    arr_b = json.dumps({'encoding': encoding, 'values': values}, separators=(',', ':')).encode()
    return ref_b, arr_b, _sha(ref_b), _sha(arr_b)

def _metrics(encoding, refs, values):
    errs = []
    for value, ref in zip(values, refs):
        signed = float(value) if encoding == 'delta' else float(value) - float(ref)
        errs.append(signed)
    max_abs = max(abs(e) for e in errs)
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    return max_abs, rmse

def _receipt(claim, encoding, refs, values, *, vocab=None):
    ref_b, arr_b, ref_h, arr_h = _payloads(encoding, refs, values)
    max_abs, rmse = _metrics(encoding, refs, values)
    names = {}
    def H(label):
        names[label] = _sha(label)
        return names[label]
    binds = {k: H(k) for k in ('model_sha256', 'workload_sha256', 'build_sha256', 'executable_sha256')}
    quant, tensor, weight, clean, comp, gguf = H('quant'), H('tensor'), H('weight'), H('clean'), H('comp'), H('gguf')
    pids = ['gpu-nv', 'gpu-amd']
    ev = dict(binds)
    ev.update({
        'full_count': len(refs), 'finite_count': len(refs), 'violation_count': 0,
        'rmse': rmse, 'max_abs_error': max_abs, 'atol': 0.0, 'rtol': 0.1,
        'predeclared_atol': 0.0, 'predeclared_rtol': 0.1,
        'array_sha256': arr_h, 'reference_sha256': ref_h,
        'physical_ids': list(pids), 'context': 128, 'quant_sha256': quant,
        'clean_artifact_sha256': clean,
    })
    if vocab is not None:
        ev['vocab'] = vocab
        ev['licensed'] = True
        ev['gguf_sha256'] = gguf
        ev['attention_ops'] = ['attn']
        ev['kv_ops'] = ['kv']
    def dev(pid, pci, vendor, cls):
        return {
            'pci_id': pci, 'physical_id': pid, 'vendor': vendor, 'device_class': cls,
            'kernel': {'completed': True, 'tensor_sha256': tensor},
            'blocks': [
                {'block_id': pid + '-0', 'weight_sha256': weight, 'owner': pid},
                {'block_id': pid + '-1', 'weight_sha256': weight, 'owner': pid},
            ],
        }
    devices = [
        dev('gpu-nv', '0000:01:00.0', 'NVIDIA', 'DISCRETE_GPU'),
        dev('gpu-amd', '0000:02:00.0', 'AMD', 'IGPU'),
    ]
    def ctrl(kind, art, exit_code, detected, **extra):
        row = dict(binds)
        row.update({
            'kind': kind, 'scope': 'COMPARE_ONLY', 'artifact_sha256': art,
            'exit_code': exit_code, 'detected': detected, 'physical_ids': list(pids),
            'quant_sha256': quant, 'context': 128,
        })
        row.update(extra)
        return row
    neg_kind = 'COMPARATOR_CONTROL' if claim == 'LLM_LOGIT_PARITY' else 'COMPARATOR_ONLY'
    controls = [
        ctrl('CLEAN_BASELINE', clean, 0, False),
        ctrl(neg_kind, comp, 1, True, baseline_artifact_sha256=clean),
    ]
    receipt = {
        'schema': 1, 'timestamp': '2026-10-04T12:00:00Z', 'claims': [claim],
        'bindings': binds, 'devices': devices, 'controls': controls,
    }
    if claim == 'LLM_LOGIT_PARITY':
        receipt['llm'] = ev
    else:
        receipt['numerical'] = ev
    found = []
    _walk(receipt, found)
    arts, seen = [], set()
    for h in found:
        if h not in seen:
            seen.add(h)
            arts.append({'sha256': h})
    receipt['artifacts'] = arts
    return receipt, {ref_h: ref_b, arr_h: arr_b}, frozenset(seen)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)

def _run(receipt, payloads, trust):
    return _status(mod.validate_result(copy.deepcopy(receipt), now_utc=NOW, trusted_artifact_hashes=trust, verified_artifact_payloads=payloads))

def test_sources_have_no_global_payload_state():
    for fn in (mod.validate_result, mod._claim, mod._two, mod._capacity, mod._llm, mod._p2p, mod._numbers):
        assert '_payloads' not in inspect.getsource(fn)
    assert 'validate_result' not in inspect.getsource(mod._numbers)
    assert 'numerical_payloads' in inspect.signature(mod._numbers).parameters

def test_target_relative_pass_and_igpu_two_vendor():
    refs, values = [4.0, -8.0], [4.0, -8.5]
    receipt, payloads, trust = _receipt('TWO_VENDOR_NUMERICAL', 'target', refs, values)
    st, reasons = _run(receipt, payloads, trust)
    assert st == 'QUALIFIED' and reasons == [], (st, reasons)
    assert not hasattr(mod.validate_result, '_payloads')

def test_llm_delta_per_logit_and_unique_control_digests():
    refs, values = [4.0, 8.0], [0.0, 0.5]
    receipt, payloads, trust = _receipt('LLM_LOGIT_PARITY', 'delta', refs, values, vocab=2)
    clean = receipt['llm']['clean_artifact_sha256']
    comp = receipt['controls'][1]['artifact_sha256']
    assert clean != comp and clean != receipt['llm']['array_sha256']
    st, reasons = _run(receipt, payloads, trust)
    assert st == 'QUALIFIED' and reasons == [], (st, reasons)

def test_missing_and_reference_hash_mismatch():
    refs, values = [4.0, 8.0], [4.0, 8.5]
    receipt, payloads, trust = _receipt('TWO_VENDOR_NUMERICAL', 'target', refs, values)
    ref_h = receipt['numerical']['reference_sha256']
    missing = dict(payloads)
    missing.pop(ref_h)
    st, reasons = _run(receipt, missing, trust)
    assert st == 'NOT_CHECKED' and 'UNVERIFIED_PAYLOAD' in reasons
    bad = dict(payloads)
    bad[ref_h] = b'[1.0,2.0]'
    st, reasons = _run(receipt, bad, trust)
    assert st == 'REFUSED' and 'PAYLOAD_HASH_MISMATCH' in reasons
    assert not hasattr(mod.validate_result, '_payloads')

def test_combined_blob_does_not_qualify():
    blob = json.dumps({'deltas': [0.0, 0.5], 'references': [4.0, 8.0]}).encode()
    refs, values = [4.0, 8.0], [0.0, 0.5]
    receipt, payloads, trust = _receipt('TWO_VENDOR_NUMERICAL', 'delta', refs, values)
    ev = receipt['numerical']
    ev['array_sha256'] = _sha(blob)
    found = []
    receipt['artifacts'] = []
    _walk(receipt, found)
    arts, seen = [], set()
    for h in found:
        if h not in seen:
            seen.add(h)
            arts.append({'sha256': h})
    receipt['artifacts'] = arts
    trust = frozenset(seen)
    payloads = {ev['reference_sha256']: payloads[list(payloads)[0]] if False else json.dumps(refs, separators=(',', ':')).encode(), ev['array_sha256']: blob}
    payloads[ev['reference_sha256']] = json.dumps(refs, separators=(',', ':')).encode()
    st, reasons = _run(receipt, payloads, trust)
    assert st == 'REFUSED' and 'PAYLOAD_MALFORMED' in reasons

def test_relative_logit_fail():
    refs, values = [4.0, 8.0], [4.0, 9.0]
    ref_b, arr_b, ref_h, arr_h = _payloads('target', refs, values)
    ev = {
        'full_count': 2, 'finite_count': 2, 'violation_count': 0,
        'rmse': 0.0, 'max_abs_error': 1.0, 'atol': 0.0, 'rtol': 0.1,
        'predeclared_atol': 0.0, 'predeclared_rtol': 0.1,
        'array_sha256': arr_h, 'reference_sha256': ref_h,
        'model_sha256': _sha('m'), 'workload_sha256': _sha('w'),
        'build_sha256': _sha('b'), 'executable_sha256': _sha('e'),
    }
    binds = {k: ev[k] for k in ('model_sha256', 'workload_sha256', 'build_sha256', 'executable_sha256')}
    st, reason = mod._numbers(ev, binds, None, {ref_h: ref_b, arr_h: arr_b})
    assert st == 'REFUSED' and reason == 'NUMERICAL_TOLERANCE_EXCEEDED'

def test_control_wrong_baseline_device_model_context():
    refs, values = [4.0, 8.0], [4.0, 8.5]
    receipt, payloads, trust = _receipt('TWO_VENDOR_NUMERICAL', 'target', refs, values)
    base = copy.deepcopy(receipt)
    base['controls'][1]['baseline_artifact_sha256'] = base['numerical']['array_sha256']
    st, reasons = _run(base, payloads, trust)
    assert st == 'REFUSED' and 'CONTROL_BASELINE_MISMATCH' in reasons
    dev = copy.deepcopy(receipt)
    dev['controls'][0]['physical_ids'] = ['gpu-nv', 'other']
    st, reasons = _run(dev, payloads, trust)
    assert st == 'REFUSED' and 'CONTROL_DEVICE_MISMATCH' in reasons
    model = copy.deepcopy(receipt)
    model['controls'][0]['model_sha256'] = model['bindings']['workload_sha256']
    st, reasons = _run(model, payloads, trust)
    assert st != 'QUALIFIED'
    ctx = copy.deepcopy(receipt)
    ctx['controls'][1]['context'] = 64
    st, reasons = _run(ctx, payloads, trust)
    assert st == 'REFUSED' and 'CONTROL_CONTEXT_MISMATCH' in reasons

def test_reentrant_calls_do_not_cross_payloads():
    refs, values = [4.0, -8.0], [4.0, -8.5]
    receipt, good, trust = _receipt('TWO_VENDOR_NUMERICAL', 'target', refs, values)
    bad = dict(good)
    ref_h = receipt['numerical']['reference_sha256']
    bad[ref_h] = b'[0.0,0.0]'
    errors = []
    barrier = threading.Barrier(8)
    def worker(payloads, expect):
        try:
            barrier.wait(timeout=5)
            for _ in range(12):
                st, reasons = _run(receipt, payloads, trust)
                if st != expect:
                    errors.append((expect, st, reasons))
        except Exception as exc:
            errors.append(repr(exc))
    threads = []
    for i in range(8):
        payload, expect = (good, 'QUALIFIED') if i % 2 == 0 else (bad, 'REFUSED')
        threads.append(threading.Thread(target=worker, args=(payload, expect)))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, errors
    assert not hasattr(mod.validate_result, '_payloads')

if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

