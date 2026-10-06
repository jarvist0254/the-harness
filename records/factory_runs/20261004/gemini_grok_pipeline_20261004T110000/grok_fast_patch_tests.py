"""GPU-free checks for reported max-allocation admission and vendor boundaries."""
import unittest

from j_link.opencl_executor import (
    RuntimeRefused,
    RuntimeUnavailable,
    _check_device_memory,
    _first_vendor_boundary,
    _require_vendor_boundary,
)


def _largest(width, workspace_bytes):
    activation_bytes = workspace_bytes // 2
    return max(width * width * 4, width * 4, activation_bytes)


def _prepared(width=8, workspace_bytes=64, layer_bytes=16, policy_mib=1):
    """Synthetic admission plan with the same fields prepare_plan supplies."""
    return {
        'actual_layer_weight_bytes': layer_bytes,
        'workspace_bytes': workspace_bytes,
        'width': width,
        'policy_mib_per_device': policy_mib,
        'layer_ownership': [
            {'device_id': 'gpu0', 'layers': ['layer_00']},
        ],
    }


def _selected(maximum):
    return [{
        'runtime_id': 'gpu0',
        'max_mem_alloc_bytes_reported': maximum,
    }]


class MaxAllocAdmissionTest(unittest.TestCase):
    def test_unknown_maximum_raises_before_allocation(self):
        prepared = _prepared()
        for maximum in (0, None, True, False, -1, -8, 1.5, '4096'):
            with self.subTest(maximum=maximum):
                with self.assertRaises(RuntimeUnavailable):
                    _check_device_memory(_selected(maximum), prepared)

    def test_known_maximum_below_largest_buffer_rejects(self):
        prepared = _prepared()
        largest = _largest(prepared['width'], prepared['workspace_bytes'])
        self.assertGreater(prepared['policy_mib_per_device'] * 1024 * 1024, largest - 1)
        with self.assertRaises(RuntimeUnavailable):
            _check_device_memory(_selected(largest - 1), prepared)

    def test_sufficient_maximum_returns_allocation_record(self):
        prepared = _prepared()
        largest = _largest(prepared['width'], prepared['workspace_bytes'])
        self.assertEqual(largest, 256)
        records = _check_device_memory(_selected(largest), prepared)
        record = records['gpu0']
        self.assertEqual(record['max_single_buffer_bytes_reported'], largest)
        self.assertEqual(record['assigned_layers'], ['layer_00'])
        self.assertEqual(record['resident_weight_and_bias_bytes'], 16)
        self.assertEqual(record['activation_ping_pong_bytes'], 64)
        self.assertEqual(record['planned_allocation_bytes'], 80)
        self.assertEqual(record['policy_cap_bytes'], 1024 * 1024)


class VendorBoundaryTest(unittest.TestCase):
    def test_first_vendor_boundary_after_second_nvidia(self):
        layer_owner = {0: 'nv0', 1: 'nv1', 2: 'amd0'}
        vendor_by_id = {'nv0': 'NVIDIA', 'nv1': 'NVIDIA', 'amd0': 'AMD'}
        self.assertEqual(
            _first_vendor_boundary(layer_owner, 3, vendor_by_id), 1)
        self.assertEqual(
            _require_vendor_boundary(layer_owner, 3, vendor_by_id, True), 1)

    def test_reverse_amd_then_nvidia_selects_first_change(self):
        layer_owner = {0: 'amd0', 1: 'nv0', 2: 'nv1'}
        vendor_by_id = {'amd0': 'AMD', 'nv0': 'NVIDIA', 'nv1': 'NVIDIA'}
        self.assertEqual(
            _first_vendor_boundary(layer_owner, 3, vendor_by_id), 0)

    def test_homogeneous_vendor_is_none_and_inject_refuses(self):
        layer_owner = {0: 'nv0', 1: 'nv1', 2: 'nv2'}
        vendor_by_id = {'nv0': 'NVIDIA', 'nv1': 'NVIDIA', 'nv2': 'NVIDIA'}
        self.assertIsNone(_first_vendor_boundary(layer_owner, 3, vendor_by_id))
        self.assertIsNone(
            _require_vendor_boundary(layer_owner, 3, vendor_by_id, False))
        with self.assertRaises(RuntimeRefused):
            _require_vendor_boundary(layer_owner, 3, vendor_by_id, True)


if __name__ == '__main__':
    unittest.main()

