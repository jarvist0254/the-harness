"""Actual-candidate regressions for plan_layout printed height.

Loads integrated_core.grok_corrected.py via CANDIDATE_PATH, otherwise the
adjacent file. Calls that module only. No FreeCAD, native kernel, or provider.
"""
import importlib.util
import os
import unittest
from pathlib import Path


def load_candidate():
    override = os.environ.get('CANDIDATE_PATH')
    path = Path(override) if override else Path(__file__).resolve().parent / 'integrated_core.grok_corrected.py'
    spec = importlib.util.spec_from_file_location('integrated_core_grok_corrected', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrintedHeightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_candidate()

    def layout(self, profile):
        return self.mod.plan_layout(self.mod.default_config(profile))

    def test_exact_printed_bbox_and_rotation(self):
        expected = {'compact': 150.0, 'universal': 199.0}
        for profile, height in expected.items():
            layout = self.layout(profile)
            self.assertEqual(layout['printed_bbox_mm'], [188.0, 200.0, height])
            self.assertEqual(layout['core_bbox_mm'], [188.0, 200.0, height])
            self.assertEqual(layout['print_bbox_mm'], [200.0, 188.0, height])
            self.assertEqual(layout['print_rotation'], 'Z_PLUS_90_DEGREES')
            self.assertEqual(layout['printed_bbox_mm'][2], layout['post_height_mm'])
            self.assertEqual(layout['post_height_mm'], layout['beam_top_mm'])
            self.assertEqual(layout['beam_top_mm'], height)
            self.assertEqual(len(layout['post_boxes']), 4)
            for post in layout['post_boxes']:
                self.assertEqual(post['size_mm'][2], height)

    def test_universal_d_support_and_body_remain_overhang(self):
        layout = self.layout('universal')
        card_d = layout['cards'][3]
        body_top = card_d['origin_mm'][2] + card_d['size_mm'][2]
        self.assertEqual(layout['d_support_elevation_mm'], 201.0)
        self.assertEqual(card_d['origin_mm'][2], 201.0)
        self.assertEqual(body_top, 269.0)
        self.assertGreater(layout['d_support_elevation_mm'], layout['beam_top_mm'])
        self.assertGreater(body_top, layout['printed_bbox_mm'][2])
        self.assertGreater(layout['gpu_bbox_mm'][2], layout['printed_bbox_mm'][2])
        self.assertEqual(layout['status'], 'DRAFT_UNQUALIFIED')
        self.assertFalse(layout['production_release'])
        self.assertIn('receiver_hole_datums', layout['unknown_interfaces'])

    def test_oversize_post_and_gap_gates(self):
        short_gap = self.mod.default_config('compact')
        short_gap['gap_mm'] = 11
        with self.assertRaises(ValueError):
            self.mod.plan_layout(short_gap)
        wide_post = self.mod.default_config('compact')
        wide_post['post_mm'] = wide_post['gap_mm']
        with self.assertRaises(ValueError):
            self.mod.plan_layout(wide_post)
        kept = self.layout('compact')
        self.assertGreaterEqual(kept['dimensions']['gap_mm'], 12)
        self.assertLess(kept['dimensions']['post_mm'], kept['dimensions']['gap_mm'])


if __name__ == '__main__':
    unittest.main()

