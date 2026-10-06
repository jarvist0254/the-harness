"""Schema 1 pure measured-evidence qualification validator.

Receipt keys:
  schema: 1
  timestamp: aware ISO-8601 UTC sample time
  artifacts: nonempty list of {sha256: 64 lowercase hex, role?: str}
  bindings: model_sha256, workload_sha256, build_sha256, executable_sha256
  devices: physical devices (may be empty only when unused)
  claims: requested claim names, unique strings
  numerical, llm, capacity, p2p, durable, controls: evidence objects

Device: pci_id, physical_id, vendor, device_class
  DISCRETE_GPU|IGPU|CPU|OTHER, optional memory, kernel, blocks.
PCI input is domain:bus:device.function. Domain is 4 or 8 hex and must be
<= 0xffff. Bus is 2 hex. Device is 2 hex and <= 0x1f. Function is 0..7.
Canonical form is four lowercase components, 0000:bb:dd.f. A missing domain
is not invented. Aliases that canonicalize equal are duplicates.
Memory: kind DEDICATED|SHARED_HOST|UNKNOWN, nonnegative non-bool int
  total_bytes, free_bytes, reserve_bytes, highwater_bytes, usable_bytes,
  source ACTUAL_ALLOCATOR|DRIVER_ADVERTISED|UNKNOWN, aware measured_at.
  free<=total, reserve<=total, usable<=total, highwater<=usable,
  usable+reserve<=total.
Kernel: completed bool plus tensor_sha256.
Block: nonempty block_id, weight_sha256, owner equal to physical_id.

Claims, never inferred from each other:
  TWO_VENDOR_NUMERICAL, FOUR_PHYSICAL_GPU, DEDICATED_CAPACITY_GT_ONE_CARD,
  FOUR_REQUIRED_CAPACITY, LLM_LOGIT_PARITY, DIRECT_P2P, DURABLE_REPLAY.

Trust: every sha256 / *_sha256 value must be listed in artifacts and in the
caller trusted_artifact_hashes set. Empty trust or empty artifacts is
NOT_CHECKED. This module does not authenticate arbitrary JSON.

Status: every requested claim proven => QUALIFIED and only those claims.
Any missing or unverified requested claim => NOT_CHECKED and no qualified
claims. Any malformed, contradictory, or known-false claim => REFUSED and
no qualified claims. Empty claims => NOT_CHECKED.
"""
import math
import re
from datetime import datetime, timezone

CLAIMS = (
    'TWO_VENDOR_NUMERICAL', 'FOUR_PHYSICAL_GPU', 'DEDICATED_CAPACITY_GT_ONE_CARD',
    'FOUR_REQUIRED_CAPACITY', 'LLM_LOGIT_PARITY', 'DIRECT_P2P', 'DURABLE_REPLAY',
)
BIND_KEYS = ('model_sha256', 'workload_sha256', 'build_sha256', 'executable_sha256')
_PCI = re.compile(r'^([0-9a-fA-F]{4}|[0-9a-fA-F]{8}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])$')
_SHA = re.compile(r'^[0-9a-f]{64}$')
_BAD_P2P = ('HOST_STAGED', 'D3D12', 'LEVEL_ZERO', 'SYSTEM_HEAP', 'D3D12_SYSTEM_HEAP')
_UNKNOWN_STATE = ('UNKNOWN', 'IN_FLIGHT', 'UNKNOWN_INTERRUPTED')


