"""GPU-free tests for truthful per-stage error aggregation."""
from pathlib import Path
import sys
import unittest

J_LINK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(J_LINK))
import opencl_executor as executor


class StageErrorAggregation(unittest.TestCase):
    def test_finite_stage_errors_keep_the_maximum(self):
        self.assertEqual(executor._max_stage_abs_error([0.0, 0.25, 0.125]), 0.25)

    def test_mixed_finite_and_unknown_stage_errors_report_unknown(self):
        self.assertIsNone(executor._max_stage_abs_error([0.0, 1.5e-6, None, 2.0e-6]))

    def test_all_unknown_stage_errors_report_unknown(self):
        self.assertIsNone(executor._max_stage_abs_error([None, None]))

    def test_empty_stage_error_sequence_keeps_empty_case_default(self):
        self.assertEqual(executor._max_stage_abs_error([]), 0.0)


if __name__ == '__main__':
    unittest.main()
