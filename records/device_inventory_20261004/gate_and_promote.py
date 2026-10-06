import hashlib
import json
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parent
workspace = root.parents[1]
candidate = root / 'device_inventory.py'
tests = root / 'test_device_inventory.py'
original = candidate.read_bytes()
def check(phase):
    command = [sys.executable, '-B', '-m', 'unittest', '-v', 'test_device_inventory', 'test_real_headers']
    p = subprocess.run(command, cwd=root, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    (root / (phase + '.stdout.log')).write_bytes(p.stdout)
    (root / (phase + '.stderr.log')).write_bytes(p.stderr)
    return {'command': command, 'exit_code': p.returncode}
red = check('red')
assert red['exit_code'] == 1
source = original.decode()
old = "    header = [h.strip().lower() for h in rows_in[0]]"
new = """    # Only these exact known NVIDIA MiB header fields carry convertible units.
    known_headers = {
        'memory.total [mib]': 'memory.total',
        'memory.free [mib]': 'memory.free',
        'memory.used [mib]': 'memory.used',
    }
    header = [known_headers.get(h.strip().lower(), h.strip().lower())
              for h in rows_in[0]]
    if len(header) != len(set(header)):
        return []"""
assert source.count(old) == 1
source = source.replace(old, new)
source = source.replace('"""Pure stdlib GPU inventory adapter. No native execution, no subprocess at import."""', '"""Pure captured-output adapter; no GPU imports or subprocess at import.\n\nNVIDIA MiB CSV headers are live-qualified on this host. AMD/Intel named JSON\nschemas are synthetic fixture contracts, not verified native CLI schemas; their\nfree capacity remains unknown and cannot enter dedicated-memory admission.\n"""')
candidate.write_text(source)
test_source = tests.read_text()
old = "        self.assertIsNone(inv['devices'][0]['advertised_total_bytes'])\n        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)\n        self.assertEqual(snap['refused'][0]['reason'], 'unknown_free')"
new = old.replace("'unknown_free'", "'invalid_total'")
assert test_source.count(old) == 1
tests.write_text(test_source.replace(old, new))
green = check('green')
assert green['exit_code'] == 0, (root / 'green.stderr.log').read_text()
target = workspace / 'j_link/device_inventory.py'
target_tests = workspace / 'j_link/tests/test_device_inventory.py'
assert not target.exists() and not target_tests.exists()
target.write_bytes(candidate.read_bytes())
main_tests = tests.read_text().replace('import device_inventory', 'from j_link import device_inventory').replace('from device_inventory import (', 'from j_link.device_inventory import (')
extra = (root / 'test_real_headers.py').read_text().replace('from device_inventory import ', 'from j_link.device_inventory import ').replace('ROOT = Path(__file__).resolve().parent', "ROOT = Path(__file__).resolve().parents[2] / 'records/device_inventory_20261004'")
main_tests = main_tests[:main_tests.rfind("if __name__ == '__main__':")]
target_tests.write_text(main_tests + '\n' + extra)
receipt = {'immutable_source_sha256': hashlib.sha256(original).hexdigest(), 'accepted_source_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'red': red, 'green': green,
           'amendments': ['Whitelist three exact memory.* [MiB] headers only', 'Reject duplicate canonical CSV fields rather than silently overwrite', 'Clarify synthetic AMD/Intel schema limitations', 'Correct fractional-total refusal expectation: invalid_total precedes unknown_free'],
           'public_api': ['normalize_inventory(samples, *, now_utc, max_age_seconds=5)', 'get_admission_snapshot(inventory_result, *, now_utc, max_age_seconds=5)']}
(root / 'promotion.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