def validate_result(receipt, *, now_utc, max_age_seconds=10, trusted_artifact_hashes=frozenset()):
    if not isinstance(receipt, dict) or receipt.get('schema') != 1:
        return _out('REFUSED', ['INVALID_SCHEMA'])
    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() is None:
        return _out('REFUSED', ['INVALID_NOW'])
    if not _is_int(max_age_seconds) or max_age_seconds < 0:
        return _out('REFUSED', ['INVALID_MAX_AGE'])
    now = now_utc.astimezone(timezone.utc)
    claims = receipt.get('claims')
    if not isinstance(claims, list):
        return _out('REFUSED', ['INVALID_SCHEMA'])
    if len(claims) == 0:
        return _out('NOT_CHECKED', ['EMPTY_CLAIMS'])
    if any(not isinstance(c, str) or not c for c in claims) or len(set(claims)) != len(claims):
        return _out('REFUSED', ['INVALID_SCHEMA'])
    ts = _parse_time(receipt.get('timestamp'))
    if ts is None:
        return _out('REFUSED', ['INVALID_TIMESTAMP'])
    if not _fresh(ts, now, max_age_seconds):
        return _out('NOT_CHECKED', ['STALE_OR_FUTURE_TIMESTAMP'])
    trusted = trusted_artifact_hashes
    if not isinstance(trusted, (set, frozenset)) or any(not isinstance(h, str) for h in trusted):
        return _out('REFUSED', ['INVALID_TRUST_SET'])
    arts = receipt.get('artifacts')
    if not isinstance(arts, list) or len(arts) == 0 or len(trusted) == 0:
        return _out('NOT_CHECKED', ['UNTRUSTED_OR_MISSING_ARTIFACTS'])
    listed = []
    for art in arts:
        if not isinstance(art, dict) or not _is_sha(art.get('sha256')):
            return _out('REFUSED', ['MALFORMED_ARTIFACT_HASH'])
        if art['sha256'] not in trusted:
            return _out('NOT_CHECKED', ['UNTRUSTED_OR_MISSING_ARTIFACTS'])
        listed.append(art['sha256'])
    if len(set(listed)) != len(listed):
        return _out('REFUSED', ['DUPLICATE_ARTIFACT'])
    listed_set = set(listed)
    found = []
    _collect_shas(receipt, found)
    for h in found:
        if not _is_sha(h):
            return _out('REFUSED', ['MALFORMED_ARTIFACT_HASH'])
        if h not in trusted or h not in listed_set:
            return _out('NOT_CHECKED', ['UNTRUSTED_OR_MISSING_ARTIFACTS'])
    bindings = receipt.get('bindings')
    if not isinstance(bindings, dict) or any(not _is_sha(bindings.get(k)) for k in BIND_KEYS):
        return _out('REFUSED', ['INVALID_BINDINGS'])
    controls = receipt.get('controls', [])
    if not isinstance(controls, list) or any(not isinstance(c, dict) for c in controls):
        return _out('REFUSED', ['INVALID_SCHEMA'])
    devs, err = _devices(receipt.get('devices', []), now, max_age_seconds)
    if err:
        return _out(err[0], [err[1]])
    reasons, refused, unchecked, ok = [], False, False, []
    for name in claims:
        if name not in CLAIMS:
            st, reason = 'NOT_CHECKED', 'UNKNOWN_CLAIM'
        else:
            st, reason = _claim(name, receipt, bindings, devs, controls)
        if st == 'REFUSED':
            refused = True
        elif st == 'NOT_CHECKED':
            unchecked = True
        else:
            ok.append(name)
        if reason and st != 'QUALIFIED':
            reasons.append(reason)
    if refused:
        return _out('REFUSED', reasons)
    if unchecked:
        return _out('NOT_CHECKED', reasons)
    return _out('QUALIFIED', [], ok)


def _claim(name, receipt, bindings, devs, controls):
    if name == 'TWO_VENDOR_NUMERICAL':
        return _two(receipt, bindings, devs, controls)
    if name == 'FOUR_PHYSICAL_GPU':
        return _four(devs)
    if name == 'DEDICATED_CAPACITY_GT_ONE_CARD':
        return _capacity(receipt, bindings, devs, False)
    if name == 'FOUR_REQUIRED_CAPACITY':
        return _capacity(receipt, bindings, devs, True)
    if name == 'LLM_LOGIT_PARITY':
        return _llm(receipt, bindings, controls)
    if name == 'DIRECT_P2P':
        return _p2p(receipt, devs)
    return _durable(receipt, bindings)


