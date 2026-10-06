import hashlib, json, math
from datetime import datetime, timezone
import validator_coherent as m

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)

def H(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')

def walk(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and (k == 'sha256' or k.endswith('sha256')):
                acc.add(v)
            else:
                walk(v, acc)
    elif isinstance(obj, list):
        for i in obj:
            walk(i, acc)

def seal(body):
    found = set()
    walk(body, found)
    body['artifacts'] = [{'sha256': s} for s in sorted(found)]
    return frozenset(found)

BINDS = {
    'model_sha256': H('model'),
    'workload_sha256': H('workload'),
    'build_sha256': H('build'),
    'executable_sha256': H('exec'),
}

def memory(usable=800, kind='DEDICATED'):
    return {
        'kind': kind, 'total_bytes': 1000, 'free_bytes': 400, 'reserve_bytes': 100,
        'highwater_bytes': 100, 'usable_bytes': usable, 'source': 'ACTUAL_ALLOCATOR',
        'measured_at': NOW.isoformat(),
    }

def block(pid, name, nbytes):
    return {'block_id': name, 'weight_sha256': H('w-' + name), 'owner': pid, 'resident_bytes': nbytes}

def device(pci, pid, vendor, cls, blocks, kind='DEDICATED', usable=800):
    return {
        'pci_id': pci, 'physical_id': pid, 'vendor': vendor, 'device_class': cls,
        'memory': memory(usable, kind),
        'kernel': {'completed': True, 'tensor_sha256': H('tensor-' + pid)},
        'blocks': blocks,
    }

def controls_for(pids, array_sha, wrong=False):
    use = ['other-device'] if wrong else list(pids)
    def one(kind, code, detected):
        row = {'kind': kind, 'scope': 'COMPARE_ONLY', 'exit_code': code, 'detected': detected,
               'artifact_sha256': array_sha, 'physical_ids': use}
        row.update(BINDS)
        return row
    return [one('CLEAN_BASELINE', 0, False), one('COMPARATOR_ONLY', 1, True)]

def proof(pids, deltas, refs, atol=1e-6, rtol=1e-6):
    doc = {'deltas': deltas, 'references': refs, 'physical_ids': list(pids), 'context': None, 'quant_sha256': None}
    doc.update(BINDS)
    blob = canon(doc)
    return H(blob), blob, doc

def numerical(pids, deltas, refs, array_sha, ref_sha, **extra):
    max_abs = max(abs(float(d)) for d in deltas)
    rmse = math.sqrt(sum(float(d) * float(d) for d in deltas) / len(deltas))
    ev = {
        'full_count': len(deltas), 'finite_count': len(deltas), 'violation_count': 0,
        'rmse': rmse, 'max_abs_error': max_abs, 'atol': 1e-6, 'rtol': 1e-6,
        'predeclared_atol': 1e-6, 'predeclared_rtol': 1e-6,
        'array_sha256': array_sha, 'reference_sha256': ref_sha, 'physical_ids': list(pids),
    }
    ev.update(BINDS)
    ev.update(extra)
    return ev

def two_receipt(second_cls, second_vendor, deltas=(0.0,), refs=(1.0,), wrong_controls=False, summary=None, scale=None):
    pids = ['gpu-nv', 'gpu-second']
    array_sha, blob, _doc = proof(pids, list(deltas), list(refs))
    ref_sha = H('unrelated-reference')
    ev = numerical(pids, deltas, refs, array_sha, ref_sha)
    if summary is not None:
        ev['max_abs_error'] = summary['max_abs_error']
        ev['rmse'] = summary['rmse']
    if scale is not None:
        ev['reference_scale'] = scale
    body = {
        'schema': 1, 'timestamp': NOW.isoformat(), 'claims': ['TWO_VENDOR_NUMERICAL'],
        'bindings': dict(BINDS),
        'devices': [
            device('0000:01:00.0', 'gpu-nv', 'NVIDIA', 'DISCRETE_GPU', [block('gpu-nv', 'nv0', 800)]),
            device('0000:02:00.0', 'gpu-second', second_vendor, second_cls, [block('gpu-second', 's0', 800)],
                   kind='DEDICATED' if second_cls == 'DISCRETE_GPU' else 'SHARED_HOST'),
        ],
        'controls': controls_for(pids, array_sha, wrong=wrong_controls),
        'numerical': ev,
    }
    trusted = seal(body)
    return body, trusted, {array_sha: blob}, ref_sha, blob

def test_schema():
    for bad in (1.0, True, False):
        out = m.validate_result({'schema': bad}, now_utc=NOW)
        assert out['status'] == 'REFUSED' and 'INVALID_SCHEMA' in out['reasons'] and out['qualified_claims'] == [], out

def test_scale_and_unverified():
    body, trusted, payloads, _ref, _blob = two_receipt('IGPU', 'Intel', scale='nan')
    out = m.validate_result(body, now_utc=NOW, trusted_artifact_hashes=trusted)
    assert out['status'] == 'NOT_CHECKED' and out['qualified_claims'] == [], out
    body2, trusted2, payloads2, ref_sha, blob = two_receipt('IGPU', 'Intel')
    out2 = m.validate_result(body2, now_utc=NOW, trusted_artifact_hashes=trusted2)
    assert out2['status'] == 'NOT_CHECKED' and out2['qualified_claims'] == [], out2
    unrelated = {ref_sha: blob}
    out3 = m.validate_result(body2, now_utc=NOW, trusted_artifact_hashes=trusted2, verified_artifact_payloads=unrelated)
    assert out3['status'] == 'NOT_CHECKED' and out3['qualified_claims'] == [], out3
    out4 = m.validate_result(body2, now_utc=NOW, trusted_artifact_hashes=trusted2, verified_artifact_payloads=payloads2)
    assert out4['status'] == 'QUALIFIED' and out4['qualified_claims'] == ['TWO_VENDOR_NUMERICAL'], out4

def test_cpu_igpu_and_wrong_controls():
    cpu, tc, _pc, _r, _b = two_receipt('CPU', 'Intel')
    out = m.validate_result(cpu, now_utc=NOW, trusted_artifact_hashes=tc, verified_artifact_payloads=_pc)
    assert out['status'] == 'REFUSED' and 'CPU_OR_OTHER_VENDOR' in out['reasons'] and out['qualified_claims'] == [], out
    bad, tb, pb, _r, _b = two_receipt('IGPU', 'Intel', wrong_controls=True)
    outb = m.validate_result(bad, now_utc=NOW, trusted_artifact_hashes=tb, verified_artifact_payloads=pb)
    assert outb['status'] == 'REFUSED' and 'CONTROL_DEVICE_MISMATCH' in outb['reasons'] and outb['qualified_claims'] == [], outb

def test_wrong_summary():
    body, trusted, payloads, _r, _b = two_receipt('IGPU', 'Intel', deltas=(0.5,), refs=(1.0,), summary={'max_abs_error': 0.0, 'rmse': 0.0})
    body['numerical']['atol'] = 1.0
    body['numerical']['rtol'] = 1.0
    body['numerical']['predeclared_atol'] = 1.0
    body['numerical']['predeclared_rtol'] = 1.0
    trusted = seal(body)
    out = m.validate_result(body, now_utc=NOW, trusted_artifact_hashes=trusted, verified_artifact_payloads=payloads)
    assert out['status'] == 'REFUSED' and out['qualified_claims'] == [], out

def test_many_blocks():
    devs = []
    for i, vendor in enumerate(('NVIDIA', 'AMD', 'Intel', 'NVIDIA')):
        pid = 'card-%d' % i
        blocks = [block(pid, '%s-a' % pid, 300), block(pid, '%s-b' % pid, 500)]
        devs.append(device('0000:%02x:00.0' % (i + 1), pid, vendor, 'DISCRETE_GPU', blocks))
    body = {
        'schema': 1, 'timestamp': NOW.isoformat(), 'claims': ['FOUR_PHYSICAL_GPU'],
        'bindings': dict(BINDS), 'devices': devs, 'controls': [],
    }
    trusted = seal(body)
    out = m.validate_result(body, now_utc=NOW, trusted_artifact_hashes=trusted)
    assert out['status'] == 'QUALIFIED' and out['qualified_claims'] == ['FOUR_PHYSICAL_GPU'], out

def test_llm_igpu():
    pids = ['igpu-0']
    array_sha, blob, _doc = proof(pids, [0.0], [1.0])
    ev = numerical(pids, [0.0], [1.0], array_sha, H('llm-ref'))
    ev.update({'licensed': True, 'gguf_sha256': H('gguf'), 'attention_ops': ['attn'], 'kv_ops': ['kv'], 'vocab': 1})
    body = {
        'schema': 1, 'timestamp': NOW.isoformat(), 'claims': ['LLM_LOGIT_PARITY'],
        'bindings': dict(BINDS),
        'devices': [device('0000:0a:00.0', 'igpu-0', 'Intel', 'IGPU', [block('igpu-0', 'i0', 800)], kind='SHARED_HOST')],
        'controls': controls_for(pids, array_sha), 'llm': ev,
    }
    trusted = seal(body)
    out = m.validate_result(body, now_utc=NOW, trusted_artifact_hashes=trusted, verified_artifact_payloads={array_sha: blob})
    assert out['status'] == 'QUALIFIED' and out['qualified_claims'] == ['LLM_LOGIT_PARITY'], out

if __name__ == '__main__':
    test_schema()
    test_scale_and_unverified()
    test_cpu_igpu_and_wrong_controls()
    test_wrong_summary()
    test_many_blocks()
    test_llm_igpu()

