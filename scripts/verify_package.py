#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'records/PACKAGE_SHA256.json').read_text())
failures = []
for item in manifest['files']:
    path = root / item['path']
    if not path.is_file():
        failures.append(f"missing: {item['path']}")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item['sha256']:
        failures.append(f"changed: {item['path']}")
print(json.dumps({'checked': len(manifest['files']), 'failures': failures}, indent=2))
raise SystemExit(1 if failures else 0)