def _two(receipt, bindings, devs, controls):
    ev = receipt.get('numerical')
    if not isinstance(ev, dict):
        return 'NOT_CHECKED', 'VENDOR_LABELS_ONLY'
    st, reason = _numbers(ev, bindings, None)
    if st != 'QUALIFIED':
        return st, reason
    st, reason = _good_control(controls)
    if st != 'QUALIFIED':
        return st, reason
    parts = _parts(devs, ev.get('physical_ids'))
    if parts is None:
        return 'NOT_CHECKED', 'MISSING_BINDING'
    if any(p['kernel'] is None for p in parts):
        return 'NOT_CHECKED', 'MISSING_KERNEL'
    if any(p['kernel']['completed'] is not True for p in parts):
        return 'REFUSED', 'KERNEL_NOT_COMPLETED'
    if len({p['vendor'] for p in parts}) < 2:
        return 'REFUSED', 'INSUFFICIENT_VENDORS'
    return 'QUALIFIED', None


def _four(devs):
    discs = [d for d in devs if d['device_class'] == 'DISCRETE_GPU' and d['memory'] and d['memory']['kind'] == 'DEDICATED']
    if len(discs) < 4:
        posed = any(d['device_class'] in ('CPU', 'IGPU') or (d['memory'] and d['memory']['kind'] == 'SHARED_HOST') for d in devs)
        if len(devs) >= 4 and posed:
            return 'REFUSED', 'NOT_DISCRETE_DEDICATED'
        return 'NOT_CHECKED', 'INSUFFICIENT_DISCRETE_GPUS'
    if any(d['kernel'] is None for d in discs):
        return 'NOT_CHECKED', 'MISSING_KERNEL'
    if any(d['kernel']['completed'] is not True for d in discs):
        return 'REFUSED', 'KERNEL_NOT_COMPLETED'
    if any(len(d['blocks']) != 1 for d in discs):
        return 'REFUSED', 'REPLICATION'
    ids, weights, owners = [], [], []
    for d in discs:
        b = d['blocks'][0]
        ids.append(b['block_id'])
        weights.append(b['weight_sha256'])
        owners.append(b['owner'])
    if len(ids) != len(set(ids)) or len(set(weights)) != len(discs):
        return 'REFUSED', 'REPLICATION'
    if set(owners) != {d['physical_id'] for d in discs}:
        return 'REFUSED', 'REPLICATION'
    return 'QUALIFIED', None


def _capacity(receipt, bindings, devs, need_three):
    cap = receipt.get('capacity')
    if not isinstance(cap, dict):
        return 'NOT_CHECKED', 'CAPACITY_NOT_MEASURED'
    if cap.get('source') == 'POLICY' or cap.get('failure_kind') == 'POLICY':
        return 'REFUSED', 'POLICY_NOT_CAPACITY'
    single = cap.get('single') if isinstance(cap.get('single'), dict) else None
    three = cap.get('three') if isinstance(cap.get('three'), dict) else None
    if (single and single.get('failure_kind') == 'POLICY') or (three and three.get('failure_kind') == 'POLICY'):
        return 'REFUSED', 'POLICY_NOT_CAPACITY'
    st, reason = _require_binds(cap, bindings)
    if st != 'QUALIFIED':
        return st, reason
    if not _is_sha(cap.get('quant_sha256')):
        return 'NOT_CHECKED', 'MISSING_BINDING'
    if not _is_int(cap.get('context')) or not _is_int(cap.get('batch')) or cap['context'] <= 0 or cap['batch'] <= 0:
        return 'REFUSED', 'INVALID_SCHEMA'
    if not _is_int(cap.get('requirement_bytes')) or cap['requirement_bytes'] < 0:
        return 'REFUSED', 'INVALID_MEM_TYPES'
    discs = [d for d in devs if d['device_class'] == 'DISCRETE_GPU' and d['memory'] and d['memory']['kind'] == 'DEDICATED' and d['memory']['source'] == 'ACTUAL_ALLOCATOR']
    if len(discs) < 2:
        return 'NOT_CHECKED', 'CAPACITY_NOT_MEASURED'
    largest = max(d['memory']['usable_bytes'] for d in discs)
    req = cap['requirement_bytes']
    if req <= largest:
        return 'REFUSED', 'SINGLE_CARD_FITS'
    plans = cap.get('plans')
    if not isinstance(plans, list) or not plans:
        return 'NOT_CHECKED', 'CAPACITY_NOT_MEASURED'
    mem = {d['physical_id']: d for d in discs}
    total = 0
    seen = set()
    for plan in plans:
        if not isinstance(plan, dict) or plan.get('physical_id') not in mem or not _is_int(plan.get('assigned_bytes')):
            return 'NOT_CHECKED', 'CAPACITY_NOT_MEASURED'
        if plan['assigned_bytes'] < 0 or plan['assigned_bytes'] > mem[plan['physical_id']]['memory']['usable_bytes']:
            return 'REFUSED', 'PER_DEVICE_FIT_FAIL'
        if plan['physical_id'] in seen:
            return 'REFUSED', 'PER_DEVICE_FIT_FAIL'
        seen.add(plan['physical_id'])
        total += plan['assigned_bytes']
    if total < req or len(seen) < 2:
        return 'REFUSED', 'PER_DEVICE_FIT_FAIL'
    st, reason = _oom(single, cap, bindings, devs, 1, 'MISSING_SINGLE_OOM')
    if st != 'QUALIFIED':
        return st, reason
    if need_three:
        return _oom(three, cap, bindings, devs, 3, 'MISSING_THREE_OOM')
    return 'QUALIFIED', None


