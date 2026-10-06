"""Unit tests for j_link.transport. Pure stdlib, no GPU required."""
import unittest

from j_link.transport import (
    DIRECT_P2P, EXTERNAL_MEMORY, SHARED_ZERO_COPY, PINNED_DMA_PIPELINE,
    HOST_STAGING, TRUE_DIRECT_P2P, PEER_DMA, ORDERED,
    PROVEN, BLOCKED, PLAUSIBLE,
    check_terminology, describe_pool, empty_capabilities, is_direct,
    select_transport,
)


class TerminologyTest(unittest.TestCase):
    def test_staged_never_direct(self):
        self.assertFalse(is_direct(HOST_STAGING))
        self.assertFalse(is_direct(PINNED_DMA_PIPELINE))
        self.assertFalse(is_direct(PEER_DMA))
        self.assertTrue(is_direct(TRUE_DIRECT_P2P))
        self.assertTrue(is_direct(DIRECT_P2P))
        self.assertTrue(is_direct(EXTERNAL_MEMORY))
        self.assertTrue(is_direct(SHARED_ZERO_COPY))

    def test_ordered_hierarchy(self):
        self.assertEqual(ORDERED, (TRUE_DIRECT_P2P, DIRECT_P2P,
                                   EXTERNAL_MEMORY, SHARED_ZERO_COPY,
                                   PEER_DMA, PINNED_DMA_PIPELINE,
                                   HOST_STAGING))

    def test_mislabel_raises(self):
        with self.assertRaises(ValueError):
            check_terminology(HOST_STAGING, "direct P2P")
        with self.assertRaises(ValueError):
            check_terminology(PINNED_DMA_PIPELINE, "Direct P2P link")
        # Correct labels pass silently.
        check_terminology(HOST_STAGING, "host staging baseline")
        check_terminology(PINNED_DMA_PIPELINE, "pinned DMA pipeline (staged)")


class SelectionTest(unittest.TestCase):
    def test_default_is_host_staging(self):
        sel = select_transport(empty_capabilities())
        self.assertEqual(sel["transport"], HOST_STAGING)
        self.assertFalse(sel["direct"])

    def test_direct_requires_residency_evidence(self):
        caps = empty_capabilities()
        caps["direct_p2p"] = {"available": True, "residency_evidence": False,
                              "evidence": PROVEN, "detail": "success code only"}
        sel = select_transport(caps)
        # A success code without both-endpoint residency must NOT select P2P.
        self.assertNotEqual(sel["transport"], DIRECT_P2P)

    def test_direct_with_residency_wins(self):
        caps = empty_capabilities()
        caps["direct_p2p"] = {"available": True, "residency_evidence": True,
                              "evidence": PROVEN, "detail": "control R PASS"}
        caps["pinned_dma_pipeline"] = {"available": True, "evidence": PLAUSIBLE,
                                       "detail": "dma both ways"}
        sel = select_transport(caps)
        self.assertEqual(sel["transport"], DIRECT_P2P)
        self.assertTrue(sel["direct"])

    def test_pipeline_beats_host_staging(self):
        caps = empty_capabilities()
        caps["pinned_dma_pipeline"] = {"available": True, "evidence": PLAUSIBLE,
                                       "detail": "both DMA to one pinning"}
        sel = select_transport(caps)
        self.assertEqual(sel["transport"], PINNED_DMA_PIPELINE)
        self.assertFalse(sel["direct"])

    def test_true_p2p_needs_proven_residency(self):
        caps = empty_capabilities()
        caps["true_direct_p2p"] = {"available": True,
                                   "residency_evidence": True,
                                   "evidence": PLAUSIBLE,
                                   "detail": "residency claimed, not proven"}
        sel = select_transport(caps)
        # PLAUSIBLE residency must NOT unlock the TRUE tier.
        self.assertNotEqual(sel["transport"], TRUE_DIRECT_P2P)

    def test_true_p2p_wins_when_proven(self):
        caps = empty_capabilities()
        caps["true_direct_p2p"] = {"available": True,
                                   "residency_evidence": True,
                                   "evidence": PROVEN,
                                   "detail": "control R PASS both endpoints"}
        caps["direct_p2p"] = {"available": True, "residency_evidence": True,
                              "evidence": PROVEN, "detail": "control R PASS"}
        sel = select_transport(caps)
        self.assertEqual(sel["transport"], TRUE_DIRECT_P2P)
        self.assertTrue(sel["direct"])

    def test_peer_dma_between_shared_and_pipeline(self):
        caps = empty_capabilities()
        caps["peer_dma"] = {"available": True, "evidence": PLAUSIBLE,
                            "detail": "SDMA moves bytes, staging unproven"}
        caps["pinned_dma_pipeline"] = {"available": True, "evidence": PLAUSIBLE,
                                       "detail": "both DMA to one pinning"}
        sel = select_transport(caps)
        self.assertEqual(sel["transport"], PEER_DMA)
        self.assertFalse(sel["direct"])
        with self.assertRaises(ValueError):
            check_terminology(PEER_DMA, "direct P2P")

    def test_external_memory_order(self):
        caps = empty_capabilities()
        caps["external_memory"] = {"available": True, "evidence": PROVEN,
                                   "detail": "import verified"}
        caps["shared_zero_copy"] = {"available": True, "evidence": PROVEN,
                                    "detail": "shared map"}
        sel = select_transport(caps)
        self.assertEqual(sel["transport"], EXTERNAL_MEMORY)


class PoolTest(unittest.TestCase):
    def test_pool_never_coherent(self):
        pool = describe_pool([
            {"id": "GPU0", "vendor": "nvidia", "dedicated_bytes": 16 << 30,
             "kind": "DEDICATED"},
            {"id": "GPU1", "vendor": "intel", "dedicated_bytes": 24 << 30,
             "kind": "DEDICATED"},
        ])
        self.assertFalse(pool["physically_coherent"])
        self.assertEqual(pool["aggregate_dedicated_bytes"], 40 << 30)

    def test_shared_host_not_counted_as_dedicated(self):
        pool = describe_pool([
            {"id": "iGPU", "vendor": "amd", "dedicated_bytes": 8 << 30,
             "kind": "SHARED_HOST"},
        ])
        self.assertEqual(pool["aggregate_dedicated_bytes"], 0)
        self.assertEqual(pool["aggregate_shared_host_bytes"], 8 << 30)


if __name__ == "__main__":
    unittest.main()
