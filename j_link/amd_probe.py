#!/usr/bin/env python3
"""AMD hardware probe (three-vendor arm, 2026-10-05).

Identifies AMD GPUs without inventing any: model, PCI IDs, discrete vs
integrated (an iGPU on shared host memory is NOT a P2P endpoint),
driver/ROCm/HIP/Vulkan stack presence, and peer-access tooling.

Output: one JSON object on stdout. Exit 0 probed OK (AMD absent is a
finding, not an error), 1 internal failure, 2 the probe itself could not
run. Stdlib only. Never labels shared host memory as dedicated VRAM.
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
NO_AMD = "NO_COMPATIBLE_AMD_GPU_THIS_HOST"
SUBPROCESS_TIMEOUT = 30

# AMD display vendor id; Raphael iGPU device seen on this host.
AMD_VENDOR = "VEN_1002"
KNOWN_SHARED_DEVICES = ("DEV_164E",)  # Raphael iGPU class, shared host mem


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
    return {"status": "SAMPLED", "argv": argv[0], "stdout": proc.stdout[:8192]}


def _pnp_amd_devices() -> dict:
    """Windows: enumerate Display PnP ids, keep AMD ones with class."""
    out = _run(["powershell", "-NoProfile", "-Command",
                "Get-PnpDevice -Class Display -PresentOnly | "
                "Select-Object FriendlyName, InstanceId | "
                "ConvertTo-Json -Compress"])
    devices = []
    if out["status"] == "SAMPLED":
        try:
            raw = json.loads(out["stdout"])
        except ValueError:
            raw = None
        rows = ([raw] if isinstance(raw, dict) else
                (raw if isinstance(raw, list) else []))
        for row in rows:
            iid = str(row.get("InstanceId", ""))
            if AMD_VENDOR in iid.upper():
                upper = iid.upper()
                shared = any(tag in upper for tag in KNOWN_SHARED_DEVICES)
                devices.append({
                    "name": row.get("FriendlyName"),
                    "instance_id": iid,
                    "endpoint_class": ("SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM"
                                       if shared else "DISCRETE_CANDIDATE"),
                })
    return {"probe": out["status"], "amd_devices": devices}


def _tooling() -> dict:
    """ROCm/HIP/Vulkan stack presence. Presence only, never capability."""
    tools = {}
    for tool, argv in (
            ("amd-smi", ["amd-smi", "list"]),
            ("rocm-smi", ["rocm-smi", "--showid"]),
            ("rocminfo", ["rocminfo"]),
            ("hipinfo", ["hipinfo"]),
            ("vulkaninfo", ["vulkaninfo", "--summary"])):
        out = _run(argv)
        tools[tool] = {"status": out["status"],
                       "reason": out.get("reason"),
                       "head": (out.get("stdout", "")[:512]
                                if out["status"] == "SAMPLED" else None)}
    return tools


def main() -> int:
    receipt = {"schema": "amd_probe/1.0",
               "sampled_at_utc": datetime.now(timezone.utc).isoformat()}
    if os.name == "nt":
        pnp = _pnp_amd_devices()
    else:
        out = _run(["lspci", "-nn"])
        devices = []
        if out["status"] == "SAMPLED":
            for line in out["stdout"].splitlines():
                if "1002:" in line:
                    devices.append({"source": "lspci", "raw": line.strip(),
                                    "endpoint_class": "NEEDS_CLASSIFICATION"})
        pnp = {"probe": out["status"], "amd_devices": devices}
    receipt["display_devices"] = pnp
    receipt["tooling"] = _tooling()
    discrete = [d for d in pnp["amd_devices"]
                if d.get("endpoint_class") == "DISCRETE_CANDIDATE"]
    if discrete:
        receipt["verdict"] = "AMD_DISCRETE_PRESENT"
        receipt["evidence"] = NOT_CHECKED
        receipt["note"] = ("discrete AMD GPU enumerated; peer matrix not "
                           "yet executed -- run amd_future_matrix.py")
    else:
        receipt["verdict"] = NO_AMD
        receipt["evidence"] = PROVEN
        receipt["note"] = ("no discrete AMD GPU: only shared-memory iGPU "
                           "or nothing; zero AMD peer pairs constructible")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