def _oom(block, cap, bindings, devs, n, missing):
    if not isinstance(block, dict):
        return 'NOT_CHECKED', missing
    kind = block.get('failure_kind')
    if kind == 'POLICY':
        return 'REFUSED', 'POLICY_NOT_CAPACITY'
    if kind != 'ACTUAL_ALLOCATOR_OOM':
        return 'REFUSED', 'OOM_KIND_NOT_ALLOCATOR'
    if not _is_int(block.get('device_count')) or block['device_count'] != n:
        return 'REFUSED', 'OOM_KIND_NOT_ALLOCATOR'
    known = {d['physical_id'] for d in devs if d['device_class'] == 'DISCRETE_GPU' and d['memory'] and d['memory']['kind'] == 'DEDICATED'}
    ids = block.get('physical_ids')
    if not isinstance(ids, list) or len(ids) != n or len(set(ids)) != n or any(i not in known for i in ids):
        return 'NOT_CHECKED', 'MISSING_BINDING'
    st, reason = _require_binds(block, bindings)
    if st != 'QUALIFIED':
        return st, reason
    if block.get('quant_sha256') != cap['quant_sha256'] or block.get('context') != cap['context'] or block.get('batch') != cap['batch']:
        return 'REFUSED', 'BINDING_MISMATCH'
    if not _is_sha(block.get('artifact_sha256')):
        return 'NOT_CHECKED', missing
    return 'QUALIFIED', None


def _llm(receipt, bindings, controls):
    ev = receipt.get('llm')
    if not isinstance(ev, dict):
        return 'NOT_CHECKED', 'LLM_MISSING_GGUF'
    if ev.get('prose') is True or ev.get('type') == 'TEXT_PROSE':
        return 'REFUSED', 'LLM_PROSE'
    if ev.get('observed_failure') is True:
        return 'REFUSED', 'LLM_FAILED_PARITY'
    if ev.get('licensed') is not True or not _is_sha(ev.get('gguf_sha256')):
        return 'NOT_CHECKED', 'LLM_MISSING_GGUF'
    ops = (ev.get('attention_ops'), ev.get('kv_ops'))
    if any(not isinstance(xs, list) or not xs or any(not isinstance(x, str) or not x for x in xs) for xs in ops):
        return 'NOT_CHECKED', 'LLM_MISSING_GGUF'
    if not _is_int(ev.get('vocab')) or ev['vocab'] <= 0:
        return 'REFUSED', 'INVALID_SCHEMA'
    st, reason = _numbers(ev, bindings, ev['vocab'])
    if st != 'QUALIFIED':
        return st, reason
    return _good_control(controls)


