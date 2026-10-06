"""Feed measured numbers into transport selection + pipeline planning.

Glue between the harnesses and the abstraction (heterogeneous arm):

    stream_bench --json  +  rtx5070ti_harness.py
        -> load_stream_bench_receipt / build_caps_from_measurements
        -> select_transport + simulate_pipeline
        -> one combined receipt

Assumption, stated not hidden: stream_bench reports ROUND-TRIP GB/s
(2*bytes/wall). Per-direction stage bandwidth is taken as that same rate,
i.e. symmetric H2D/D2H. If a later probe reports per-direction rates, pass
them explicitly via stage_bw_overrides.

Evidence rule: measured NVIDIA numbers promote the NVIDIA half only. The
Intel half is unmeasured until a B60 exists, so pinned_dma_pipeline stays
PLAUSIBLE (never PROVEN) until both halves are measured on a two-card rig
with control R + N1. Stdlib only.
"""

from __future__ import annotations

from j_link.pinned_dma_pipeline import simulate_pipeline
from j_link.transport import (empty_capabilities, select_transport,
                              PLAUSIBLE, PROVEN)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def load_stream_bench_receipt(obj: dict) -> dict:
    """Validate a stream_bench --json receipt; return {case_name: entry}."""
    _require(isinstance(obj, dict), "receipt must be an object")
    _require(obj.get("status") == "MEASURED",
             "stream_bench did not MEASURE (status=%r)" % obj.get("status"))
    cases = obj.get("cases")
    _require(isinstance(cases, list) and cases,
             "receipt has no cases list")
    out = {}
    for entry in cases:
        _require(isinstance(entry, dict), "case entry must be an object")
        for key in ("name", "bytes", "gbps", "checksum_ok"):
            _require(key in entry, "case missing %r" % key)
        _require(entry["checksum_ok"] is True,
                 "case %r failed checksum; refuses to plan on corrupt data"
                 % entry.get("name"))
        _require(entry["gbps"] > 0, "case %r has no bandwidth"
                 % entry.get("name"))
        out[entry["name"]] = entry
    return out


def pick_stage_bandwidth(cases: dict, size_label: str = "67108864",
                         stage_bw_overrides: dict | None = None) -> dict:
    """Per-direction stage rates (GB/s) for the pipeline simulator.

    Default: pinned round-trip rate at 64 MiB for both stages (symmetric
    assumption, documented above). Overrides: {"intel_to_host": x,
    "host_to_nvidia": y} from per-direction probes when available.
    """
    key = "pinned_%s" % size_label
    _require(key in cases, "no %r case in receipt" % key)
    base = float(cases[key]["gbps"])
    bw = {"intel_to_host": base, "host_to_nvidia": base,
          "basis": key, "symmetric_assumption": True}
    for stage in ("intel_to_host", "host_to_nvidia"):
        if stage_bw_overrides and stage in stage_bw_overrides:
            value = float(stage_bw_overrides[stage])
            _require(value > 0, "override %s must be positive" % stage)
            bw[stage] = value
            bw["symmetric_assumption"] = False
    return bw


def build_caps_from_measurements(cases: dict) -> dict:
    """Capability dict with the NVIDIA half PROVEN, Intel half pending."""
    caps = empty_capabilities()
    _require(any(name.startswith("pinned_") for name in cases),
             "no pinned cases; cannot claim DMA-against-pinned works")
    caps["pinned_dma_pipeline"] = {
        "available": True, "evidence": PLAUSIBLE,
        "detail": ("NVIDIA H2D/D2H vs pinned host PROVEN by stream_bench; "
                   "Intel DMA half unmeasured -- B60 pending. Staged, "
                   "NOT direct P2P.")}
    caps["host_staging"] = {"available": True, "evidence": PROVEN,
                            "detail": "baseline always constructible"}
    return caps


def plan_transfer(stream_bench_obj: dict, object_bytes: int,
                  chunk_bytes: int = 64 << 20,
                  stage_bw_overrides: dict | None = None) -> dict:
    """Combined receipt: selection + pipelined vs sequential timeline."""
    cases = load_stream_bench_receipt(stream_bench_obj)
    bw = pick_stage_bandwidth(cases,
                              stage_bw_overrides=stage_bw_overrides)
    caps = build_caps_from_measurements(cases)
    selection = select_transport(caps)
    sim = simulate_pipeline(object_bytes, chunk_bytes,
                            bw["intel_to_host"], bw["host_to_nvidia"])
    return {"transport_selection": selection,
            "stage_bandwidth_gbps": bw,
            "pipeline": {"pipelined_seconds": sim["pipelined_seconds"],
                         "sequential_seconds": sim["sequential_seconds"],
                         "overlap_gain": sim["overlap_gain"]},
            "evidence": PLAUSIBLE,
            "note": ("promotes to PROVEN only with both halves measured on "
                     "a two-card rig plus control R and N1")}
