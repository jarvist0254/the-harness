#!/usr/bin/env python3
"""Freeze a checkpoint manifest: SHA256 of every file in the listed roots.

Usage:
    python -B scripts/freeze_checkpoint.py <label> <path...>

Writes records/CHECKPOINT_<label>_<UTC>.json = {file: sha256}. Earlier
manifests stay immutable; verification is byte comparison, never trust.
Stdlib only. Exit 0 wrote manifest, 1 nothing matched, 2 write failed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "target"}


def iter_files(roots: list) -> list:
    out = []
    for root in roots:
        base = Path(root)
        if base.is_file():
            out.append(base)
            continue
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not any(
                    part in SKIP_DIRS for part in path.parts):
                out.append(path)
    return out


def main(argv: list) -> int:
    if len(argv) < 3:
        print("usage: freeze_checkpoint.py <LABEL> <path...>")
        return 2
    label = argv[1]
    files = iter_files(argv[2:])
    if not files:
        print("no files matched")
        return 1
    manifest = {}
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest[str(path).replace("\\", "/")] = digest
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    records = Path("records")
    records.mkdir(exist_ok=True)
    dest = records / ("CHECKPOINT_%s_%s.json" % (label, stamp))
    dest.write_text(json.dumps({"label": label, "utc": stamp,
                                "file_count": len(manifest),
                                "files": manifest}, indent=2),
                    encoding="utf-8")
    print("wrote %s (%d files)" % (dest, len(manifest)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