def _p2p(receipt, devs):
    ev = receipt.get('p2p')
    if not isinstance(ev, dict) or not isinstance(ev.get('pairs'), list) or not ev['pairs']:
        return 'NOT_CHECKED', 'P2P_MISSING_INSTRUMENT'
    known = {d['physical_id'] for d in devs}
    for pair in ev['pairs']:
        if not isinstance(pair, dict):
            return 'REFUSED', 'INVALID_SCHEMA'
        prim = pair.get('primitive')
        if prim in _BAD_P2P:
            return 'REFUSED', 'P2P_NOT_DIRECT'
        if prim != 'DIRECT_DEVICE':
            return 'NOT_CHECKED', 'P2P_MISSING_INSTRUMENT'
        if 'parity_max_abs' not in pair or 'parity_violation_count' not in pair or 'artifact_sha256' not in pair:
            return 'NOT_CHECKED', 'P2P_LABEL_ONLY'
        if not _finite(pair.get('parity_max_abs')) or pair['parity_max_abs'] < 0:
            return 'REFUSED', 'NON_FINITE_METRIC'
        if not _is_int(pair.get('parity_violation_count')) or pair['parity_violation_count'] != 0:
            return 'REFUSED', 'NUMERICAL_TOLERANCE_EXCEEDED'
        src, dst = pair.get('src'), pair.get('dst')
        if src not in known or dst not in known or src == dst:
            return 'NOT_CHECKED', 'MISSING_BINDING'
        if not _is_sha(pair.get('artifact_sha256')):
            return 'REFUSED', 'MALFORMED_ARTIFACT_HASH'
    return 'QUALIFIED', None


def _durable(receipt, bindings):
    ev = receipt.get('durable')
    if not isinstance(ev, dict):
        return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
    if ev.get('method') in ('ATOMIC_JSON_WRITE_ONLY', 'ATOMIC_JSON'):
        return 'REFUSED', 'DURABLE_ATOMIC_ONLY'
    if ev.get('in_flight') is True and ev.get('state') == 'COMPLETE':
        return 'REFUSED', 'DURABLE_IN_FLIGHT'
    if ev.get('in_flight') is True or ev.get('state') in _UNKNOWN_STATE:
        return 'NOT_CHECKED', 'DURABLE_IN_FLIGHT'
    if ev.get('state') != 'COMPLETE':
        return 'NOT_CHECKED', 'DURABLE_IN_FLIGHT'
    if not isinstance(ev.get('checkpoint_identity'), str) or not ev['checkpoint_identity']:
        return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
    if not _is_int(ev.get('commit_sequence')) or not _is_int(ev.get('replay_boundary')):
        return 'REFUSED', 'INVALID_SCHEMA'
    if ev['commit_sequence'] < 0 or ev['replay_boundary'] < 0:
        return 'REFUSED', 'INVALID_SCHEMA'
    st, reason = _require_binds(ev, bindings)
    if st != 'QUALIFIED':
        return st, reason
    events = ev.get('events')
    if not isinstance(events, list):
        return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
    kinds = set()
    for event in events:
        if not isinstance(event, dict) or event.get('kind') not in ('WORKER_LOSS', 'CANCEL', 'RESTART'):
            return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
        if not _is_sha(event.get('artifact_sha256')):
            return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
        kinds.add(event['kind'])
    if kinds != {'WORKER_LOSS', 'CANCEL', 'RESTART'} and not {'WORKER_LOSS', 'CANCEL', 'RESTART'} <= kinds:
        return 'NOT_CHECKED', 'DURABLE_MISSING_EVENTS'
    return 'QUALIFIED', None


