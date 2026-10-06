"""J-Link transport abstraction: Intel Arc Pro B60 + NVIDIA RTX 5070 Ti fabric.

Frozen-boundary note: the pre-existing Intel-Intel P2P work is FROZEN and is
not touched here. This module is the NEW heterogeneous arm: it names the
transport hierarchy, probes capabilities, and selects the fastest *valid*
transport. It performs no GPU calls itself; harnesses fill the capability
dict and this module decides.

Terminology guard (hard rule): HOST_STAGING and PINNED_DMA_PIPELINE are never
direct P2P. `is_direct()` encodes that; selection reasons restate it.
"""

from __future__ import annotations

DIRECT_P2P = "DIRECT_P2P"
EXTERNAL_MEMORY = "EXTERNAL_MEMORY"
SHARED_ZERO_COPY = "SHARED_ZERO_COPY"
PINNED_DMA_PIPELINE = "PINNED_DMA_PIPELINE"
HOST_STAGING = "HOST_STAGING"
# Three-vendor arm additions (additive; existing names keep working):
# TRUE_DIRECT_P2P = peer path with PROVEN residency evidence, the only tier
# allowed to claim true cross-vendor P2P. PEER_DMA = GPU DMA engines move
# the payload (SDMA/copy engines) without CPU memcpy, but through mappings
# that control R has not proven staging-free -- never labeled direct.
TRUE_DIRECT_P2P = "TRUE_DIRECT_P2P"
PEER_DMA = "PEER_DMA"

ORDERED = (
    TRUE_DIRECT_P2P,
    DIRECT_P2P,
    EXTERNAL_MEMORY,
    SHARED_ZERO_COPY,
    PEER_DMA,
    PINNED_DMA_PIPELINE,
    HOST_STAGING,
)

# Evidence classification every result must carry.
PROVEN = "PROVEN"
DOCUMENTED = "DOCUMENTED"
PLAUSIBLE = "PLAUSIBLE"
FAILED = "FAILED"
BLOCKED = "BLOCKED"
EVIDENCE = (PROVEN, DOCUMENTED, PLAUSIBLE, FAILED, BLOCKED)


def is_direct(transport: str) -> bool:
    """True only for transports that keep the payload out of host memory."""
    return transport in (TRUE_DIRECT_P2P, DIRECT_P2P, EXTERNAL_MEMORY,
                         SHARED_ZERO_COPY)


def check_terminology(transport: str, label: str) -> None:
    """Raise if anyone labels a staged transport as direct P2P."""
    low = (label or "").lower().replace("-", " ").replace("_", " ")
    claims_direct = ("direct p2p" in low or "direct peer" in low
                     or low.strip() in ("p2p", "direct"))
    if claims_direct and not is_direct(transport):
        raise ValueError(
            "terminology violation: %s must never be labeled direct P2P"
            % transport)


def empty_capabilities() -> dict:
    """Capability dict harnesses fill. All peer paths default to absent."""
    return {
        # TRUE_DIRECT_P2P: TRUE_P2P grade -- peer path with PROVEN
        # both-endpoint residency evidence. The only tier that may claim
        # true cross-vendor P2P.
        "true_direct_p2p": {"available": False, "residency_evidence": False,
                            "evidence": BLOCKED, "detail": "unprobed"},
        # DIRECT_P2P: payload leaves source dedicated VRAM and arrives in
        # destination dedicated VRAM with no host-memory copy. Requires
        # residency evidence on both endpoints (control R), not just a
        # success code.
        "direct_p2p": {"available": False, "residency_evidence": False,
                       "evidence": BLOCKED, "detail": "unprobed"},
        # EXTERNAL_MEMORY: one vendor's allocation exported and imported by
        # the other (Vulkan/DMA-BUF/D3D12/CUDA-ext/L0-IPC) with the backing
        # still in dedicated VRAM.
        "external_memory": {"available": False, "evidence": BLOCKED,
                            "detail": "unprobed"},
        # SHARED_ZERO_COPY: both GPUs map the same allocation (BAR-exposed
        # or OS-shared) with no copy at all.
        "shared_zero_copy": {"available": False, "evidence": BLOCKED,
                             "detail": "unprobed"},
        # PEER_DMA: GPU DMA engines (SDMA/copy) move the payload without
        # CPU memcpy, but control R has not proven the path staging-free.
        # Never labeled direct; promotes only on residency evidence.
        "peer_dma": {"available": False, "evidence": BLOCKED,
                     "detail": "unprobed"},
        # PINNED_DMA_PIPELINE: both GPUs independently DMA against the same
        # pinned host allocation, chunked + overlapped. Host memory IS in
        # the data path: staged, not P2P.
        "pinned_dma_pipeline": {"available": False, "evidence": BLOCKED,
                                "detail": "unprobed"},
        # HOST_STAGING: explicit two-hop copy through host memory. Always
        # available as the baseline; never direct.
        "host_staging": {"available": True, "evidence": PROVEN,
                         "detail": "memcpy-class baseline always constructible"},
    }


