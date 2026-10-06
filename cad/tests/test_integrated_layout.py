import importlib.util
from pathlib import Path
import unittest


def module():
    path = Path(__file__).resolve().parents[1] / 'integrated_core.py'
    spec = importlib.util.spec_from_file_location('integrated_core', path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class IntegratedLayoutTests(unittest.TestCase):
    def test_fourth_card_rolls_same_fixture_dimensions(self):
        layout = module().plan_layout(module().default_config())
        self.assertEqual(len(layout['cards']), 4)
        self.assertEqual(layout['cards'][3]['size_mm'], [116.0, 199.0, 40.0])
        self.assertEqual(layout['cards'][3]['orientation'], 'ROLLED_90_DEGREES')
        self.assertEqual(layout['printed_bbox_mm'], [188.0, 200.0, 150.0])
        self.assertEqual(layout['print_bbox_mm'], [200.0, 188.0, 150.0])
        self.assertFalse(layout['measured_interfaces'])

    def test_body_gaps_and_independent_integrated_supports(self):
        layout = module().plan_layout(module().default_config())
        lower = layout['cards'][:3]
        self.assertEqual(lower[1]['origin_mm'][0] -
                         (lower[0]['origin_mm'][0] + lower[0]['size_mm'][0]), 12.0)
        self.assertEqual(layout['cards'][3]['origin_mm'][2] -
                         max(card['origin_mm'][2] + card['size_mm'][2] for card in lower), 12.0)
        self.assertEqual(set(layout['mount_bays']), {'A', 'B', 'C', 'D'})
        self.assertEqual(layout['frame_policy'], 'ONE_CONNECTED_CORE_NO_APPEND_D')
        self.assertEqual(layout['support_bodies'], ['BASE', 'POSTS', 'D_BEAMS', 'METAL_RAIL_CONCEPT'])

    def test_invalid_dimensions_and_fixed_print_limit_are_refused(self):
        core = module()
        for value in (True, -1, float('nan'), 0):
            config = core.default_config()
            config['gap_mm'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.plan_layout(config)
        config = core.default_config()
        config['core_width_mm'] = 201
        with self.assertRaises(ValueError):
            core.plan_layout(config)

    def test_universal_boxes_are_not_silently_certified(self):
        core = module()
        config = core.default_config('universal')
        layout = core.plan_layout(config)
        self.assertEqual(layout['cards'][3]['size_mm'], [165.0, 360.0, 68.0])
        self.assertEqual(layout['status'], 'DRAFT_UNQUALIFIED')
        self.assertGreater(layout['gpu_bbox_mm'][0], layout['printed_bbox_mm'][0])
        self.assertFalse(layout['production_release'])

    def test_structural_primitives_must_have_positive_sizes(self):
        core = module()
        for key, value in (('rail_depth_mm', 1), ('rail_depth_mm', 2),
                           ('core_depth_mm', 10), ('core_width_mm', 10)):
            config = core.default_config()
            config[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                core.plan_layout(config)

    def test_d_beam_cannot_intrude_into_lower_card_bodies(self):
        core = module()
        config = core.default_config()
        config['d_beam_height_mm'] = 20
        with self.assertRaises(ValueError):
            core.plan_layout(config)

    def test_all_cards_must_reach_both_nominal_support_footprints(self):
        core = module()
        for index in (0, 3):
            config = core.default_config()
            config['cards'][index]['length_mm'] = 100
            with self.subTest(bay=index), self.assertRaises(ValueError):
                core.plan_layout(config)

    def test_a_card_outside_core_cannot_claim_integral_support(self):
        core = module()
        config = core.default_config()
        for card, thickness in zip(config['cards'][:3], (1, 120, 120)):
            card['thickness_mm'] = thickness
        with self.assertRaises(ValueError):
            core.plan_layout(config)


if __name__ == '__main__':
    unittest.main()