def _numbers(ev, bindings, expected):
    keys = ('full_count', 'finite_count', 'violation_count', 'rmse', 'max_abs_error', 'atol', 'rtol', 'array_sha256', 'reference_sha256')
    if any(k not in ev for k in keys):
        alt = ('array_sha256', 'reference_sha256', 'calculated_logit_hash', 'reference_logit_hash')
        return 'NOT_CHECKED', 'HASH_ONLY_NUMERICAL' if any(k in ev for k in alt) else 'MISSING_NUMERICAL_EVIDENCE'
    if not _is_sha(ev['array_sha256']) or not _is_sha(ev['reference_sha256']):
        return 'REFUSED', 'MALFORMED_ARTIFACT_HASH'
    if not all(_is_int(ev[k]) for k in ('full_count', 'finite_count', 'violation_count')):
        return 'REFUSED', 'INVALID_SCHEMA'
    for k in ('rmse', 'max_abs_error', 'atol', 'rtol'):
        if not _finite(ev[k]) or ev[k] < 0:
            return 'REFUSED', 'NON_FINITE_METRIC'
    if 'predeclared_atol' in ev or 'predeclared_rtol' in ev:
        if not _finite(ev.get('predeclared_atol')) or not _finite(ev.get('predeclared_rtol')):
            return 'REFUSED', 'NON_FINITE_METRIC'
        if ev['atol'] > ev['predeclared_atol'] or ev['rtol'] > ev['predeclared_rtol']:
            return 'REFUSED', 'TOLERANCE_LOOSENED'
    if ev['full_count'] <= 0 or ev['finite_count'] != ev['full_count'] or ev['violation_count'] != 0:
        return 'REFUSED', 'NUMERICAL_TOLERANCE_EXCEEDED'
    if expected is not None and ev['full_count'] != expected:
        return 'REFUSED', 'NUMERICAL_TOLERANCE_EXCEEDED'
    if ev['max_abs_error'] > ev['atol'] or ev['rmse'] > ev['atol']:
        return 'REFUSED', 'NUMERICAL_TOLERANCE_EXCEEDED'
    return _require_binds(ev, bindings)


def _good_control(controls):
    found = False
    for c in controls:
        if c.get('scope') == 'TRANSPORT' or c.get('transport_negative') is True:
            return 'REFUSED', 'CONTROL_SCOPE_INVALID'
        if c.get('kind') != 'COMPARATOR_ONLY':
            continue
        ok = _is_int(c.get('exit_code')) and c['exit_code'] == 1 and c.get('detected') is True
        ok = ok and c.get('scope') == 'COMPARE_ONLY' and _is_sha(c.get('artifact_sha256'))
        if not ok:
            return 'REFUSED', 'CONTROL_SCOPE_INVALID'
        found = True
    if not found:
        return 'NOT_CHECKED', 'MISSING_CONTROL'
    return 'QUALIFIED', None


def _devices(raw, now, max_age):
    if not isinstance(raw, list):
        return None, ('REFUSED', 'INVALID_SCHEMA')
    out, seen, phys = [], set(), set()
    for d in raw:
        if not isinstance(d, dict):
            return None, ('REFUSED', 'INVALID_SCHEMA')
        pci = _canon_pci(d.get('pci_id'))
        if pci is None:
            return None, ('REFUSED', 'MALFORMED_PCI')
        if pci in seen:
            return None, ('REFUSED', 'DUPLICATE_PCI')
        seen.add(pci)
        pid = d.get('physical_id')
        if not isinstance(pid, str) or not pid or pid in phys:
            return None, ('REFUSED', 'INVALID_PHYSICAL_ID')
        phys.add(pid)
        if d.get('device_class') not in ('DISCRETE_GPU', 'IGPU', 'CPU', 'OTHER') or not isinstance(d.get('vendor'), str) or not d['vendor']:
            return None, ('REFUSED', 'INVALID_DEVICE_CLASS')
        memory = None
        if 'memory' in d:
            memory, err = _memory(d['memory'], now, max_age)
            if err:
                return None, err
        kernel = None
        if 'kernel' in d:
            kernel = d['kernel']
            if not isinstance(kernel, dict) or not isinstance(kernel.get('completed'), bool) or not _is_sha(kernel.get('tensor_sha256')):
                return None, ('REFUSED', 'INVALID_KERNEL')
        blocks = d.get('blocks', [])
        if not isinstance(blocks, list):
            return None, ('REFUSED', 'INVALID_SCHEMA')
        parsed = []
        bids = set()
        for b in blocks:
            if not isinstance(b, dict):
                return None, ('REFUSED', 'INVALID_SCHEMA')
            bid = b.get('block_id')
            if not isinstance(bid, str) or not bid.strip() or bid in bids:
                return None, ('REFUSED', 'MISSING_BLOCK')
            if not _is_sha(b.get('weight_sha256')) or b.get('owner') != pid:
                return None, ('REFUSED', 'BINDING_MISMATCH')
            bids.add(bid)
            parsed.append(b)
        out.append({'pci': pci, 'physical_id': pid, 'vendor': d['vendor'], 'device_class': d['device_class'], 'memory': memory, 'kernel': kernel, 'blocks': parsed})
    return out, None


