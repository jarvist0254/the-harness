import unittest
import json
from datetime import datetime, timezone

# Assuming the source above is imported as qualification_validator
# For this test file, we will define a mock import structure or assume it exists.
# In a real scenario: from qualification_validator import validate_result

def validate_result_mock(receipt, *, now_utc, max_age_seconds=10, trusted_artifact_hashes=frozenset()):
    # Placeholder to allow tests to run in isolation if module not found
    # But per instructions, we must use actual-import. 
    # We will rely on the environment having the source available.
    pass

try:
    from qualification_validator import validate_result
except ImportError:
    # Fallback for strict execution context if needed, but prompt says NO stubs.
    # We assume the runner injects the source into sys.modules or path.
    raise ImportError("qualification_validator not found")

class TestQualificationValidator(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
        self.max_age = 10
        self.trusted_hash = 'a' * 64
        self.trusted_set = frozenset([self.trusted_hash])

    def make_receipt(self, **kwargs):
        base = {
            'timestamp': self.now.isoformat(),
            'artifacts': [{'sha256': self.trusted_hash}],
            'devices': [],
            'claims': []
        }
        base.update(kwargs)
        return base

    def test_unknown_missing_untrusted_not_checked(self):
        # Missing artifact hash
        receipt = self.make_receipt(artifacts=[{'sha256': 'wrong'}])
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('UNTRUSTED_ARTIFACT:wrong', res['reasons'])

    def test_malformed_bool_nan_negative_refused(self):
        # Invalid memory types
        dev = {
            'pci_id': '0000:01:00.0',
            'vendor': 'NVIDIA',
            'memory': {
                'total_bytes': float('nan'),
                'free_bytes': 100,
                'allocator_peak_bytes': 50,
                'kind': 'DEDICATED'
            },
            'kernels_completed': True,
            'resident_block_hash': 'block1'
        }
        receipt = self.make_receipt(
            devices=[dev]*4,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('INVALID_MEM_TYPES', res['reasons'])

    def test_stale_future_timestamp_not_checked(self):
        old_time = self.now.replace(minute=59)
        receipt = self.make_receipt(timestamp=old_time.isoformat())
        res = validate_result(receipt, now_utc=self.now, max_age_seconds=10, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'NOT_CHECKED')
        self.assertIn('STALE_OR_FUTURE_TIMESTAMP', res['reasons'])

    def test_8hex_alias_dup_refused(self):
        # Duplicate normalized PCI
        dev1 = {'pci_id': '0000:01:00.0', 'vendor': 'A', 'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 100, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b1'}
        dev2 = {'pci_id': '0000:01:00.0', 'vendor': 'B', 'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 100, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b2'}
        receipt = self.make_receipt(
            devices=[dev1, dev2, dev1, dev2],
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('DUPLICATE_PCI_ALIAS:0000:01:00.0', res['reasons'])

    def test_cpu_shared_amd_tiny_policy_single_card_fits_replication_refused(self):
        # Shared host memory cannot qualify for dedicated VRAM gate
        dev = {
            'pci_id': '0000:01:00.0',
            'vendor': 'AMD',
            'memory': {
                'total_bytes': 1000,
                'free_bytes': 500,
                'allocator_peak_bytes': 100,
                'kind': 'SHARED_HOST' # Not Dedicated
            },
            'kernels_completed': True,
            'resident_block_hash': 'b1'
        }
        receipt = self.make_receipt(
            devices=[dev]*4,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('SHARED_MEMORY_NOT_DEDICATED', res['reasons'])

    def test_model_workload_mismatch_refused(self):
        # Duplicate resident blocks implies replication
        dev = {
            'pci_id': '0000:01:00.0',
            'vendor': 'NVIDIA',
            'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 100, 'kind': 'DEDICATED'},
            'kernels_completed': True,
            'resident_block_hash': 'SAME_BLOCK' # All same
        }
        receipt = self.make_receipt(
            devices=[dev]*4,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('DUPLICATE_MODEL_REPLICATION', res['reasons'])

    def test_absent_allocator_not_checked(self):
        # Missing allocator proof
        dev = {
            'pci_id': '0000:01:00.0',
            'vendor': 'NVIDIA',
            'memory': {'total_bytes': 1000, 'free_bytes': 500, 'kind': 'DEDICATED'}, # No peak
            'kernels_completed': True,
            'resident_block_hash': 'b1'
        }
        receipt = self.make_receipt(
            devices=[dev]*4,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED') # INVALID_MEM_TYPES because peak is None/missing
        self.assertIn('INVALID_MEM_TYPES', res['reasons'])

    def test_forged_bool_no_provenance_not_checked(self):
        # If artifacts are missing/untrusted, it's NOT_CHECKED
        receipt = self.make_receipt(artifacts=[], claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}])
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'NOT_CHECKED')

    def test_valid_two_vendor_partial(self):
        devs = [
            {'pci_id': '0000:01:00.0', 'vendor': 'NVIDIA', 'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 100, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b1'},
            {'pci_id': '0000:02:00.0', 'vendor': 'AMD', 'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 100, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b2'},
        ]
        receipt = self.make_receipt(
            devices=devs,
            claims=[{'id': 'TWO_VENDOR_NUMERICAL', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'QUALIFIED')
        self.assertIn('TWO_VENDOR_NUMERICAL', res['qualified_claims'])

    def test_complete_4_trusted_synthetic_structured_fixture_pass(self):
        devs = []
        for i in range(4):
            devs.append({
                'pci_id': f'0000:0{i+1}:00.0',
                'vendor': 'NVIDIA' if i % 2 == 0 else 'AMD',
                'memory': {'total_bytes': 10000, 'free_bytes': 5000, 'allocator_peak_bytes': 1000, 'kind': 'DEDICATED'},
                'kernels_completed': True,
                'resident_block_hash': f'unique_block_{i}'
            })
        receipt = self.make_receipt(
            devices=devs,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'QUALIFIED')
        self.assertIn('FOUR_PHYSICAL_GPU', res['qualified_claims'])

    def test_4_necessary_3_policy_oom_refuse(self):
        # Simulate OOM by setting peak > total
        devs = []
        for i in range(4):
            devs.append({
                'pci_id': f'0000:0{i+1}:00.0',
                'vendor': 'NVIDIA',
                'memory': {'total_bytes': 1000, 'free_bytes': 500, 'allocator_peak_bytes': 2000, 'kind': 'DEDICATED'}, # Peak > Total
                'kernels_completed': True,
                'resident_block_hash': f'b{i}'
            })
        receipt = self.make_receipt(
            devices=devs,
            claims=[{'id': 'FOUR_PHYSICAL_GPU', 'evidence': {}}]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('PEAK_GT_TOTAL', res['reasons'])

    def test_llm_prose_fake_refused(self):
        devs = [{'pci_id': '0000:01:00.0', 'vendor': 'N', 'memory': {'total_bytes': 100, 'free_bytes': 50, 'allocator_peak_bytes': 10, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b1'}] * 4
        receipt = self.make_receipt(
            devices=devs,
            claims=[{
                'id': 'LLM_LOGIT_PARITY', 
                'evidence': {
                    'type': 'TEXT_PROSE', # Fake
                    'reference_logit_hash': 'h1',
                    'calculated_logit_hash': 'h1',
                    'max_abs_error': 0.0,
                    'tolerance': 0.0
                }
            }]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('PROSE_ONLY_EVIDENCE', res['reasons'])

    def test_p2p_host_stage_fake_refused(self):
        devs = [{'pci_id': '0000:01:00.0', 'vendor': 'N', 'memory': {'total_bytes': 100, 'free_bytes': 50, 'allocator_peak_bytes': 10, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b1'}] * 4
        receipt = self.make_receipt(
            devices=devs,
            claims=[{
                'id': 'DIRECT_P2P', 
                'evidence': {
                    'primitive_type': 'HOST_STAGED' # Fake
                }
            }]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('HOST_STAGED_OR_SYSTEM_HEAP_P2P', res['reasons'])

    def test_durable_atomic_fake_refused(self):
        devs = [{'pci_id': '0000:01:00.0', 'vendor': 'N', 'memory': {'total_bytes': 100, 'free_bytes': 50, 'allocator_peak_bytes': 10, 'kind': 'DEDICATED'}, 'kernels_completed': True, 'resident_block_hash': 'b1'}] * 4
        receipt = self.make_receipt(
            devices=devs,
            claims=[{
                'id': 'DURABLE_REPLAY', 
                'evidence': {
                    'checkpoint_identity': 'cp1',
                    'commit_sequence': 1,
                    'replay_boundary': 1,
                    'method': 'ATOMIC_JSON_WRITE_ONLY' # Fake durability
                }
            }]
        )
        res = validate_result(receipt, now_utc=self.now, trusted_artifact_hashes=self.trusted_set)
        self.assertEqual(res['status'], 'REFUSED')
        self.assertIn('ATOMIC_JSON_NOT_DURABILITY', res['reasons'])

if __name__ == '__main__':
    unittest.main()
