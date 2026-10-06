"""Unit tests for the AMD probe helpers and future-matrix runner."""
import unittest

from j_link.amd_future_matrix import PAIRS, TESTS, build_matrix
from j_link.amd_probe import KNOWN_SHARED_DEVICES, NO_AMD


def _classify(instance_id):
    upper = instance_id.upper()
    if "VEN_1002" not in upper:
        return None
    if any(tag in upper for tag in KNOWN_SHARED_DEVICES):
        return "SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM"
    return "DISCRETE_CANDIDATE"


class ClassifyTest(unittest.TestCase):
    def test_raphael_igpu_is_shared(self):
        self.assertEqual(
            _classify(r"PCI\VEN_1002&DEV_164E&SUBSYS_164E1849&REV_C6\4&1A9C2D8A&0&0041"),
            "SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM")

    def test_discrete_candidate(self):
        self.assertEqual(
            _classify(r"PCI\VEN_1002&DEV_744C&SUBSYS_00000000&REV_C8\4&1234&0&00"),
            "DISCRETE_CANDIDATE")

    def test_non_amd_ignored(self):
        self.assertIsNone(
            _classify(r"PCI\VEN_10DE&DEV_2C05&SUBSYS_00000000\4&5678&0&00"))

    def test_no_amd_sentence(self):
        self.assertEqual(NO_AMD, "NO_COMPATIBLE_AMD_GPU_THIS_HOST")


class MatrixTest(unittest.TestCase):
    def test_six_directions_present(self):
        pairs = {(s, d) for s, d, _ in PAIRS}
        for expect in (("NVIDIA_RTX5070TI", "AMD_DISCRETE"),
                       ("AMD_DISCRETE", "NVIDIA_RTX5070TI"),
                       ("NVIDIA_RTX5070TI", "INTEL_B60"),
                       ("INTEL_B60", "NVIDIA_RTX5070TI"),
                       ("INTEL_B60", "AMD_DISCRETE"),
                       ("AMD_DISCRETE", "INTEL_B60")):
            self.assertIn(expect, pairs)

    def test_no_symmetry_assumption(self):
        by_pair = {}
        for src, dst, reason in PAIRS:
            by_pair.setdefault((src, dst), []).append(reason)
        fwd = by_pair[("NVIDIA_RTX5070TI", "AMD_DISCRETE")]
        rev = by_pair[("AMD_DISCRETE", "NVIDIA_RTX5070TI")]
        # Each direction carries its own entry; neither implies the other.
        self.assertEqual(len(fwd), 1)
        self.assertEqual(len(rev), 1)

    def test_cell_count(self):
        matrix = build_matrix()
        self.assertEqual(len(matrix), len(PAIRS) * len(TESTS))
        self.assertTrue(all(m["status"] == "NOT_CHECKED" for m in matrix))


if __name__ == "__main__":
    unittest.main()
