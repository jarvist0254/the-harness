"""Unit tests for j_link.feed_measurements. No GPU required."""
import unittest

from j_link.feed_measurements import (
    build_caps_from_measurements, load_stream_bench_receipt,
    pick_stage_bandwidth, plan_transfer,
)
from j_link.transport import PINNED_DMA_PIPELINE


def _canned():
    return {"status": "MEASURED", "evidence": "PROVEN",
            "device": "NVIDIA GeForce RTX 5070 Ti", "cc": [12, 0],
            "overlap_64MiB_gain": 1.42,
            "cases": [
                {"name": "pinned_8388608", "bytes": 8388608,
                 "seconds": 0.001, "gbps": 16.0, "checksum_ok": True},
                {"name": "pinned_67108864", "bytes": 67108864,
                 "seconds": 0.006, "gbps": 22.0, "checksum_ok": True},
                {"name": "pageable_67108864", "bytes": 67108864,
                 "seconds": 0.012, "gbps": 11.0, "checksum_ok": True},
            ]}


class ReceiptTest(unittest.TestCase):
    def test_loads_good_receipt(self):
        cases = load_stream_bench_receipt(_canned())
        self.assertIn("pinned_67108864", cases)

    def test_refuses_unmeasured(self):
        bad = _canned()
        bad["status"] = "NOT_CHECKED"
        with self.assertRaises(ValueError):
            load_stream_bench_receipt(bad)

    def test_refuses_checksum_failure(self):
        bad = _canned()
        bad["cases"][1]["checksum_ok"] = False
        with self.assertRaises(ValueError):
            load_stream_bench_receipt(bad)


class PlanTest(unittest.TestCase):
    def test_selects_pipeline_not_p2p(self):
        plan = plan_transfer(_canned(), 1 << 30)
        sel = plan["transport_selection"]
        self.assertEqual(sel["transport"], PINNED_DMA_PIPELINE)
        self.assertFalse(sel["direct"])
        self.assertGreater(plan["pipeline"]["overlap_gain"], 1.0)

    def test_overrides_break_symmetry(self):
        cases = load_stream_bench_receipt(_canned())
        bw = pick_stage_bandwidth(
            cases, stage_bw_overrides={"host_to_nvidia": 11.0})
        self.assertFalse(bw["symmetric_assumption"])
        self.assertEqual(bw["host_to_nvidia"], 11.0)
        self.assertEqual(bw["intel_to_host"], 22.0)

    def test_caps_never_claim_proven_pipeline(self):
        caps = build_caps_from_measurements(
            load_stream_bench_receipt(_canned()))
        self.assertEqual(caps["pinned_dma_pipeline"]["evidence"],
                         "PLAUSIBLE")


if __name__ == "__main__":
    unittest.main()
