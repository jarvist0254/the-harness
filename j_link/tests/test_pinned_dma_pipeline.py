"""Unit tests for the pinned-DMA pipeline simulator. No GPU required."""
import unittest

from j_link.pinned_dma_pipeline import chunk_plan, simulate_pipeline


class ChunkPlanTest(unittest.TestCase):
    def test_even_split(self):
        plan = chunk_plan(1024, 256)
        self.assertEqual(plan["chunk_count"], 4)
        self.assertEqual([c["size"] for c in plan["chunks"]], [256] * 4)

    def test_ragged_tail(self):
        plan = chunk_plan(1000, 256)
        self.assertEqual(plan["chunk_count"], 4)
        self.assertEqual(plan["chunks"][-1]["size"], 232)
        self.assertEqual(sum(c["size"] for c in plan["chunks"]), 1000)

    def test_rejects_bad_sizes(self):
        with self.assertRaises(ValueError):
            chunk_plan(0, 256)
        with self.assertRaises(ValueError):
            chunk_plan(1024, -1)


class SimulateTest(unittest.TestCase):
    def test_pipeline_beats_sequential(self):
        sim = simulate_pipeline(1 << 30, 64 << 20, 20.0, 20.0)
        self.assertLess(sim["pipelined_seconds"], sim["sequential_seconds"])
        self.assertGreater(sim["overlap_gain"], 1.5)

    def test_overlap_means_early_consume(self):
        # With equal 10 GB/s stages and 4 chunks, chunk 0's B must finish
        # long before the whole object arrives (the point of pipelining).
        sim = simulate_pipeline(256 << 20, 64 << 20, 10.0, 10.0)
        first_b_end = sim["schedule"][0]["b_end"]
        self.assertLess(first_b_end, sim["pipelined_seconds"] * 0.5)

    def test_single_chunk_equals_sequential(self):
        sim = simulate_pipeline(1 << 20, 1 << 20, 10.0, 10.0)
        self.assertAlmostEqual(sim["pipelined_seconds"],
                               sim["sequential_seconds"], places=9)


if __name__ == "__main__":
    unittest.main()
