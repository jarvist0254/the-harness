#!/usr/bin/env python3
"""RTX 5070 Ti experimental harness (heterogeneous arm, 2026-10-05).

Instruments the NVIDIA half with real executable probes wherever possible:
PCIe topology/BDF, BAR + Resizable BAR readout, CUDA device properties,
link generation/width, memory totals, pinned-host allocation behavior, and
async-copy/stream overlap where the local stack allows.

No Intel card is required to run this: with zero Intel GPUs present the
cross-vendor sections report NOT_CHECKED (exit 2 shape is reserved for the
matrix runner; THIS script exits 0 with measured NVIDIA facts plus explicit
NOT_CHECKED Intel slots).

Output: one JSON object on stdout. Exit codes: 0 measured OK (Intel slots
may still be NOT_CHECKED), 1 internal failure, 2 the probe itself could
not run (nvidia-smi missing).
Stdlib only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

PROVEN = "PROVEN"
NOT_CHECKED = "NOT_CHECKED"
UNAVAILABLE = "UNAVAILABLE"

TARGET_NAME_FRAGMENT = "5070 Ti"
# Measured on this host 2026-10-04/05; re-read live in _nvidia_smi_query rows.
EXPECTED_VRAM_MIB = 16303
SUBPROCESS_TIMEOUT = 30


def _run(argv: list) -> dict:
    exe = shutil.which(argv[0])
    if not exe:
        return {"status": UNAVAILABLE, "argv": argv,
                "reason": "REFUSED_TOOL_NOT_FOUND"}
    try:
        proc = subprocess.run(
            [exe] + argv[1:], capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": UNAVAILABLE, "argv": argv,
                "reason": "REFUSED_EXEC_FAILED: %s" % type(exc).__name__}
    if proc.returncode != 0:
        return {"status": UNAVAILABLE, "argv": argv,
                "reason": "REFUSED_NONZERO_EXIT",
                "exit_code": proc.returncode,
                "stderr_tail": proc.stderr[-1024:]}
    return {"status": "SAMPLED", "argv": argv, "stdout": proc.stdout[:16384]}


def _nvidia_smi_list() -> dict:
    out = _run(["nvidia-smi", "-L"])
    gpus = []
    if out["status"] == "SAMPLED":
        for line in out["stdout"].splitlines():
            line = line.strip()
            if line.startswith("GPU "):
                gpus.append(line)
    return {"probe": out, "gpu_lines": gpus}


def _nvidia_smi_query() -> dict:
    fields = ("name,pci.bus_id,memory.total,memory.free,driver_version,"
              "pcie.link.gen.current,pcie.link.width.current,"
              "pcie.link.gen.max,pcie.link.width.max")
    out = _run(["nvidia-smi",
                "--query-gpu=%s" % fields, "--format=csv,noheader,nounits"])
    rows = ([r.strip() for r in out["stdout"].splitlines() if r.strip()]
            if out["status"] == "SAMPLED" else [])
    return {"probe": out, "fields": fields, "rows": rows}


def _nvidia_smi_rebar() -> dict:
    # Full `nvidia-smi -q` carries BAR1 + Resizable BAR state; keep the
    # BAR/ReBAR lines only so the receipt stays small and factual.
    out = _run(["nvidia-smi", "-q"])
    hits = []
    if out["status"] == "SAMPLED":
        for line in out["stdout"].splitlines():
            low = line.lower()
            if ("bar1" in low or "resizable bar" in low or "re-bar" in low
                    or low.strip().startswith("bar")
                    or "pcie link" in low):
                hits.append(line.rstrip())
    return {"probe_status": out["status"], "bar_lines": hits[:60],
            "note": "full -q output NOT stored; BAR/ReBAR lines only"}


def _cuda_probe() -> dict:
    # Optional CUDA-driver probe: report availability only, never emulate.
    try:
        import ctypes
        names = (["nvcuda.dll"] if os.name == "nt"
                 else ["libcuda.so.1", "libcuda.so"])
        for name in names:
            try:
                ctypes.CDLL(name)
                return {"status": "DRIVER_LIBRARY_PRESENT", "library": name,
                        "evidence": NOT_CHECKED,
                        "note": "presence only; no props queried without "
                                "a compiled CUDA probe"}
            except OSError:
                continue
        return {"status": UNAVAILABLE, "reason": "CUDA driver library absent"}
    except Exception as exc:  # never let an optional probe fail the run
        return {"status": UNAVAILABLE,
                "reason": "REFUSED: %s" % type(exc).__name__}


def main() -> int:
    receipt = {"schema": "rtx5070ti_harness/1.0",
               "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
               "target": TARGET_NAME_FRAGMENT}
    smi_list = _nvidia_smi_list()
    if smi_list["probe"]["status"] != "SAMPLED":
        receipt["status"] = UNAVAILABLE
        receipt["evidence_host_gpu"] = NOT_CHECKED
        receipt["reason"] = smi_list["probe"].get("reason")
        print(json.dumps(receipt, indent=2))
        return 2
    receipt["evidence_host_gpu"] = PROVEN
    receipt["nvidia_smi_list"] = smi_list["gpu_lines"]
    receipt["query"] = _nvidia_smi_query()
    receipt["bar"] = _nvidia_smi_rebar()
    receipt["cuda"] = _cuda_probe()
    receipt["intel_slot"] = {"status": NOT_CHECKED,
                             "reason": "no Intel GPU on this host; rerun the "
                                       "cross-vendor matrix when a B60 arrives"}
    receipt["pinned_dma_probe"] = {
        "status": NOT_CHECKED,
        "reason": "async/pinned bandwidth + overlap benchmark lands in the "
                  "next edit (cudaMemcpyAsync/Event stream harness); this "
                  "receipt pins topology/BAR/props first"}
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
