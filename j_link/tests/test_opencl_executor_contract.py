"""GPU-free contracts for the experimental mixed-vendor executor."""
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

J_LINK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(J_LINK))
from planner import PlanError as PlannerPlanError


MIB = 1024 * 1024


def device(alias, physical, vendor):
    return {'id': alias, 'physical_id': physical, 'vendor': vendor}


def executor_module():
    return importlib.import_module('opencl_executor')


class ExecutorPlanContracts(unittest.TestCase):
    def setUp(self):
        self.nvidia_amd = [device('nv0', 'pci-nv0', 'NVIDIA'),
                           device('amd0', 'pci-amd0', 'AMD')]

    def test_import_is_gpu_free_and_planerror_is_planner_error(self):
        code = r"""
import builtins, sys
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == 'numpy' or name.startswith('numpy.') or name == 'pyopencl' or name.startswith('pyopencl.'):
        raise AssertionError('GPU/runtime dependency imported during pure module import')
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
import opencl_executor
from planner import PlanError
assert opencl_executor.PlanError is PlanError
assert 'numpy' not in sys.modules
assert 'pyopencl' not in sys.modules
print('GPU_FREE_IMPORT_OK')
"""
        env = os.environ.copy()
        env['PYTHONPATH'] = str(J_LINK)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        child = subprocess.run([sys.executable, '-c', code], cwd=J_LINK, env=env,
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr or child.stdout)
        self.assertIn('GPU_FREE_IMPORT_OK', child.stdout)

    def test_default_policy_assigns_four_unique_layers_to_each_vendor(self):
        module = executor_module()
        result = module.prepare_plan(self.nvidia_amd)
        expected_layers = [f'layer_{i:02d}' for i in range(8)]
        layer_bytes = (512 * 512 + 512) * 4

        self.assertEqual(result['actual_layer_weight_bytes'], layer_bytes)
        self.assertEqual(result['modeled_layer_mib'], 2)
        self.assertEqual(result['workspace_bytes'], 2 * 8 * 512 * 4)
        self.assertEqual(result['total_actual_weight_bytes'], layer_bytes * 8)
        self.assertLess(result['total_actual_weight_bytes'] + result['workspace_bytes'], 32 * MIB)
        self.assertEqual(result['planner_result']['status'], 'PLANNED_NOT_ALLOCATED')
        self.assertEqual(result['planner_result']['aggregate_budget_mib'], 16)

        ownership = result['layer_ownership']
        self.assertEqual([entry['device_id'] for entry in ownership], ['nv0', 'amd0'])
        flattened = [layer for entry in ownership for layer in entry['layers']]
        self.assertEqual(flattened, expected_layers)
        self.assertEqual([len(entry['layers']) for entry in ownership], [4, 4])
        self.assertEqual(len(set(flattened)), 8)
        for entry in ownership:
            self.assertEqual(entry['physical_id'], {'nv0': 'pci-nv0', 'amd0': 'pci-amd0'}[entry['device_id']])

        planned_devices = result['planner_result']['devices']
        self.assertEqual([d['block_memory_mib'] for d in planned_devices], [8, 8])
        self.assertTrue(all(d['remaining_budget_mib'] == 0 for d in planned_devices))
        self.assertEqual([block for d in planned_devices for block in d['blocks']], expected_layers)

    def test_four_device_sixteen_layer_policy_fit_and_accounting_rounds_up(self):
        module = executor_module()
        devices = [device(f'd{i}', f'physical-{i}', vendor)
                   for i, vendor in enumerate(('NVIDIA', 'AMD', 'Intel', 'NVIDIA'))]
        result = module.prepare_plan(devices, width=32, batch=1, layers=16, policy_mib=9)

        small_layer_bytes = (32 * 32 + 32) * 4
        self.assertEqual(result['actual_layer_weight_bytes'], small_layer_bytes)
        self.assertEqual(result['modeled_layer_mib'], 1)  # ceiling, not truncation
        self.assertEqual(result['workspace_bytes'], 2 * 1 * 32 * 4)
        self.assertEqual(result['total_actual_weight_bytes'], small_layer_bytes * 16)
        self.assertEqual([len(entry['layers']) for entry in result['layer_ownership']], [4, 4, 4, 4])
        self.assertEqual(result['planner_result']['aggregate_budget_mib'], 32)
        self.assertLess(result['workspace_bytes'], MIB)

    def test_same_sixteen_layer_workload_is_rejected_with_three_devices(self):
        module = executor_module()
        devices = [device(f'd{i}', f'physical-{i}', f'vendor-{i}') for i in range(3)]
        with self.assertRaises(PlannerPlanError):
            module.prepare_plan(devices, width=512, batch=8, layers=16, policy_mib=9)

    def test_same_width512_sixteen_layer_workload_fits_four_policy_budgets(self):
        module = executor_module()
        devices = [device(f'd{i}', f'physical-{i}', f'vendor-{i}') for i in range(4)]
        result = module.prepare_plan(devices, width=512, batch=8, layers=16, policy_mib=9)
        self.assertEqual(result['modeled_layer_mib'], 2)
        self.assertEqual(result['planner_result']['aggregate_budget_mib'], 32)
        self.assertEqual([len(entry['layers']) for entry in result['layer_ownership']], [4, 4, 4, 4])

    def test_single_nine_mib_policy_device_cannot_fit_default_eight_layers(self):
        module = executor_module()
        with self.assertRaises(PlannerPlanError):
            module.prepare_plan([device('nv0', 'pci-nv0', 'NVIDIA')])

    def test_rejects_unused_device_participants_and_duplicate_identities(self):
        module = executor_module()
        three = [device('nv0', 'pci-nv0', 'NVIDIA'),
                 device('amd0', 'pci-amd0', 'AMD'),
                 device('intel0', 'pci-intel0', 'Intel')]
        with self.assertRaises(PlannerPlanError):
            module.prepare_plan(three, width=32, batch=1, layers=2, policy_mib=9)

        duplicate_alias = [device('same', 'pci-1', 'NVIDIA'), device('same', 'pci-2', 'AMD')]
        with self.assertRaises(PlannerPlanError):
            module.prepare_plan(duplicate_alias)
        duplicate_physical = [device('nv0', 'same-pci', 'NVIDIA'), device('amd0', 'same-pci', 'AMD')]
        with self.assertRaises(PlannerPlanError):
            module.prepare_plan(duplicate_physical)

    def test_rejects_boolean_and_out_of_range_dimensions_and_policy(self):
        module = executor_module()
        valid = dict(width=512, batch=8, layers=8, policy_mib=9)
        invalid = [
            {'width': 31}, {'width': 513}, {'width': True},
            {'batch': 0}, {'batch': 17}, {'batch': False},
            {'layers': 1}, {'layers': 17}, {'layers': True},
            {'policy_mib': 0}, {'policy_mib': 65}, {'policy_mib': True},
        ]
        for change in invalid:
            with self.subTest(change=change):
                args = dict(valid)
                args.update(change)
                with self.assertRaises(PlannerPlanError):
                    module.prepare_plan(self.nvidia_amd, **args)

    def test_device_filter_detects_parent_device_without_legacy_parent_attribute(self):
        module = executor_module()

        class Subdevice:
            vendor = 'NVIDIA Corporation'
            name = 'partition'
            parent_device = object()

            def get_info(self, _):
                return self.parent_device

        fake_cl = SimpleNamespace(device_info=SimpleNamespace(PARENT_DEVICE=1))
        self.assertTrue(module._is_software_device(Subdevice(), fake_cl))
        self.assertFalse(module._is_software_device(
            SimpleNamespace(vendor='Mesa GPU driver', name='Discrete GPU', parent_device=None,
                            get_info=lambda _: None), fake_cl))

    def test_mixed_pci_identity_schemes_for_same_vendor_refuse_ambiguous_aliasing(self):
        module = executor_module()
        records = [
            {'runtime_id': 'p0:d0', 'physical_id': 'pci:0000:01:00.0',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'NVIDIA'},
            {'runtime_id': 'p1:d0', 'physical_id': 'pci:0000:01:slot0001',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_NV', 'vendor_key': 'NVIDIA'},
        ]
        with self.assertRaises(module.RuntimeRefused):
            module.select_devices(records, ['p0:d0', 'p1:d0'])

    def test_runtime_selection_refuses_pci_aliases_and_ambiguous_ephemeral_pairs(self):
        module = executor_module()
        aliased = [
            {'runtime_id': 'p0:d0', 'physical_id': 'pci:0000:01:00.0',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'NVIDIA'},
            {'runtime_id': 'p1:d0', 'physical_id': 'pci:0000:01:00.0',
             'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'AMD'},
        ]
        with self.assertRaises(module.RuntimeRefused):
            module.select_devices(aliased, ['p0:d0', 'p1:d0'])

        ephemeral = [
            {'runtime_id': 'p0:d0', 'physical_id': 'runtime:p0:d0',
             'identity_confidence': 'EPHEMERAL_RUNTIME_ID', 'vendor_key': 'NVIDIA'},
            {'runtime_id': 'p0:d1', 'physical_id': 'runtime:p0:d1',
             'identity_confidence': 'EPHEMERAL_RUNTIME_ID', 'vendor_key': 'NVIDIA'},
        ]
        with self.assertRaises(module.RuntimeRefused):
            module.select_devices(ephemeral, ['p0:d0', 'p0:d1'])

    def test_runtime_selection_reports_missing_explicit_id_as_unavailable(self):
        module = executor_module()
        records = [{'runtime_id': 'p0:d0', 'physical_id': 'pci:nv0',
                    'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR', 'vendor_key': 'NVIDIA'}]
        with self.assertRaises(module.RuntimeUnavailable):
            module.select_devices(records, ['p9:d9'])

    def test_device_type_filter_rejects_cpu_bit_combined_with_gpu(self):
        module = executor_module()
        cl = SimpleNamespace(device_type=SimpleNamespace(GPU=4, CPU=2))
        self.assertFalse(module._is_hardware_gpu_type(6, cl))
        self.assertTrue(module._is_hardware_gpu_type(4, cl))

    def _run_child_payload(self, module, payload, records):
        output = io.StringIO()
        with mock.patch.object(module.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(module.sys, 'stdout', output), \
                mock.patch.object(module, 'enumerate_opencl_devices', return_value=records):
            code = module._child_main()
        return code, json.loads(output.getvalue())

    def test_child_recomputes_plan_from_runtime_and_refuses_before_gpu_execution(self):
        module = executor_module()
        records = [
            {'runtime_id': 'p0:d0', 'physical_id': 'pci:nv', 'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR',
             'vendor_key': 'NVIDIA', 'vendor': 'NVIDIA', 'device': object(),
             'max_mem_alloc_bytes_reported': 64 * MIB},
            {'runtime_id': 'p1:d0', 'physical_id': 'pci:amd', 'identity_confidence': 'RUNTIME_REPORTED_PCI_KHR',
             'vendor_key': 'AMD', 'vendor': 'AMD', 'device': object(),
             'max_mem_alloc_bytes_reported': 64 * MIB},
        ]
        payload = {'width': 512, 'batch': 8, 'layers': 8, 'policy_mib': 1,
                   'seed': 103004, 'device_ids': None, 'reverse': False,
                   'inject_corruption': False,
                   # Caller-provided metadata and plans must never be trusted.
                   'devices': [{'runtime_id': 'p99:d99', 'vendor_key': 'WARP'}],
                   'prepared_plan': {'status': 'PASS'}}
        with mock.patch.object(module, '_execute_gpu', side_effect=AssertionError('GPU allocation/execution reached')) as run:
            code, result = self._run_child_payload(module, payload, records)
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'REFUSED')
        self.assertTrue('budget' in result['reason'].lower() or 'policy' in result['reason'].lower())
        run.assert_not_called()

    def test_child_revalidates_direct_payload_bounds_before_enumeration(self):
        module = executor_module()
        payload = {'width': 513, 'batch': 8, 'layers': 8, 'policy_mib': 9,
                   'seed': 103004, 'device_ids': None, 'reverse': False,
                   'inject_corruption': False}
        output = io.StringIO()
        with mock.patch.object(module.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(module.sys, 'stdout', output), \
                mock.patch.object(module, 'enumerate_opencl_devices', side_effect=AssertionError('invalid payload enumerated devices')) as enumerate_devices:
            code = module._child_main()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['status'], 'REFUSED')
        enumerate_devices.assert_not_called()


if __name__ == '__main__':
    unittest.main()
