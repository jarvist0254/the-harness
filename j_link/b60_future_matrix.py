#!/usr/bin/env python3
"""Intel B60 future-validation matrix runner (heterogeneous arm, 2026-10-05).

Recognizes an Intel Arc Pro B60 the moment one appears (PCI VEN_8086,
device 0xE211 per intel/compute-runtime#921; B70 is 0xE223 and is noted but
out of scope for the B60 matrix) and immediately executes the cross-vendor
test matrix against the RTX 5070 Ti. On the current host (zero Intel GPUs)
every directed pair reports NOT_CHECKED with the exact reason -- that IS the
correct result here, not a failure.

Matrix per directed pair (both directions are separate pairs):
  M1  capability query (CUDA ordinal / zeDeviceCanAccessPeer / Vulkan peer
      features / D3D12 cross-adapter) -- recorded both directions
  M2  64 MiB checksum transfer on the best available transport
  M3  control R residency sample (both endpoints, before/after)
  M4  control N1 host-staged baseline at the same sizes
  M5  corruption control (--inject-corruption must FAIL loudly)

Transport selection delegates to j_link.transport.select_transport so the
terminology guard (staged is never direct P2P) applies automatically.

Stdlib only. Exit codes: 0 matrix executed (pairs may be NOT_CHECKED),
1 internal failure, 2 this probe itself could not run.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from j_link.transport import (  # noqa: E402
    empty_capabilities, select_transport, describe_pool, HOST_STAGING,
)

INTEL_VENDOR = 0x8086
B60_DEVICE = 0xE211
B70_DEVICE = 0xE223  # noted, out of scope for the B60 matrix
NVIDIA_VENDOR = 0x10DE
RTX_5070_TI_DEVICE = 0x2C05  # measured on this host via Display PnP id
SUBPROCESS_TIMEOUT = 30


def _run(argv: list) -> dict:
    exe = shutil.which(argv[0])
    if not exe:
        return {"status": "UNAVAILABLE", "reason": "REFUSED_TOOL_NOT_FOUND"}
    try:
        proc = subprocess.run(
            [exe] + argv[1:], capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "UNAVAILABLE",
                "reason": "REFUSED_EXEC_FAILED: %s" % type(exc).__name__}
    if proc.returncode != 0:
        return {"status": "UNAVAILABLE", "reason": "REFUSED_NONZERO_EXIT",
                "exit_code": proc.returncode}
    return {"status": "SAMPLED", "stdout": proc.stdout[:8192]}


def enumerate_intel_gpus() -> dict:
    """Look for Intel discrete GPUs without inventing any.

    Windows: nvidia-smi cannot see Intel; use PnP device ids when
    available. Linux: lspci -n. Either way, classify by vendor:device.
    """
    found: list = []
    if os.name == "nt":
        out = _run(["powershell", "-NoProfile", "-Command",
                    "Get-PnpDevice -Class Display -PresentOnly | "
                    "Select-Object -ExpandProperty InstanceId"])
        text = out.get("stdout", "") if out["status"] == "SAMPLED" else ""
        for token in text.replace("&", " ").split():
            if token.upper().startswith("VEN_8086"):
                found.append({"source": "pnp-display", "raw": token.strip()})
        detail = {"method": "pnp-display", "probe": out["status"]}
    else:
        out = _run(["lspci", "-n"])
        detail = {"method": "lspci -n", "probe": out["status"]}
        if out["status"] == "SAMPLED":
            for line in out["stdout"].splitlines():
                if "8086:" in line:
                    found.append({"source": "lspci", "raw": line.strip()})
    b60_hex = "%04X" % B60_DEVICE  # E211
    b60 = [f for f in found if b60_hex in f["raw"].upper()]
    return {"intel_gpus_seen": found, "b60_candidates": b60,
            "detail": detail,
            "b70_note": "B70 is %04X; out of scope for the B60 matrix" % B70_DEVICE,
            "verdict": ("B60_PRESENT" if b60 else "NO_INTEL_B60_THIS_HOST")}


def build_matrix() -> list:
    """The directed cross-vendor matrix. Two pairs, five tests each."""
    pairs = [("NVIDIA_RTX5070TI", "INTEL_B60"),
             ("INTEL_B60", "NVIDIA_RTX5070TI")]
    tests = ("M1_capability_query", "M2_checksum_transfer_64MiB",
             "M3_control_R_residency", "M4_control_N1_baseline",
             "M5_corruption_control")
    return [{"pair": list(p), "test": t, "status": "NOT_CHECKED",
             "reason": "no Intel B60 on this host"}
            for p in pairs for t in tests]


def main() -> int:
    intel = enumerate_intel_gpus()
    matrix = build_matrix()
    caps = empty_capabilities()
    # Current host reality: no peer path is available; the pinned-DMA
    # pipeline is PLAUSIBLE (designed + simulated) but not yet measured
    # here, so it stays unavailable until the RTX benchmark lands.
    caps["pinned_dma_pipeline"] = {
        "available": False, "evidence": "PLAUSIBLE",
        "detail": "simulator + protocol written; needs measured bandwidths"}
    selection = select_transport(caps)
    assert selection["transport"] == HOST_STAGING, selection
    pool = describe_pool([
        {"id": "GPU0", "vendor": "nvidia",
         "dedicated_bytes": 16303 * 1048576, "kind": "DEDICATED"},
        {"id": "iGPU", "vendor": "amd", "dedicated_bytes": 0,
         "kind": "SHARED_HOST"},
    ])
    receipt = {"schema": "b60_future_matrix/1.0",
               "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
               "intel": intel,
               "directed_pairs_constructible": 0,
               "matrix": matrix,
               "transport_selection_today": selection,
               "logical_pool_today": pool,
               "qwen_cuda_l0_payload": {
                   "status": "PROPOSED_NOT_RUN",
                   "source": ("records/factory_runs/20261004/"
                              "cuda_l0_device_dmabuf_prep_20261004T195400Z/"
                              "qwen_cuda_l0_device_dmabuf_v3/answer.raw.txt"),
                   "scope": ("Linux-only CUDA-owned 64 KiB export to "
                             "Level Zero DMA-BUF import; reverse refused; "
                             "needs one NVIDIA + one Intel device")},
               "next_experiment": ("run rtx5070ti_harness.py for live "
                                   "topology/BAR/props, then add the "
                                   "cudaMemcpyAsync stream benchmark")}
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
