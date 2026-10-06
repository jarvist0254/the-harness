"""Harmless subprocess used only by the native supervisor fixture."""
import sys
import time


marker = sys.argv[1]
mode = sys.argv[2]
if mode == "natural":
    print(f"{marker}:stdout", flush=True)
    print(f"{marker}:stderr", file=sys.stderr, flush=True)
    time.sleep(0.05)
    raise SystemExit(0)
if mode == "nonzero":
    print(f"{marker}:nonzero", flush=True)
    raise SystemExit(3)
if mode in ("timeout", "cancel"):
    print(f"{marker}:sleeping", flush=True)
    time.sleep(5.0)
    raise SystemExit(0)
if mode == "overflow":
    sys.stdout.write("X" * 16384)
    sys.stdout.flush()
    raise SystemExit(0)
raise SystemExit(64)
