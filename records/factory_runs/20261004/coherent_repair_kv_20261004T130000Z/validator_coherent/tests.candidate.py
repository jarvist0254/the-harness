import unittest
import hashlib
import copy
from datetime import datetime, timezone, timedelta

try:
    from qualification_validator import validate_result, CLAIMS, BIND_KEYS
except ImportError:
    import importlib.util, pathlib, sys
    _vpath = pathlib.Path(__file__).resolve().parent / 'qualification_validator.py'
    if not _vpath.exists():
        _vpath = pathlib.Path('qualification_validator.py')
    _spec = importlib.util.spec_from_file_location('qualification_validator', _vpath)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules['qualification_validator'] = _mod
    _spec.loader.exec_module(_mod)
    validate_result = _mod.validate_result
    CLAIMS = _mod.CLAIMS
    BIND_KEYS = _mod.BIND_KEYS

H = lambda s: hashlib.sha256(s.encode()).hexdigest()
NOW = datetime.now(timezone.utc)
TS = NOW.strftime('%Y-%m-%dT%H:%M:%S+00:00')
H_MODEL = H('model')
H_WORK = H('workload')
H_BUILD = H('build')
H_EXEC = H('exec')
H_QUANT = H('quant')
H_ARR = H('arr')
H_REF = H('ref')
H_TENS = [H(f'tensor{i}') for i in range(10)]
H_WGT = [H(f'weight{i}') for i in range(10)]
H_CTRL_ART = H('ctrl_art')
H_OOM_ART = H('oom_art')
H_P2P_ART = H('p2p_art')
H_DUR_ART = H('dur_art')
H_LLM_GGUF = H('gguf')

BINDS = {'model_sha256': H_MODEL, 'workload_sha256': H_WORK, 'build_sha256': H_BUILD, 'executable_sha256': H_EXEC}

def _gpu(idx, vendor='NVIDIA', usable=10**10, high=10**10, reserve=0, completed=True, blocks=None, source='ACTUAL_ALLOCATOR'):
    d = {
        'pci_id': f'0000:{idx:02x}:00.0',
        'physical_id': f'gpu{idx}',
        'vendor': vendor,
        'device_class': 'DISCRETE_GPU',
        'memory': {
            'kind': 'DEDICATED', 'source': source,
            'total_bytes': usable + reserve + 10**9,
            'free_bytes': usable - high + 10**9,
            'reserve_bytes': reserve, 'highwater_bytes': high,
            'usable_bytes': usable, 'measured_at': TS,
        },
        'kernel': {'completed': completed, 'tensor_sha256': H_TENS[idx]},
        'blocks': blocks or [{'block_id': f'b{idx}', 'weight_sha256': H_WGT[idx], 'owner': f'gpu{idx}'}],
    }
    return d

def _num_ev(ids, vocab=None, ref_scale=0.0):
    ev = dict(BINDS, physical_ids=ids, array_sha256=H_ARR, reference_sha256=H_REF,
              full_count=vocab or 100, finite_count=vocab or 100, violation_count=0,
              rmse=1e-6, max_abs_error=1e-6, atol=5e-5, rtol=5e-5,
              predeclared_atol=5e-5, predeclared_rtol=5e-5, reference_scale=ref_scale)
    return ev

def _ctrl(ids):
    return dict(BINDS, physical_ids=ids, kind='COMPARATOR_ONLY', scope='COMPARE_ONLY',
                exit_code=1, detected=True, artifact_sha256=H_CTRL_ART,
                quant_sha256=H_QUANT, context=2048)