def _memory(mem, now, max_age):
    if not isinstance(mem, dict) or mem.get('kind') not in ('DEDICATED', 'SHARED_HOST', 'UNKNOWN'):
        return None, ('REFUSED', 'INVALID_MEM_TYPES')
    if mem.get('source') not in ('ACTUAL_ALLOCATOR', 'DRIVER_ADVERTISED', 'UNKNOWN'):
        return None, ('REFUSED', 'INVALID_MEM_TYPES')
    keys = ('total_bytes', 'free_bytes', 'reserve_bytes', 'highwater_bytes', 'usable_bytes')
    vals = [mem.get(k) for k in keys]
    if not all(_is_int(v) and v >= 0 for v in vals):
        return None, ('REFUSED', 'INVALID_MEM_TYPES')
    total, free, reserve, high, usable = vals
    if free > total or reserve > total or usable > total or high > usable or usable + reserve > total:
        return None, ('REFUSED', 'INVALID_MEM_RANGE')
    mt = _parse_time(mem.get('measured_at'))
    if mt is None:
        return None, ('REFUSED', 'INVALID_TIMESTAMP')
    if not _fresh(mt, now, max_age):
        return None, ('NOT_CHECKED', 'STALE_OR_FUTURE_TIMESTAMP')
    mem = {'kind': mem['kind'], 'source': mem['source'], 'total_bytes': total, 'free_bytes': free, 'reserve_bytes': reserve, 'highwater_bytes': high, 'usable_bytes': usable}
    return mem, None


def _parts(devs, ids):
    if not isinstance(ids, list) or not ids:
        return None
    by = {d['physical_id']: d for d in devs}
    if any(not isinstance(i, str) or i not in by for i in ids) or len(set(ids)) != len(ids):
        return None
    return [by[i] for i in ids]


def _require_binds(ev, bindings):
    for k in BIND_KEYS:
        if k not in ev:
            return 'NOT_CHECKED', 'MISSING_BINDING'
        if ev[k] != bindings[k]:
            return 'REFUSED', 'BINDING_MISMATCH'
    return 'QUALIFIED', None


def _collect_shas(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'sha256' or k.endswith('_sha256'):
                out.append(v)
            else:
                _collect_shas(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_shas(item, out)


def _canon_pci(s):
    if not isinstance(s, str):
        return None
    m = _PCI.match(s)
    if not m:
        return None
    dom, bus, dev, fn = m.groups()
    di, dv = int(dom, 16), int(dev, 16)
    if di > 0xffff or dv > 0x1f:
        return None
    return f'{di:04x}:{int(bus, 16):02x}:{dv:02x}.{int(fn, 16):x}'


def _parse_time(v):
    if not isinstance(v, str) or not v:
        return None
    s = v[:-1] + '+00:00' if v.endswith('Z') else v
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt.astimezone(timezone.utc)


def _fresh(dt, now, max_age):
    age = (now - dt).total_seconds()
    return age >= 0 and age <= max_age


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_sha(v):
    return isinstance(v, str) and _SHA.fullmatch(v) is not None


def _finite(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return False
    return True


def _out(status, reasons, claims=None):
    return {'status': status, 'reasons': sorted(set(reasons)), 'qualified_claims': sorted(claims or [])}
