"""Pinned-DMA pipelined transport: design + pure simulator.

Architecture (staged, NOT P2P -- the CPU orchestrates, GPU DMA engines move):

    Intel VRAM --(DMA chunk k)--> pinned host RAM --(DMA chunk k)--> NVIDIA VRAM

Overlap: NVIDIA begins consuming chunk k while Intel produces chunk k+1.
This module simulates that timeline in pure Python so chunk sizing and the
overlap gain vs naive sequential bounce can be reasoned about and unit
tested with no GPU present. Measured bandwidth numbers come from the
harnesses; this module only computes with them.

Evidence class of any simulator output: PLAUSIBLE at best. Only a run on
the real two-card rig with control R + N1 can promote a number to PROVEN.
"""

from __future__ import annotations

import math


def validate_positive(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    if not math.isfinite(float(value)) or value <= 0:
        raise ValueError("%s must be finite and positive" % name)
    return float(value)


def chunk_plan(object_bytes: int, chunk_bytes: int) -> dict:
    """Split an object into chunk descriptors (pure, testable)."""
    if isinstance(object_bytes, bool) or not isinstance(object_bytes, int):
        raise ValueError("object_bytes must be an int")
    if isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int):
        raise ValueError("chunk_bytes must be an int")
    if object_bytes <= 0 or chunk_bytes <= 0:
        raise ValueError("sizes must be positive")
    n = (object_bytes + chunk_bytes - 1) // chunk_bytes
    chunks = []
    for i in range(n):
        start = i * chunk_bytes
        size = min(chunk_bytes, object_bytes - start)
        chunks.append({"index": i, "offset": start, "size": size,
                       "state": "PLANNED"})
    return {"object_bytes": object_bytes, "chunk_bytes": chunk_bytes,
            "chunk_count": n, "chunks": chunks}


def simulate_pipeline(object_bytes: int, chunk_bytes: int,
                       intel_to_host_gbps: float,
                       host_to_nvidia_gbps: float) -> dict:
    """Two-stage pipeline timeline (seconds) vs sequential baseline.

    Stage A: Intel VRAM -> pinned host. Stage B: pinned host -> NVIDIA VRAM.
    Chunk k's stage B can start when chunk k's stage A finishes; stage A of
    k+1 runs concurrently. Per-chunk times derive from the two one-way
    bandwidths. Returns per-chunk schedule plus totals and overlap gain.
    """
    plan = chunk_plan(object_bytes, chunk_bytes)
    bw_a = validate_positive("intel_to_host_gbps", intel_to_host_gbps)
    bw_b = validate_positive("host_to_nvidia_gbps", host_to_nvidia_gbps)
    gbps_to_Bps = 1e9
    t_a_done = 0.0
    t_b_done = 0.0
    schedule = []
    for ch in plan["chunks"]:
        a_dur = ch["size"] / (bw_a * gbps_to_Bps)
        b_dur = ch["size"] / (bw_b * gbps_to_Bps)
        a_start = t_a_done
        a_end = a_start + a_dur
        # Stage B needs this chunk's A done AND the B engine free.
        b_start = max(a_end, t_b_done)
        b_end = b_start + b_dur
        t_a_done = a_end
        t_b_done = b_end
        schedule.append({"index": ch["index"], "size": ch["size"],
                         "a_start": a_start, "a_end": a_end,
                         "b_start": b_start, "b_end": b_end})
    pipelined = t_b_done
    # Sequential baseline: every chunk fully A then B before the next chunk.
    total_a = object_bytes / (bw_a * gbps_to_Bps)
    total_b = object_bytes / (bw_b * gbps_to_Bps)
    sequential = total_a + total_b
    return {"schedule": schedule, "pipelined_seconds": pipelined,
            "sequential_seconds": sequential,
            "overlap_gain": sequential / pipelined if pipelined > 0 else 1.0,
            "evidence": "PLAUSIBLE",
            "note": ("simulator only: replace bandwidth inputs with harness "
                     "measurements; staged transport, never direct P2P")}