def _base(claims, devs, **kw):
    r = {'schema': 1, 'timestamp': TS, 'claims': claims, 'devices': devs, 'bindings': dict(BINDS), 'controls': [], **kw}
    shas = []
    def collect(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and (k == 'sha256' or k.endswith('_sha256')):
                    if isinstance(v, str): shas.append(v)
                else: collect(v)
        elif isinstance(x, list):
            for v in x: collect(v)
    collect(r)
    trust = frozenset(shas)
    r['artifacts'] = [{'sha256': h} for h in sorted(trust)]
    return r, trust

class TestTwoVendorNumerical(unittest.TestCase):
    def test_positive_two_vendor_baseline(self):
        devs = [_gpu(1, 'AMD'), _gpu(2, 'NVIDIA')]
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=_num_ev(['gpu1','gpu2']), controls=[_ctrl(['gpu1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_cpu_participants_refused(self):
        devs = [{'pci_id':'0000:01:00.0','physical_id':'c1','vendor':'Intel','device_class':'CPU'}, _gpu(2,'AMD')]
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=_num_ev(['c1','gpu2']), controls=[_ctrl(['c1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('CPU_OR_OTHER_VENDOR', out['reasons'])

    def test_other_participants_refused(self):
        devs = [{'pci_id':'0000:01:00.0','physical_id':'o1','vendor':'X','device_class':'OTHER'}, _gpu(2,'AMD')]
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=_num_ev(['o1','gpu2']), controls=[_ctrl(['o1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

class TestFourPhysicalGPU(unittest.TestCase):
    def test_four_success(self):
        devs = [_gpu(i, 'AMD' if i%2 else 'NVIDIA') for i in range(1,5)]
        r, t = _base(['FOUR_PHYSICAL_GPU'], devs)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_three_devices_not_checked(self):
        devs = [_gpu(i) for i in range(1,4)]
        r, t = _base(['FOUR_PHYSICAL_GPU'], devs)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertNotEqual(out['status'], 'QUALIFIED')

    def test_alias_rejected(self):
        d = _gpu(1)
        devs = [copy.deepcopy(d) for _ in range(4)]
        for i, dd in enumerate(devs): dd['physical_id'] = f'g{i}'
        r, t = _base(['FOUR_PHYSICAL_GPU'], devs)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

class TestCapacity(unittest.TestCase):
    def _cap(self, n, assigned=2*10**9, usable=3*10**9, high=3*10**9, reserve=0, claim='DEDICATED_CAPACITY_GT_ONE_CARD'):
        devs = [_gpu(i, usable=usable, high=high, reserve=reserve) for i in range(1, n+1)]
        plans = [{'physical_id': f'gpu{i}', 'assigned_bytes': assigned} for i in range(1, n+1)]
        cap = dict(BINDS, source='ACTUAL_ALLOCATOR', quant_sha256=H_QUANT, context=2048, batch=1,
                   requirement_bytes=assigned*n - 1, plans=plans,
                   single=dict(BINDS, failure_kind='ACTUAL_ALLOCATOR_OOM', device_count=1, physical_ids=['gpu1'],
                               quant_sha256=H_QUANT, context=2048, batch=1, artifact_sha256=H_OOM_ART))
        if claim == 'FOUR_REQUIRED_CAPACITY':
            cap['three'] = dict(BINDS, failure_kind='ACTUAL_ALLOCATOR_OOM', device_count=3, physical_ids=['gpu1','gpu2','gpu3'],
                                quant_sha256=H_QUANT, context=2048, batch=1, artifact_sha256=H_OOM_ART)
        r, t = _base([claim], devs, capacity=cap)
        return r, t

    def test_dedicated_capacity_pass(self):
        r, t = self._cap(2)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_zero_highwater_refused(self):
        r, t = self._cap(2, high=0)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_four_required_exactly_three_devices_not_checked(self):
        r, t = self._cap(3, claim='FOUR_REQUIRED_CAPACITY')
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertNotEqual(out['status'], 'QUALIFIED')

    def test_four_required_pass(self):
        r, t = self._cap(4, claim='FOUR_REQUIRED_CAPACITY')
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_policy_oom_refused(self):
        r, t = self._cap(2)
        r['capacity']['single']['failure_kind'] = 'POLICY'
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_zero_assignment_refused(self):
        r, t = self._cap(2, assigned=0)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

class TestLLM(unittest.TestCase):
    def test_llm_without_gpu_refused(self):
        ev = dict(_num_ev([], vocab=8), gguf_sha256=H_LLM_GGUF, licensed=True,
                  attention_ops=['attn'], kv_ops=['kv'], vocab=8, type='NUMERICAL_ARRAY')
        r, t = _base(['LLM_LOGIT_PARITY'], [], llm=ev, controls=[_ctrl([])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('LLM_NO_GPU', out['reasons'])

    def test_llm_with_gpu_pass(self):
        devs = [_gpu(1)]
        ev = dict(_num_ev(['gpu1'], vocab=8), gguf_sha256=H_LLM_GGUF, licensed=True,
                  attention_ops=['attn'], kv_ops=['kv'], vocab=8, type='NUMERICAL_ARRAY')
        r, t = _base(['LLM_LOGIT_PARITY'], devs, llm=ev, controls=[_ctrl(['gpu1'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_observed_llm_failure_refused(self):
        devs = [_gpu(1)]
        ev = dict(_num_ev(['gpu1'], vocab=8), gguf_sha256=H_LLM_GGUF, licensed=True,
                  attention_ops=['attn'], kv_ops=['kv'], vocab=8, observed_failure=True)
        r, t = _base(['LLM_LOGIT_PARITY'], devs, llm=ev, controls=[_ctrl(['gpu1'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

class TestNumericalMetrics(unittest.TestCase):
    def test_declared_tolerance_metric_inconsistency(self):
        devs = [_gpu(1,'AMD'), _gpu(2,'NVIDIA')]
        ev = _num_ev(['gpu1','gpu2'])
        ev['rmse'] = 1e-4; ev['max_abs_error'] = 1e-6
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=ev, controls=[_ctrl(['gpu1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('RMSE_EXCEEDS_MAX_ABS', out['reasons'])

    def test_tolerance_loosening_refused(self):
        devs = [_gpu(1,'AMD'), _gpu(2,'NVIDIA')]
        ev = _num_ev(['gpu1','gpu2']); ev['atol'] = 1.0
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=ev, controls=[_ctrl(['gpu1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_missing_predeclared_refused(self):
        devs = [_gpu(1,'AMD'), _gpu(2,'NVIDIA')]
        ev = _num_ev(['gpu1','gpu2']); del ev['predeclared_atol']; del ev['predeclared_rtol']
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=ev, controls=[_ctrl(['gpu1','gpu2'])])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('MISSING_PREDECLARED_TOLERANCE', out['reasons'])

class TestControlBinding(unittest.TestCase):
    def test_unrelated_workload_control_refused(self):
        devs = [_gpu(1,'AMD'), _gpu(2,'NVIDIA')]
        c = _ctrl(['gpu1','gpu2']); c['model_sha256'] = H('other')
        r, t = _base(['TWO_VENDOR_NUMERICAL'], devs, numerical=_num_ev(['gpu1','gpu2']), controls=[c])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'NOT_CHECKED')

class TestP2P(unittest.TestCase):
    def test_p2p_host_staged_refused(self):
        devs = [_gpu(1), _gpu(2)]
        p2p = dict(BINDS, pairs=[{'primitive':'HOST_STAGED','src':'gpu1','dst':'gpu2','parity_max_abs':0.0,'parity_violation_count':0,'artifact_sha256':H_P2P_ART,'count_bytes':1024}])
        r, t = _base(['DIRECT_P2P'], devs, p2p=p2p)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_p2p_direct_pass(self):
        devs = [_gpu(1), _gpu(2)]
        p2p = dict(BINDS, pairs=[{'primitive':'DIRECT_DEVICE','src':'gpu1','dst':'gpu2','parity_max_abs':0.0,'parity_violation_count':0,'artifact_sha256':H_P2P_ART,'count_bytes':1024}])
        r, t = _base(['DIRECT_P2P'], devs, p2p=p2p)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

class TestDurable(unittest.TestCase):
    def test_atomic_json_refused(self):
        dur = dict(BINDS, method='ATOMIC_JSON', state='COMPLETE', checkpoint_identity='cp1', commit_sequence=1, replay_boundary=1, events=[])
        r, t = _base(['DURABLE_REPLAY'], [], durable=dur)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_durable_pass(self):
        evts = [{'kind':k, 'artifact_sha256':H_DUR_ART} for k in ('WORKER_LOSS','CANCEL','RESTART')]
        dur = dict(BINDS, method='JOURNAL', state='COMPLETE', checkpoint_identity='cp1', commit_sequence=3, replay_boundary=3, events=evts)
        r, t = _base(['DURABLE_REPLAY'], [], durable=dur)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'QUALIFIED')

class TestSchemaGuards(unittest.TestCase):
    def test_bool_schema_refused(self):
        r, t = _base(['FOUR_PHYSICAL_GPU'], [])
        r['schema'] = True
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'REFUSED')

    def test_empty_claims_not_checked(self):
        r, t = _base([], [])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=t)
        self.assertEqual(out['status'], 'NOT_CHECKED')

if __name__ == '__main__':
    unittest.main()

