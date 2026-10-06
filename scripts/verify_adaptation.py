#!/usr/bin/env python3
"""Verify the current curated adaptation receipt without rewriting the import baseline."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    manifest_path = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else
                     root / 'records' / 'ADAPTATION_SHA256_20261004.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    failures = []
    entries = manifest['files']
    seen = set()
    for entry in entries:
        relative = entry['path']
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            failures.append(f'outside workspace: {relative}')
            continue
        if relative in seen:
            failures.append(f'duplicate manifest entry: {relative}')
            continue
        seen.add(relative)
        if not candidate.is_file():
            failures.append(f'missing: {relative}')
            continue
        data = candidate.read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            failures.append(f'changed: {relative}')
    print(json.dumps({'manifest': str(manifest_path), 'checked': len(entries),
                      'failures': failures, 'scope': manifest['scope']}, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
