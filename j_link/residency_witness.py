#!/usr/bin/env python3
"""Host-activity witness R+2 (three-vendor arm, 2026-10-05).

Watches host memory while a transfer command runs: if a "direct" claim is
on the table but host committed bytes grow with the payload, that is
hidden staging -- demote to PIPE/HST. Corroborates, never proves.

Usage:
    python -B j_link/residency_witness.py -- <transfer command...>

Output: JSON receipt {host_before, host_after, delta, verdict, cmd_exit}.
Verdict is WITNESSED (no anomaly) or HOST_GROWTH_OBSERVED (investigate);
it never claims residency proven -- that needs control R on both GPUs.
Windows uses GlobalMemoryStatusEx via ctypes; Linux reads /proc/meminfo.
Stdlib only. Exit code mirrors the wrapped command (0/1), or 2 if the
witness itself failed.
"""
from __future__ import annotations

import json
import subprocess
import sys


def _host_committed_bytes() -> int | None:
    try:
        if sys.platform == "win32":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            status = Status()
            status.dwLength = ctypes.sizeof(Status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
                    ctypes.byref(status)):
                return None
            return int(status.ullTotalPhys - status.ullAvailPhys)
        with open("/proc/meminfo", encoding="utf-8") as handle:
            total = avail = None
            for line in handle:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    avail = int(line.split()[1]) * 1024
            if total is None or avail is None:
                return None
            return total - avail
    except (OSError, ValueError):
        return None


def main(argv: list) -> int:
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        print(json.dumps({"status": "REFUSED",
                          "reason": "usage: residency_witness.py -- <cmd>"}))
        return 2
    cmd = argv[argv.index("--") + 1:]
    before = _host_committed_bytes()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=900)
        cmd_exit = proc.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "REFUSED",
                          "reason": "command failed to launch: %s"
                          % type(exc).__name__}))
        return 2
    after = _host_committed_bytes()
    receipt = {"schema": "residency_witness_R2/1.0",
               "cmd": cmd, "cmd_exit": cmd_exit,
               "host_committed_before": before,
               "host_committed_after": after}
    if before is None or after is None:
        receipt["verdict"] = "UNMEASURABLE_ON_THIS_PLATFORM"
    else:
        receipt["host_delta_bytes"] = after - before
        receipt["verdict"] = ("HOST_GROWTH_OBSERVED_INVESTIGATE"
                              if after - before > 64 << 20
                              else "WITNESSED_NO_ANOMALY")
        receipt["note"] = ("growth alone is not proof of staging; "
                           "payload-sized growth under a direct claim "
                           "demotes the claim to PIPE/HST pending control R")
    print(json.dumps(receipt, indent=2))
    return 0 if cmd_exit == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
