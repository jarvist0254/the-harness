import unittest
from datetime import datetime, timezone, timedelta
from qualification_validator import validate_result

H = 'a' * 64
H2 = 'b' * 64
H3 = 'c' * 64
H4 = 'd' * 64
H5 = 'e' * 64
H6 = 'f' * 64
H7 = '1' * 64
H8 = '2' * 64
H9 = '3' * 64
H10 = '4' * 64
H11 = '5' * 64
H12 = '6' * 64
H13 = '7' * 64
H14 = '8' * 64
H15 = '9' * 64
H16 = '0' * 64
TRUST = frozenset([H, H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12, H13, H14, H15, H16])
NOW = datetime.now(timezone.utc)
TS = NOW.strftime('%Y-%m-%dT%H:%M:%S+00:00')

def base_receipt(**kw):
    r = {
        'schema': 1,
        'timestamp': TS,
        'artifacts': [{'sha256': h} for h in TRUST],
        'bindings': {'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4},
        'devices': [],
        'claims': [],
    }
    r.update(kw)
    return r

def gpu(pid, vendor='NVIDIA', usable=10**10, high=10**10, reserve=0, completed=True, blocks=None, source='ACTUAL_ALLOCATOR'):
    d = {
        'pci_id': f'0000:{pid[-2:]}:00.0',
        'physical_id': pid,
        'vendor': vendor,
        'device_class': 'DISCRETE_GPU',
        'memory': {
            'kind': 'DEDICATED',
            'source': source,
            'total_bytes': usable + reserve + 10**9,
            'free_bytes': usable - high + 10**9,
            'reserve_bytes': reserve,
            'highwater_bytes': high,
            'usable_bytes': usable,
            'measured_at': TS,
        },
        'kernel': {'completed': completed, 'tensor_sha256': H5},
        'blocks': blocks or [],
    }
    return d

def cpu_dev(pid, vendor='Intel'):
    return {
        'pci_id': f'0000:{pid[-2:]}:00.0',
        'physical_id': pid,
        'vendor': vendor,
        'device_class': 'CPU',
    }

class TestFourRequired(unittest.TestCase):
    def test_four_required_needs_4_devices(self):
        devs = [gpu(f'g{i}', blocks=[{'block_id': f'b{i}', 'weight_sha256': H6, 'owner': f'g{i}'}]) for i in range(3)]
        r = base_receipt(devices=devs, claims=['FOUR_PHYSICAL_GPU'])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'NOT_CHECKED')

    def test_four_required_success(self):
        devs = [gpu(f'g{i}', blocks=[{'block_id': f'b{i}', 'weight_sha256': H6, 'owner': f'g{i}'}]) for i in range(4)]
        r = base_receipt(devices=devs, claims=['FOUR_PHYSICAL_GPU'])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'QUALIFIED')

    def test_four_alias_rejected(self):
        devs = [gpu('g0', blocks=[{'block_id': 'b0', 'weight_sha256': H6, 'owner': 'g0'}]) for _ in range(4)]
        r = base_receipt(devices=devs, claims=['FOUR_PHYSICAL_GPU'])
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

class TestCapacityGuards(unittest.TestCase):
    def _cap_receipt(self, n_devs=4, assigned=2*10**9, usable=3*10**9, high=3*10**9, reserve=0, multi_ok=True, claim='FOUR_REQUIRED_CAPACITY'):
        devs = [gpu(f'g{i}', usable=usable, high=high, reserve=reserve) for i in range(n_devs)]
        plans = [{'physical_id': f'g{i}', 'assigned_bytes': assigned} for i in range(n_devs)]
        cap = {
            'quant_sha256': H7, 'context': 2048, 'batch': 1, 'requirement_bytes': assigned * n_devs - 1,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
            'plans': plans,
            'single': {'failure_kind': 'ACTUAL_ALLOCATOR_OOM', 'device_count': 1, 'physical_ids': ['g0'],
                       'quant_sha256': H7, 'context': 2048, 'batch': 1, 'artifact_sha256': H8,
                       'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4},
        }
        if multi_ok:
            cap['multi'] = {
                'status': 'SUCCESS', 'physical_ids': [f'g{i}' for i in range(n_devs)],
                'quant_sha256': H7, 'context': 2048, 'batch': 1, 'artifact_sha256': H9,
                'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
                'numerical': {
                    'full_count': 100, 'finite_count': 100, 'violation_count': 0,
                    'rmse': 0.0, 'max_abs_error': 0.0, 'atol': 1e-5, 'rtol': 1e-5,
                    'predeclared_atol': 1e-5, 'predeclared_rtol': 1e-5,
                    'array_sha256': H10, 'reference_sha256': H11,
                    'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
                }
            }
        r = base_receipt(devices=devs, claims=[claim], capacity=cap)
        return r

    def test_zero_assignment_rejected(self):
        r = self._cap_receipt(assigned=0)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

    def test_absent_multi_success_rejected(self):
        r = self._cap_receipt(multi_ok=False)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'NOT_CHECKED')

    def test_insufficient_highwater_rejected(self):
        r = self._cap_receipt(assigned=2*10**9, high=10**9)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

    def test_stale_memory_rejected(self):
        r = self._cap_receipt()
        old_ts = (NOW - timedelta(seconds=100)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        for d in r['devices']:
            d['memory']['measured_at'] = old_ts
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertNotEqual(out['status'], 'QUALIFIED')

    def test_wrong_quant_rejected(self):
        r = self._cap_receipt()
        r['capacity']['multi']['quant_sha256'] = H12
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

    def test_wrong_context_rejected(self):
        r = self._cap_receipt()
        r['capacity']['multi']['context'] = 4096
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

    def test_three_devices_four_required_rejected(self):
        r = self._cap_receipt(n_devs=3)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'NOT_CHECKED')

    def test_capacity_from_count_alone_rejected(self):
        r = self._cap_receipt(multi_ok=False)
        del r['capacity']['multi']
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'NOT_CHECKED')

