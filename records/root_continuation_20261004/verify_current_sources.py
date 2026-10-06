"""Capture current pure-suite evidence without native GPU or CAD execution."""
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    out = Path(__file__).parent / ('pure_verification_' + now.strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(exist_ok=False)
    sources = [
        'j_link/device_inventory.py', 'j_link/opencl_executor.py',
        'j_link/tests/test_device_inventory.py', 'cad/integrated_core.py',
        'cad/tests/test_integrated_layout.py', 'cad/tests/test_gap_posts.py',
    ]
    before = {p: sha(ROOT / p) for p in sources}
    runs = []
    for suite in ('j_link', 'cad'):
        command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', suite + '/tests', '-v']
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        (out / (suite + '.stdout.log')).write_bytes(result.stdout)
        (out / (suite + '.stderr.log')).write_bytes(result.stderr)
        match = re.search(rb'Ran (\d+) tests?', result.stderr)
        runs.append({
            'suite': suite, 'command': command, 'exit': result.returncode,
            'seconds': time.monotonic() - started,
            'test_methods': int(match.group(1)) if match else None,
            'reported_ok': result.stderr.rstrip().endswith(b'OK'),
        })
    after = {p: sha(ROOT / p) for p in sources}
    passed = before == after and all(r['exit'] == 0 and r['reported_ok'] for r in runs)
    receipt = {
        'utc': now.isoformat(), 'scope': 'Pure/mocked regression suites; not native hardware, capacity, physical fit or full-goal qualification',
        'source_hashes_before': before, 'source_hashes_after': after,
        'runs': runs, 'verdict': 'PASS_CURRENT_PURE_SUITES' if passed else 'FAIL',
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'receipt': str(out / 'receipt.json'), 'runs': runs, 'verdict': receipt['verdict']}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
