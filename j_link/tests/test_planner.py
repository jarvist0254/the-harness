import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from planner import plan, PlanError


def fixture(capacities, sizes):
    return {'devices': [{'id': f'd{i}', 'physical_id': f'card{i}', 'free_mib': c,
                         'reserve_mib': 1, 'workspace_mib': 1}
                        for i, c in enumerate(capacities)],
            'blocks': [{'id': f'b{i}', 'memory_mib': n} for i, n in enumerate(sizes)]}


class CapacityTests(unittest.TestCase):
    def four_card_profile(self):
        path = Path(__file__).resolve().parents[1] / 'examples' / 'mixed.json'
        return json.loads(path.read_text(encoding='utf-8'))

    def test_four_card_profiles_preserve_order_and_device_budgets(self):
        for path in sorted((Path(__file__).resolve().parents[1] / 'examples').glob('*.json')):
            with self.subTest(profile=path.name):
                spec = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(len(spec['devices']), 4)
                self.assertTrue(spec['hypothetical'])
                self.assertEqual(len(spec['blocks']), 48)
                self.assertEqual([b['memory_mib'] for b in spec['blocks']], [512] * 48)
                self.assertEqual([(d['free_mib'], d['reserve_mib'], d['workspace_mib'])
                                  for d in spec['devices']], [(8192, 1024, 512)] * 4)
                result = plan(spec)
                self.assertEqual(result['block_memory_mib'], 24576)
                self.assertEqual(result['aggregate_budget_mib'], 26624)
                self.assertEqual([d['block_memory_mib'] for d in result['devices']], [6144] * 4)
                self.assertEqual([d['remaining_budget_mib'] for d in result['devices']], [512] * 4)
                self.assertEqual([b for d in result['devices'] for b in d['blocks']],
                                 [b['id'] for b in spec['blocks']])

    def test_three_cards_reject_same_four_card_workload(self):
        spec = self.four_card_profile()
        spec['devices'] = spec['devices'][:3]
        with self.assertRaisesRegex(PlanError, 'Total'):
            plan(spec)

    def test_fourth_card_backend_alias_cannot_add_capacity(self):
        spec = self.four_card_profile()
        spec['devices'][-1]['physical_id'] = spec['devices'][0]['physical_id']
        with self.assertRaisesRegex(PlanError, 'Duplicate'):
            plan(spec)

    def test_four_cards_reject_block_larger_than_each_budget(self):
        spec = self.four_card_profile()
        spec['blocks'] = [{'id': 'too_large', 'memory_mib': 6657}]
        with self.assertRaisesRegex(PlanError, 'Indivisible'):
            plan(spec)

    def test_optional_fifth_display_card_is_distinct_and_counted_once(self):
        spec = self.four_card_profile()
        baseline = plan(spec)
        self.assertEqual(len(baseline['devices']), 4)
        display = {'id': 'HOST_DISPLAY', 'physical_id': 'separate_display_card',
                   'vendor': 'NVIDIA', 'free_mib': 16384,
                   'reserve_mib': 1024, 'workspace_mib': 512}
        spec['devices'].append(display)
        result = plan(spec)
        self.assertEqual(len(result['devices']), 5)
        self.assertEqual(result['aggregate_free_mib'], 49152)
        self.assertEqual(result['aggregate_budget_mib'], 41472)
        self.assertEqual([b for d in result['devices'] for b in d['blocks']],
                         [b['id'] for b in spec['blocks']])
        alias = copy.deepcopy(display)
        alias['id'] = 'HOST_DISPLAY_OTHER_BACKEND'
        spec['devices'].append(alias)
        with self.assertRaisesRegex(PlanError, 'Duplicate'):
            plan(spec)

    def test_larger_than_one_card_fits_three(self):
        spec = fixture([12, 12, 12], [5] * 6)
        result = plan(spec)
        self.assertGreater(result['block_memory_mib'], max(d['budget_mib'] for d in result['devices']))
        self.assertEqual([d['block_memory_mib'] for d in result['devices']], [10, 10, 10])
        self.assertEqual([b for d in result['devices'] for b in d['blocks']], [b['id'] for b in spec['blocks']])

    def test_aliases_cannot_double_count_one_physical_card(self):
        spec = fixture([20, 20], [5])
        spec['devices'][1]['physical_id'] = 'card0'
        with self.assertRaisesRegex(PlanError, 'Duplicate'):
            plan(spec)

    def test_aggregate_does_not_fit_indivisible_block(self):
        with self.assertRaisesRegex(PlanError, 'Indivisible'):
            plan(fixture([10, 10, 10], [12]))

    def test_reserves_cannot_be_ignored(self):
        with self.assertRaisesRegex(PlanError, 'Total'):
            plan(fixture([10, 10], [7, 7, 3]))

    def test_order_can_make_aggregate_capacity_unusable(self):
        with self.assertRaisesRegex(PlanError, 'contiguous'):
            plan(fixture([8, 10], [7, 6]))

    def test_unequal_devices_and_unused_device(self):
        result = plan(fixture([2, 7, 12], [4, 5, 5]))
        self.assertEqual(result['devices'][0]['blocks'], [])
        self.assertTrue(all(d['remaining_budget_mib'] >= 0 for d in result['devices']))

    def test_negative_and_boolean_sizes_rejected(self):
        for value in [-1, True, 1.5]:
            with self.assertRaises(PlanError):
                plan(fixture([10], [value]))

    def test_duplicate_block_rejected(self):
        spec = fixture([20], [5, 5])
        spec['blocks'][1]['id'] = 'b0'
        with self.assertRaises(PlanError):
            plan(spec)


if __name__ == '__main__':
    unittest.main()
