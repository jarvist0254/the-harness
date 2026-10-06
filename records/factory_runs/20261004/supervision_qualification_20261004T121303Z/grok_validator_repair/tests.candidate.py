import unittest
from datetime import datetime, timedelta, timezone
from qualification_validator import validate_result

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
BINDS = {'model_sha256': 'aa' * 32, 'workload_sha256': 'bb' * 32, 'build_sha256': 'cc' * 32, 'executable_sha256': 'dd' * 32}

def S(tag):
    return (tag * 32)[:64]

def tags(*extra):
    return ['aa', 'bb', 'cc', 'dd', *extra]

def receipt(claims, devices=None, fields=None, extra=(), timestamp=None):
    hs = [S(t) for t in tags(*extra)]
    body = {
        'schema': 1,
        'timestamp': (timestamp or NOW).isoformat(),
        'artifacts': [{'sha256': h, 'role': 'evidence'} for h in hs],
        'bindings': dict(BINDS),
        'devices': [] if devices is None else devices,
        'claims': claims,
    }
    if fields:
        body.update(fields)
    return body, frozenset(hs)

def memory(kind='DEDICATED', usable=6000000000, total=8000000000, source='ACTUAL_ALLOCATOR'):
    return {
        'kind': kind, 'total_bytes': total, 'free_bytes': usable, 'reserve_bytes': total - usable,
        'highwater_bytes': 1024, 'usable_bytes': usable, 'source': source, 'measured_at': NOW.isoformat(),
    }

def device(i, vendor='NVIDIA', cls='DISCRETE_GPU', kind='DEDICATED', weight='55', tensor='11', usable=6000000000, kernel=True, block=True):
    pid = f'p{i}'
    d = {'pci_id': f'0000:0{i}:00.0', 'physical_id': pid, 'vendor': vendor, 'device_class': cls, 'memory': memory(kind, usable)}
    if kernel:
        d['kernel'] = {'completed': True, 'tensor_sha256': S(tensor)}
    if block:
        d['blocks'] = [{'block_id': f'blk-{pid}', 'weight_sha256': S(weight), 'owner': pid}]
    return d

def numbers(ids, **over):
    ev = dict(BINDS)
    ev.update({'array_sha256': S('ee'), 'reference_sha256': S('ff'), 'full_count': 8, 'finite_count': 8,
               'violation_count': 0, 'rmse': 8.3e-6, 'max_abs_error': 8.3e-6, 'atol': 5e-5, 'rtol': 5e-5,
               'physical_ids': ids})
    ev.update(over)
    return ev

def controls(scope='COMPARE_ONLY'):
    return [{'kind': 'COMPARATOR_ONLY', 'exit_code': 1, 'detected': True, 'scope': scope, 'artifact_sha256': S('00')}]

def four_devices():
    spec = [(1, 'NVIDIA', '11', '55'), (2, 'AMD', '22', '66'), (3, 'NVIDIA', '33', '77'), (4, 'AMD', '44', '88')]
    return [device(i, vendor=v, tensor=t, weight=w) for i, v, t, w in spec]

def capacity():
    cap = dict(BINDS)
    cap.update({
        'quant_sha256': S('fa'), 'context': 2048, 'batch': 1, 'requirement_bytes': 8000000000,
        'source': 'ACTUAL_ALLOCATOR',
        'plans': [{'physical_id': f'p{i}', 'assigned_bytes': 2000000000} for i in (1, 2, 3, 4)],
        'single': dict(BINDS, quant_sha256=S('fa'), context=2048, batch=1, device_count=1,
                       failure_kind='ACTUAL_ALLOCATOR_OOM', physical_ids=['p1'], artifact_sha256=S('99')),
        'three': dict(BINDS, quant_sha256=S('fa'), context=2048, batch=1, device_count=3,
                      failure_kind='ACTUAL_ALLOCATOR_OOM', physical_ids=['p1', 'p2', 'p3'], artifact_sha256=S('ab')),
    })
    return cap

