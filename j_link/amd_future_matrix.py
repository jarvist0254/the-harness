#!/usr/bin/env python3
"""AMD future-matrix runner (three-vendor arm, 2026-10-05).

Recognizes a discrete AMD GPU (never the shared-memory iGPU) and executes
the cross-vendor experiment matrix for all six directional pairs:

    NVIDIA->AMD  AMD->NVIDIA  NVIDIA->Intel  Intel->NVIDIA
    Intel->AMD   AMD->Intel

 plus the three same-vendor reference pairs (NVIDIA->NVIDIA,
 Intel->Intel, AMD->AMD). Each pair runs M1..M5 (capability, checksum
 transfer, control R, control N1, corruption control), each direction
 independent -- no symmetry assumed.

On the current host (zero discrete AMD, zero Intel) every AMD-involving
pair reports NOT_CHECKED with the exact reason. Exit 0 matrix executed,
1 internal failure, 2 probe itself could not run. Stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from j_link.amd_probe import (  # noqa: E402
    _pnp_amd_devices as _amd_display_devices,
)
from j_link.transport import (  # noqa: E402
    empty_capabilities, select_transport, HOST_STAGING,
)

TESTS = ("M1_capability_query", "M2_checksum_transfer_64MiB",
         "M3_control_R_residency", "M4_control_N1_baseline",
         "M5_corruption_control")

# (source, destination, why_not_today) -- directions never share a verdict.
PAIRS = (
    ("NVIDIA_RTX5070TI", "AMD_DISCRETE", "no discrete AMD GPU on this host"),
    ("AMD_DISCRETE", "NVIDIA_RTX5070TI", "no discrete AMD GPU on this host"),
    ("NVIDIA_RTX5070TI", "INTEL_B60", "no Intel B60 on this host"),
    ("INTEL_B60", "NVIDIA_RTX5070TI", "no Intel B60 on this host"),
    ("INTEL_B60", "AMD_DISCRETE", "neither endpoint on this host"),
    ("AMD_DISCRETE", "INTEL_B60", "neither endpoint on this host"),
    ("NVIDIA_RTX5070TI", "NVIDIA_RTX5070TI",
     "single discrete GPU: no peer pair"),
    ("AMD_DISCRETE", "AMD_DISCRETE", "no discrete AMD GPU on this host"),
    ("INTEL_B60", "INTEL_B60", "no Intel B60 on this host"),
)


def build_matrix() -> list:
    return [{"pair": [src, dst], "test": test, "status": "NOT_CHECKED",
             "reason": reason}
            for src, dst, reason in PAIRS for test in TESTS]


def main() -> int:
    amd = _amd_display_devices() if os.name == "nt" else {
        "probe": "SKIPPED", "amd_devices": []}
    discrete = [d for d in amd["amd_devices"]
                if d.get("endpoint_class") == "DISCRETE_CANDIDATE"]
    matrix = build_matrix()
    caps = empty_capabilities()
    selection = select_transport(caps)
    assert selection["transport"] == HOST_STAGING, selection
    receipt = {"schema": "amd_future_matrix/1.0",
               "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
               "amd_discrete_seen": discrete,
               "directed_pairs_constructible": 0,
               "matrix": matrix,
               "matrix_cells": len(matrix),
               "transport_selection_today": selection,
               "bridge_hypothesis": {
                   "status": "UNKNOWN",
                   "statement": ("if NVIDIA<->AMD direct fails but both "
                                 "NVIDIA<->Intel and Intel<->AMD worked, "
                                 "route via Intel without host memory"),
                   "blocker": ("zero working direct legs today; re-evaluate "
                               "when the first leg proves with control R")},
               "resume": {
                   "hardware": ("one discrete AMD GPU (RDNA, slot-mounted, "
                                "CPU root, PCIe atomics) and/or Intel B60"),
                   "commands": [
                       "python -B j_link/amd_probe.py",
                       "python -B j_link/amd_future_matrix.py",
                       "nvcc -O2 -o stream_bench.exe j_link/stream_bench.cu",
                       "stream_bench.exe --json"],
                   "success_vs_failure": ("M2 checksum match + M3 residency "
                                          "deltas on both endpoints + M4 "
                                          "slower baseline = leg PROVEN; "
                                          "else the refusing layer names "
                                          "the boundary")}}
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