def _gate_ok(section: dict) -> bool:
    return bool(isinstance(section, dict) and section.get("available") is True)


def select_transport(caps: dict) -> dict:
    """Pick the fastest valid transport from a capability dict.

    DIRECT_P2P additionally requires residency_evidence; without it the
    claim is downgraded even if a driver reports "available".
    Returns {"transport", "evidence", "reason", "direct"}.
    """
    if not isinstance(caps, dict):
        raise ValueError("caps must be a dict from empty_capabilities()")
    true_p2p = caps.get("true_direct_p2p", {})
    if (_gate_ok(true_p2p) and true_p2p.get("residency_evidence") is True
            and true_p2p.get("evidence") == PROVEN):
        return {"transport": TRUE_DIRECT_P2P,
                "evidence": PROVEN,
                "reason": ("peer path with PROVEN both-endpoint residency "
                           "evidence: true cross-vendor P2P"),
                "direct": True}
    direct = caps.get("direct_p2p", {})
    if _gate_ok(direct) and direct.get("residency_evidence") is True:
        return {"transport": DIRECT_P2P,
                "evidence": direct.get("evidence", PROVEN),
                "reason": "peer path with both-endpoint residency evidence",
                "direct": True}
    ext = caps.get("external_memory", {})
    if _gate_ok(ext):
        return {"transport": EXTERNAL_MEMORY,
                "evidence": ext.get("evidence", DOCUMENTED),
                "reason": "imported allocation backed outside host memory",
                "direct": True}
    shr = caps.get("shared_zero_copy", {})
    if _gate_ok(shr):
        return {"transport": SHARED_ZERO_COPY,
                "evidence": shr.get("evidence", DOCUMENTED),
                "reason": "single allocation mapped by both GPUs, no copy",
                "direct": True}
    peer = caps.get("peer_dma", {})
    if _gate_ok(peer):
        return {"transport": PEER_DMA,
                "evidence": peer.get("evidence", PLAUSIBLE),
                "reason": ("GPU DMA engines move bytes without CPU memcpy; "
                           "NOT proven staging-free: never direct P2P"),
                "direct": False}
    pipe = caps.get("pinned_dma_pipeline", {})
    if _gate_ok(pipe):
        return {"transport": PINNED_DMA_PIPELINE,
                "evidence": pipe.get("evidence", PLAUSIBLE),
                "reason": ("both GPUs DMA against one pinned host "
                           "allocation; staged, NOT direct P2P"),
                "direct": False}
    host = caps.get("host_staging", {})
    return {"transport": HOST_STAGING,
            "evidence": host.get("evidence", PROVEN),
            "reason": "explicit two-hop through host memory; NOT direct P2P",
            "direct": False}


def describe_pool(devices: list) -> dict:
    """Logical (not physically coherent) memory-pool view.

    devices: [{"id", "vendor", "dedicated_bytes", "kind"}]. kind is
    DEDICATED or SHARED_HOST. Returns totals split so callers cannot
    mistake summed capacity for one addressable heap.
    """
    total_dedicated = 0
    total_shared_host = 0
    members = []
    for dev in devices:
        dedicated = dev.get("dedicated_bytes") or 0
        kind = dev.get("kind", "UNKNOWN")
        if kind == "DEDICATED":
            total_dedicated += dedicated
        else:
            total_shared_host += dedicated
        members.append({"id": dev.get("id"), "vendor": dev.get("vendor"),
                        "kind": kind, "dedicated_bytes": dedicated})
    return {"members": members,
            "aggregate_dedicated_bytes": total_dedicated,
            "aggregate_shared_host_bytes": total_shared_host,
            "physically_coherent": False,
            "note": ("logical pool only: no single allocation spans vendors; "
                     "place whole layers/experts/stages per device")}