def run(claims, devices=None, fields=None, extra=(), **kw):
    body, trust = receipt(claims, devices, fields, extra, kw.get('timestamp'))
    if 'trust' in kw:
        trust = kw['trust']
    return validate_result(body, now_utc=kw.get('now', NOW), max_age_seconds=kw.get('max_age', 10), trusted_artifact_hashes=trust)

class TestQualificationValidator(unittest.TestCase):
    def test_empty_claims_not_checked(self):
        res = run([])
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertEqual(res['qualified_claims'], [])
        self.assertIn('EMPTY_CLAIMS', res['reasons'])

    def test_empty_trust_and_empty_artifacts(self):
        body, _ = receipt(['TWO_VENDOR_NUMERICAL'], [])
        res = validate_result(body, now_utc=NOW, trusted_artifact_hashes=frozenset())
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('UNTRUSTED_OR_MISSING_ARTIFACTS', res['reasons'])
        body['artifacts'] = []
        res = validate_result(body, now_utc=NOW, trusted_artifact_hashes=frozenset([S('aa')]))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertEqual(res['qualified_claims'], [])

    def test_bool_nan_inf_negative_memory_and_metrics(self):
        dev = device(1)
        dev['memory']['total_bytes'] = True
        dev['memory']['free_bytes'] = False
        res = run(['FOUR_PHYSICAL_GPU'], [dev])
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('INVALID_MEM_TYPES', res['reasons'])
        dev = device(1)
        dev['memory']['free_bytes'] = -1
        res = run(['FOUR_PHYSICAL_GPU'], [dev])
        self.assertIn('INVALID_MEM_TYPES', res['reasons'])
        devs = [device(1, tensor='11'), device(2, vendor='AMD', tensor='22', weight='66')]
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': numbers(['p1', 'p2'], max_abs_error=float('nan')), 'controls': controls()}, ('ee', 'ff', '00', '11', '22'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('NON_FINITE_METRIC', res['reasons'])
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': numbers(['p1', 'p2'], rmse=float('inf')), 'controls': controls()}, ('ee', 'ff', '00', '11', '22'))
        self.assertIn('NON_FINITE_METRIC', res['reasons'])
        self.assertNotIn('TWO_VENDOR_NUMERICAL', res['qualified_claims'])

    def test_timestamps_future_stale_naive(self):
        future = NOW + timedelta(seconds=30)
        res = run(['TWO_VENDOR_NUMERICAL'], timestamp=future)
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('STALE_OR_FUTURE_TIMESTAMP', res['reasons'])
        res = run(['TWO_VENDOR_NUMERICAL'], timestamp=NOW - timedelta(seconds=30))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        body, trust = receipt(['TWO_VENDOR_NUMERICAL'])
        body['timestamp'] = '2026-10-04T12:00:00'
        res = validate_result(body, now_utc=NOW, trusted_artifact_hashes=trust)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('INVALID_TIMESTAMP', res['reasons'])

    def test_pci_alias_range_and_missing_domain(self):
        a = device(1)
        b = device(2)
        b['pci_id'] = '00000000:01:00.0'
        b['physical_id'] = 'p9'
        res = run(['FOUR_PHYSICAL_GPU'], [a, b])
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('DUPLICATE_PCI', res['reasons'])
        bad = device(1)
        bad['pci_id'] = '01:00.0'
        self.assertIn('MALFORMED_PCI', run(['FOUR_PHYSICAL_GPU'], [bad])['reasons'])
        bad['pci_id'] = '0000:01:20.0'
        self.assertIn('MALFORMED_PCI', run(['FOUR_PHYSICAL_GPU'], [bad])['reasons'])
        bad['pci_id'] = '0000:01:00.8'
        self.assertIn('MALFORMED_PCI', run(['FOUR_PHYSICAL_GPU'], [bad])['reasons'])
        ok = device(1)
        ok['pci_id'] = '0000:01:00.0'
        res = run(['TWO_VENDOR_NUMERICAL'], [ok, device(2, vendor='AMD', tensor='22', weight='66')],
                  {'numerical': numbers(['p1', 'p2']), 'controls': controls()}, ('ee', 'ff', '00', '11', '22', '55', '66'))
        self.assertNotIn('MALFORMED_PCI', res['reasons'])

    def test_vendor_labels_hash_only_and_missing_control(self):
        devs = [device(1, tensor='11'), device(2, vendor='AMD', kind='SHARED_HOST', tensor='22', weight='66')]
        res = run(['TWO_VENDOR_NUMERICAL'], devs)
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('VENDOR_LABELS_ONLY', res['reasons'])
        self.assertNotIn('TWO_VENDOR_NUMERICAL', res['qualified_claims'])
        ev = {'reference_logit_hash': S('ff'), 'calculated_logit_hash': S('ff'), 'type': 'NUMERICAL_ARRAY'}
        res = run(['LLM_LOGIT_PARITY'], devs, {'llm': ev})
        self.assertNotEqual(res['status'], 'QUALIFIED')
        self.assertEqual(res['qualified_claims'], [])
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': numbers(['p1', 'p2'])}, ('ee', 'ff', '11', '22', '55', '66'))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('MISSING_CONTROL', res['reasons'])

    def test_valid_partial_two_vendor_shared_amd_only(self):
        devs = [device(1, tensor='11', weight='55'), device(2, vendor='AMD', kind='SHARED_HOST', tensor='22', weight='66')]
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': numbers(['p1', 'p2']), 'controls': controls()},
                  ('ee', 'ff', '00', '11', '22', '55', '66'))
        self.assertEqual(res['status'], 'QUALIFIED')
        self.assertEqual(res['qualified_claims'], ['TWO_VENDOR_NUMERICAL'])

    def test_cpu_shared_replication_and_count_are_not_capacity(self):
        cpus = [device(i, cls='CPU', vendor='INTEL', tensor=t, weight=w) for i, t, w in ((1, '11', '55'), (2, '22', '66'), (3, '33', '77'), (4, '44', '88'))]
        res = run(['FOUR_PHYSICAL_GPU'], cpus, extra=('11', '22', '33', '44', '55', '66', '77', '88'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('NOT_DISCRETE_DEDICATED', res['reasons'])
        shared = [device(i, kind='SHARED_HOST', vendor='AMD', tensor=t, weight=w) for i, t, w in ((1, '11', '55'), (2, '22', '66'), (3, '33', '77'), (4, '44', '88'))]
        res = run(['FOUR_PHYSICAL_GPU', 'DEDICATED_CAPACITY_GT_ONE_CARD'], shared, extra=('11', '22', '33', '44', '55', '66', '77', '88'))
        self.assertEqual(res['status'], 'REFUSED')
        reps = [device(i, tensor=t, weight='55') for i, t in ((1, '11'), (2, '22'), (3, '33'), (4, '44'))]
        res = run(['FOUR_PHYSICAL_GPU'], reps, extra=('11', '22', '33', '44', '55'))
        self.assertIn('REPLICATION', res['reasons'])
        res = run(['DEDICATED_CAPACITY_GT_ONE_CARD', 'FOUR_REQUIRED_CAPACITY'], four_devices(),
                  extra=('11', '22', '33', '44', '55', '66', '77', '88'))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertEqual(res['qualified_claims'], [])
        self.assertIn('CAPACITY_NOT_MEASURED', res['reasons'])

    def test_single_fits_and_policy_oom_refused(self):
        cap = capacity()
        cap['requirement_bytes'] = 1000000
        res = run(['DEDICATED_CAPACITY_GT_ONE_CARD'], four_devices(), {'capacity': cap},
                  ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99', 'ab'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('SINGLE_CARD_FITS', res['reasons'])
        cap = capacity()
        cap['three']['failure_kind'] = 'POLICY'
        res = run(['FOUR_REQUIRED_CAPACITY'], four_devices(), {'capacity': cap},
                  ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99', 'ab'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('POLICY_NOT_CAPACITY', res['reasons'])
        cap = capacity()
        cap['requirement_bytes'] = 32000000
        cap['source'] = 'POLICY'
        cap['plans'] = [{'physical_id': 'p1', 'assigned_bytes': 16000000}, {'physical_id': 'p2', 'assigned_bytes': 16000000}]
        res = run(['DEDICATED_CAPACITY_GT_ONE_CARD'], four_devices(), {'capacity': cap},
                  ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99', 'ab'))
        self.assertIn('POLICY_NOT_CAPACITY', res['reasons'])

    def test_binding_mismatches(self):
        devs = [device(1, tensor='11'), device(2, vendor='AMD', tensor='22', weight='66')]
        ev = numbers(['p1', 'p2'], model_sha256=S('ab'))
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': ev, 'controls': controls()}, ('ee', 'ff', '00', '11', '22', '55', '66', 'ab'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('BINDING_MISMATCH', res['reasons'])
        cap = capacity()
        cap['single']['workload_sha256'] = S('bc')
        res = run(['DEDICATED_CAPACITY_GT_ONE_CARD'], four_devices(), {'capacity': cap},
                  ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99', 'ab', 'bc'))
        self.assertIn('BINDING_MISMATCH', res['reasons'])
        owned = device(1)
        owned['blocks'][0]['owner'] = 'other'
        res = run(['FOUR_PHYSICAL_GPU'], [owned], extra=('11', '55'))
        self.assertIn('BINDING_MISMATCH', res['reasons'])

    def test_complete_capacity_qualifies_requested_only(self):
        extra = ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99', 'ab')
        fields = {'capacity': capacity()}
        devs = four_devices()
        res = run(['FOUR_PHYSICAL_GPU'], devs, fields, extra)
        self.assertEqual(res['status'], 'QUALIFIED')
        self.assertEqual(res['qualified_claims'], ['FOUR_PHYSICAL_GPU'])
        want = ['FOUR_PHYSICAL_GPU', 'DEDICATED_CAPACITY_GT_ONE_CARD', 'FOUR_REQUIRED_CAPACITY']
        res = run(want, devs, fields, extra)
        self.assertEqual(res['status'], 'QUALIFIED')
        self.assertEqual(res['qualified_claims'], sorted(want))
        self.assertNotIn('LLM_LOGIT_PARITY', res['qualified_claims'])
        self.assertNotIn('DIRECT_P2P', res['qualified_claims'])

    def test_four_required_without_three_oom(self):
        cap = capacity()
        del cap['three']
        res = run(['FOUR_REQUIRED_CAPACITY'], four_devices(), {'capacity': cap},
                  ('11', '22', '33', '44', '55', '66', '77', '88', 'fa', '99'))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('MISSING_THREE_OOM', res['reasons'])
        self.assertEqual(res['qualified_claims'], [])

    def test_llm_prose_failure_loosen_and_not_capacity(self):
        llm = dict(BINDS)
        llm.update({'gguf_sha256': S('ba'), 'licensed': True, 'attention_ops': ['softmax'], 'kv_ops': ['concat'],
                    'vocab': 32, 'full_count': 32, 'finite_count': 32, 'violation_count': 0, 'array_sha256': S('ee'),
                    'reference_sha256': S('ff'), 'rmse': 0.02, 'max_abs_error': 0.02, 'atol': 0.01, 'rtol': 0.01,
                    'predeclared_atol': 0.01, 'predeclared_rtol': 0.01, 'type': 'TEXT_PROSE'})
        res = run(['LLM_LOGIT_PARITY'], [device(1)], {'llm': llm, 'controls': controls()}, ('ee', 'ff', '00', '11', '55', 'ba'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('LLM_PROSE', res['reasons'])
        llm['type'] = 'NUMERICAL_ARRAY'
        res = run(['LLM_LOGIT_PARITY'], [device(1)], {'llm': llm, 'controls': controls()}, ('ee', 'ff', '00', '11', '55', 'ba'))
        self.assertIn('LLM_FAILED_PARITY', res['reasons']) if False else self.assertIn('NUMERICAL_TOLERANCE_EXCEEDED', res['reasons'])
        llm['max_abs_error'] = 0.001
        llm['rmse'] = 0.001
        llm['atol'] = 1.0
        llm['rtol'] = 1.0
        res = run(['LLM_LOGIT_PARITY', 'DEDICATED_CAPACITY_GT_ONE_CARD'], [device(1)], {'llm': llm, 'controls': controls()},
                  ('ee', 'ff', '00', '11', '55', 'ba'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('TOLERANCE_LOOSENED', res['reasons'])
        self.assertNotIn('DEDICATED_CAPACITY_GT_ONE_CARD', res['qualified_claims'])

    def test_p2p_unmeasured_label_and_host(self):
        devs = [device(1, tensor='11'), device(2, tensor='22', weight='66')]
        extra = ('11', '22', '55', '66')
        res = run(['DIRECT_P2P'], devs, extra=extra)
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('P2P_MISSING_INSTRUMENT', res['reasons'])
        res = run(['DIRECT_P2P'], devs, {'p2p': {'pairs': [{'src': 'p1', 'dst': 'p2', 'primitive': 'DIRECT_DEVICE'}]}}, extra)
        self.assertIn('P2P_LABEL_ONLY', res['reasons'])
        pair = {'src': 'p1', 'dst': 'p2', 'primitive': 'HOST_STAGED', 'parity_max_abs': 0.0, 'parity_violation_count': 0, 'artifact_sha256': S('ac')}
        res = run(['DIRECT_P2P'], devs, {'p2p': {'pairs': [pair]}}, extra + ('ac',))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('P2P_NOT_DIRECT', res['reasons'])

    def test_durable_atomic_unknown_and_inflight(self):
        ev = dict(BINDS)
        ev.update({'checkpoint_identity': 'cp', 'commit_sequence': 3, 'replay_boundary': 3, 'method': 'ATOMIC_JSON_WRITE_ONLY',
                   'state': 'COMPLETE', 'in_flight': False, 'events': [
                       {'kind': 'WORKER_LOSS', 'artifact_sha256': S('ad')}, {'kind': 'CANCEL', 'artifact_sha256': S('ae')},
                       {'kind': 'RESTART', 'artifact_sha256': S('af')}]})
        res = run(['DURABLE_REPLAY'], [], {'durable': ev}, ('ad', 'ae', 'af'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('DURABLE_ATOMIC_ONLY', res['reasons'])
        ev['method'] = 'CHECKPOINT_REPLAY'
        ev['state'] = 'UNKNOWN'
        res = run(['DURABLE_REPLAY'], [], {'durable': ev}, ('ad', 'ae', 'af'))
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('DURABLE_IN_FLIGHT', res['reasons'])
        self.assertEqual(res['qualified_claims'], [])
        ev['state'] = 'COMPLETE'
        ev['in_flight'] = True
        res = run(['DURABLE_REPLAY'], [], {'durable': ev}, ('ad', 'ae', 'af'))
        self.assertEqual(res['status'], 'REFUSED')

    def test_unknown_claim_and_transport_control(self):
        res = run(['NOT_A_CLAIM'])
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('UNKNOWN_CLAIM', res['reasons'])
        devs = [device(1, tensor='11'), device(2, vendor='AMD', tensor='22', weight='66')]
        res = run(['TWO_VENDOR_NUMERICAL'], devs, {'numerical': numbers(['p1', 'p2']), 'controls': controls('TRANSPORT')},
                  ('ee', 'ff', '00', '11', '22', '55', '66'))
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('CONTROL_SCOPE_INVALID', res['reasons'])

if __name__ == '__main__':
    unittest.main()

