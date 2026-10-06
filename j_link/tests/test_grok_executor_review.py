"""GPU-free review tests for admission limits and cross-vendor boundaries."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

J_LINK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(J_LINK))
import opencl_executor as executor


def largest_buffer(width, workspace_bytes):
    return max(width * width * 4, width * 4, workspace_bytes // 2)


def prepared(width=8, workspace_bytes=64, layer_bytes=16, policy_mib=1):
    return {
        'actual_layer_weight_bytes': layer_bytes,
        'workspace_bytes': workspace_bytes,
        'width': width,
        'policy_mib_per_device': policy_mib,
        'layer_ownership': [{'device_id': 'gpu0', 'layers': ['layer_00']}],
    }


def selected(maximum):
    return [{'runtime_id': 'gpu0', 'max_mem_alloc_bytes_reported': maximum}]


class MaxAllocationAdmission(unittest.TestCase):
    def test_unknown_boolean_nonpositive_or_noninteger_limit_refuses(self):
        plan = prepared()
        for maximum in (0, None, True, False, -1, -8, 1.5, '4096'):
            with self.subTest(maximum=maximum):
                with self.assertRaises(executor.RuntimeUnavailable):
                    executor._check_device_memory(selected(maximum), plan)

    def test_reported_limit_smaller_than_largest_buffer_refuses(self):
        plan = prepared()
        largest = largest_buffer(plan['width'], plan['workspace_bytes'])
        with self.assertRaises(executor.RuntimeUnavailable):
            executor._check_device_memory(selected(largest - 1), plan)

    def test_sufficient_reported_limit_is_recorded(self):
        plan = prepared()
        largest = largest_buffer(plan['width'], plan['workspace_bytes'])
        records = executor._check_device_memory(selected(largest), plan)
        self.assertEqual(records['gpu0']['max_single_buffer_bytes_reported'], largest)
        self.assertEqual(records['gpu0']['planned_allocation_bytes'], 80)

    def test_unknown_runtime_limit_stops_child_before_gpu_execution(self):
        records = [
            {'runtime_id': 'p0:d0', 'physical_id': 'pci:nv',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'NVIDIA',
             'vendor': 'NVIDIA Corporation', 'max_mem_alloc_bytes_reported': 0,
             'device': object()},
            {'runtime_id': 'p1:d0', 'physical_id': 'pci:amd',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'AMD',
             'vendor': 'Advanced Micro Devices', 'max_mem_alloc_bytes_reported': None,
             'device': object()},
        ]
        payload = {'width': 32, 'batch': 1, 'layers': 2, 'policy_mib': 9,
                   'seed': 103004, 'device_ids': None, 'reverse': False,
                   'inject_corruption': False}
        output = io.StringIO()
        with mock.patch.object(executor.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(executor.sys, 'stdout', output), \
                mock.patch.object(executor, 'enumerate_opencl_devices', return_value=records), \
                mock.patch.object(executor, '_execute_gpu', side_effect=AssertionError('GPU execution reached')) as run:
            code = executor._child_main()
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'NOT_CHECKED')
        self.assertIn('max allocation is unknown', result['reason'])
        run.assert_not_called()

    def test_single_device_corruption_is_refused_as_missing_vendor_boundary(self):
        records = [{'runtime_id': 'p0:d0', 'physical_id': 'pci:nv',
                    'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR',
                    'vendor_key': 'NVIDIA', 'vendor': 'NVIDIA Corporation',
                    'max_mem_alloc_bytes_reported': 1024 * 1024,
                    'device': object()}]
        payload = {'width': 32, 'batch': 1, 'layers': 2, 'policy_mib': 9,
                   'seed': 103004, 'device_ids': ['p0:d0'], 'reverse': False,
                   'inject_corruption': True}
        output = io.StringIO()
        with mock.patch.object(executor.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(executor.sys, 'stdout', output), \
                mock.patch.object(executor, 'enumerate_opencl_devices', return_value=records), \
                mock.patch.object(executor, '_execute_gpu', side_effect=AssertionError('GPU execution reached')) as run:
            code = executor._child_main()
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'REFUSED')
        self.assertIn('first vendor activation boundary', result['reason'])
        run.assert_not_called()


class VendorBoundary(unittest.TestCase):
    def test_boundary_is_first_change_in_vendor_not_first_device_owner(self):
        owners = {0: 'nv0', 1: 'nv1', 2: 'amd0'}
        vendors = {'nv0': 'NVIDIA', 'nv1': 'NVIDIA', 'amd0': 'AMD'}
        self.assertEqual(executor._first_vendor_boundary(owners, 3, vendors), 1)
        self.assertEqual(executor._require_vendor_boundary(owners, 3, vendors, True), 1)

    def test_reverse_vendor_order_uses_its_first_actual_vendor_change(self):
        owners = {0: 'amd0', 1: 'nv0', 2: 'nv1'}
        vendors = {'amd0': 'AMD', 'nv0': 'NVIDIA', 'nv1': 'NVIDIA'}
        self.assertEqual(executor._first_vendor_boundary(owners, 3, vendors), 0)

    def test_same_vendor_devices_are_not_a_corruption_boundary(self):
        owners = {0: 'nv0', 1: 'nv1', 2: 'nv2'}
        vendors = {'nv0': 'NVIDIA', 'nv1': 'NVIDIA', 'nv2': 'NVIDIA'}
        self.assertIsNone(executor._first_vendor_boundary(owners, 3, vendors))
        self.assertIsNone(executor._require_vendor_boundary(owners, 3, vendors, False))
        with self.assertRaises(executor.RuntimeRefused):
            executor._require_vendor_boundary(owners, 3, vendors, True)

    def test_execution_labels_only_claim_mixed_vendor_when_keys_differ(self):
        population, selected, labels = executor._execution_identity(['NVIDIA'])
        self.assertEqual(population, 'SINGLE_VENDOR')
        self.assertEqual(selected, ['NVIDIA'])
        self.assertIn('RESIDUAL_MLP_EXECUTION_ONLY', labels)
        self.assertNotIn('MIXED_VENDOR_RESIDUAL_MLP_EXECUTION_ONLY', labels)

        population, selected, labels = executor._execution_identity(
            ['NVIDIA', 'AMD', 'NVIDIA'])
        self.assertEqual(population, 'MIXED_VENDOR')
        self.assertEqual(selected, ['AMD', 'NVIDIA'])
        self.assertIn('MIXED_VENDOR_RESIDUAL_MLP_EXECUTION_ONLY', labels)


if __name__ == '__main__':
    unittest.main()