class TestTwoVendorNumerical(unittest.TestCase):
    def test_cpu_vendor_rejected(self):
        devs = [cpu_dev('c0', 'Intel'), gpu('g0', 'AMD')]
        ev = {
            'physical_ids': ['c0', 'g0'],
            'full_count': 10, 'finite_count': 10, 'violation_count': 0,
            'rmse': 0.0, 'max_abs_error': 0.0, 'atol': 1e-5, 'rtol': 1e-5,
            'predeclared_atol': 1e-5, 'predeclared_rtol': 1e-5,
            'array_sha256': H10, 'reference_sha256': H11,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }
        ctrl = [{
            'kind': 'COMPARATOR_ONLY', 'scope': 'COMPARE_ONLY', 'exit_code': 1, 'detected': True,
            'artifact_sha256': H12,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }]
        r = base_receipt(devices=devs, claims=['TWO_VENDOR_NUMERICAL'], numerical=ev, controls=ctrl)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('CPU_OR_OTHER_VENDOR', out['reasons'])

    def test_two_gpu_vendors_pass(self):
        devs = [gpu('g0', 'NVIDIA'), gpu('g1', 'AMD')]
        ev = {
            'physical_ids': ['g0', 'g1'],
            'full_count': 10, 'finite_count': 10, 'violation_count': 0,
            'rmse': 0.0, 'max_abs_error': 0.0, 'atol': 1e-5, 'rtol': 1e-5,
            'predeclared_atol': 1e-5, 'predeclared_rtol': 1e-5,
            'array_sha256': H10, 'reference_sha256': H11,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }
        ctrl = [{
            'kind': 'COMPARATOR_ONLY', 'scope': 'COMPARE_ONLY', 'exit_code': 1, 'detected': True,
            'artifact_sha256': H12,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }]
        r = base_receipt(devices=devs, claims=['TWO_VENDOR_NUMERICAL'], numerical=ev, controls=ctrl)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'QUALIFIED')

class TestControlBinding(unittest.TestCase):
    def test_unbound_control_rejected(self):
        devs = [gpu('g0', 'NVIDIA'), gpu('g1', 'AMD')]
        ev = {
            'physical_ids': ['g0', 'g1'],
            'full_count': 10, 'finite_count': 10, 'violation_count': 0,
            'rmse': 0.0, 'max_abs_error': 0.0, 'atol': 1e-5, 'rtol': 1e-5,
            'predeclared_atol': 1e-5, 'predeclared_rtol': 1e-5,
            'array_sha256': H10, 'reference_sha256': H11,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }
        ctrl = [{
            'kind': 'COMPARATOR_ONLY', 'scope': 'COMPARE_ONLY', 'exit_code': 1, 'detected': True,
            'artifact_sha256': H12,
            'model_sha256': H13, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }]
        r = base_receipt(devices=devs, claims=['TWO_VENDOR_NUMERICAL'], numerical=ev, controls=ctrl)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')

class TestPredeclaredTolerances(unittest.TestCase):
    def test_missing_predeclared_rejected(self):
        devs = [gpu('g0', 'NVIDIA'), gpu('g1', 'AMD')]
        ev = {
            'physical_ids': ['g0', 'g1'],
            'full_count': 10, 'finite_count': 10, 'violation_count': 0,
            'rmse': 0.0, 'max_abs_error': 0.0, 'atol': 1e-5, 'rtol': 1e-5,
            'array_sha256': H10, 'reference_sha256': H11,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }
        ctrl = [{
            'kind': 'COMPARATOR_ONLY', 'scope': 'COMPARE_ONLY', 'exit_code': 1, 'detected': True,
            'artifact_sha256': H12,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }]
        r = base_receipt(devices=devs, claims=['TWO_VENDOR_NUMERICAL'], numerical=ev, controls=ctrl)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('MISSING_PREDECLARED_TOLERANCE', out['reasons'])

    def test_rmse_exceeds_max_abs_rejected(self):
        devs = [gpu('g0', 'NVIDIA'), gpu('g1', 'AMD')]
        ev = {
            'physical_ids': ['g0', 'g1'],
            'full_count': 10, 'finite_count': 10, 'violation_count': 0,
            'rmse': 2.0, 'max_abs_error': 1.0, 'atol': 3.0, 'rtol': 1e-5,
            'predeclared_atol': 3.0, 'predeclared_rtol': 1e-5,
            'array_sha256': H10, 'reference_sha256': H11,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }
        ctrl = [{
            'kind': 'COMPARATOR_ONLY', 'scope': 'COMPARE_ONLY', 'exit_code': 1, 'detected': True,
            'artifact_sha256': H12,
            'model_sha256': H, 'workload_sha256': H2, 'build_sha256': H3, 'executable_sha256': H4,
        }]
        r = base_receipt(devices=devs, claims=['TWO_VENDOR_NUMERICAL'], numerical=ev, controls=ctrl)
        out = validate_result(r, now_utc=NOW, trusted_artifact_hashes=TRUST)
        self.assertEqual(out['status'], 'REFUSED')
        self.assertIn('RMSE_EXCEEDS_MAX_ABS', out['reasons'])

if __name__ == '__main__':
    unittest.main()
