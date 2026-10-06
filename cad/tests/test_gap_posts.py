"""Independent geometric gates for posts between the upright GPU bodies."""
import importlib.util
from pathlib import Path
import unittest


def core_module():
    path = Path(__file__).resolve().parents[1] / 'integrated_core.py'
    spec = importlib.util.spec_from_file_location('tested_integrated_core', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def overlap_volume(a, b):
    volume = 1.0
    for axis in range(3):
        volume *= max(0.0, min(a['origin_mm'][axis] + a['size_mm'][axis],
                              b['origin_mm'][axis] + b['size_mm'][axis]) -
                      max(a['origin_mm'][axis], b['origin_mm'][axis]))
    return volume


class GapPostGeometryTests(unittest.TestCase):
    def test_frame_bounds_follow_actual_post_and_beam_height(self):
        core = core_module()
        for profile, height in [('compact', 150.0), ('universal', 199.0)]:
            with self.subTest(profile=profile):
                layout = core.plan_layout(core.default_config(profile))
                self.assertEqual(layout['printed_bbox_mm'], [188.0, 200.0, height])
                self.assertEqual(layout['print_bbox_mm'], [200.0, 188.0, height])
                self.assertEqual(layout['post_height_mm'], height)
                self.assertEqual(layout['beam_top_mm'], height)

    def test_no_post_intersects_any_gpu_body(self):
        core = core_module()
        for profile in ['compact', 'universal']:
            layout = core.plan_layout(core.default_config(profile))
            self.assertEqual(len(layout['post_boxes']), 4)
            for post in layout['post_boxes']:
                for card in layout['cards']:
                    with self.subTest(profile=profile, card=card['bay'], post=post['origin_mm']):
                        self.assertEqual(overlap_volume(post, card), 0.0)

    def test_each_gap_has_positive_clearance_on_both_sides(self):
        core = core_module()
        config = core.default_config()
        for card, thickness in zip(config['cards'][:3], [60, 40, 50]):
            card['thickness_mm'] = thickness
        layout = core.plan_layout(config)
        for index in range(2):
            left, right = layout['cards'][index:index + 2]
            left_edge = left['origin_mm'][0] + left['size_mm'][0]
            right_edge = right['origin_mm'][0]
            for post in layout['post_boxes'][index * 2:index * 2 + 2]:
                self.assertAlmostEqual(post['origin_mm'][0] - left_edge, 1.0)
                self.assertAlmostEqual(right_edge - post['origin_mm'][0] - post['size_mm'][0], 1.0)

    def test_posts_end_below_rolled_card(self):
        core = core_module()
        layout = core.plan_layout(core.default_config('universal'))
        for post in layout['post_boxes']:
            self.assertLess(post['origin_mm'][2] + post['size_mm'][2], layout['cards'][3]['origin_mm'][2])

    def test_d_thickness_can_overhang_without_inflating_print_height(self):
        core = core_module()
        low, high = core.default_config(), core.default_config()
        low['cards'][3]['thickness_mm'] = 10
        high['cards'][3]['thickness_mm'] = 120
        low, high = core.plan_layout(low), core.plan_layout(high)
        self.assertEqual(low['printed_bbox_mm'], high['printed_bbox_mm'])
        self.assertNotEqual(low['gpu_bbox_mm'], high['gpu_bbox_mm'])

    def test_tall_frame_is_refused_without_clipping(self):
        core = core_module()
        config = core.default_config()
        for card in config['cards'][:3]:
            card['height_mm'] = 250
        with self.assertRaises(ValueError):
            core.plan_layout(config)

    def test_posts_that_fill_or_exceed_gap_are_refused(self):
        core = core_module()
        for width in [12, 14]:
            config = core.default_config()
            config['post_mm'] = width
            with self.subTest(width=width), self.assertRaises(ValueError):
                core.plan_layout(config)


if __name__ == '__main__':
    unittest.main()
