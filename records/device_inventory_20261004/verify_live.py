import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone
root = Path(__file__).resolve().parent
workspace = root.parents[1]
sys.path.insert(0, str(workspace))
from j_link.device_inventory import normalize_inventory, get_admission_snapshot

command = [r'C:\Windows\System32\nvidia-smi.exe', '--query-gpu=pci.bus_id,name,memory.total,memory.free,memory.used,uuid', '--format=csv,nounits']
start = datetime.now(timezone.utc)
p = subprocess.run(command, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
now = datetime.now(timezone.utc)
sample = {'tool': 'nvidia-smi', 'format': 'csv', 'exit_code': p.returncode,
          'stdout': p.stdout.decode(), 'sampled_at_utc': start.isoformat(),
          'memory_kind': 'DEDICATED'}
inventory = normalize_inventory([sample], now_utc=now)
fresh = get_admission_snapshot(inventory, now_utc=now)
stale = get_admission_snapshot(inventory, now_utc=start + timedelta(seconds=6))
shared = normalize_inventory([dict(sample, memory_kind='SHARED_HOST')], now_utc=now)
shared_snapshot = get_admission_snapshot(shared, now_utc=now)
assert p.returncode == 0
assert len(fresh['eligible']) == 1
assert fresh['eligible'][0]['physical_id'] == '0000:01:00.0'
assert fresh['eligible'][0]['advertised_total_bytes'] == 16303 * 1048576
assert 0 < fresh['eligible'][0]['observed_free_bytes'] <= fresh['eligible'][0]['advertised_total_bytes']
assert stale['eligible'] == [] and stale['refused'][0]['reason'] == 'stale'
assert shared_snapshot['eligible'] == [] and shared_snapshot['refused'][0]['reason'] == 'not_dedicated'
tests_command = [sys.executable, '-B', '-m', 'unittest', '-v', 'j_link.tests.test_device_inventory']
tests = subprocess.run(tests_command, cwd=workspace, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
(root / 'accepted_tests.stdout.log').write_bytes(tests.stdout)
(root / 'accepted_tests.stderr.log').write_bytes(tests.stderr)
assert tests.returncode == 0
original = workspace / 'records/factory_runs/20261004/full_fabric_continuation_20261004T113400Z/grok_inventory_edit/reconstructed/device_inventory.py'
receipt = {'command': command, 'exit_code': p.returncode, 'stdout': p.stdout.decode(), 'stderr': p.stderr.decode(), 'sample_start_utc': start.isoformat(), 'checked_at_utc': now.isoformat(), 'sample_age_seconds': (now-start).total_seconds(), 'max_age_seconds': 5, 'inventory': inventory, 'fresh_admission': fresh, 'synthetic_age_6s_admission': stale, 'same_capture_marked_shared_admission': shared_snapshot, 'source_sha256': hashlib.sha256((workspace / 'j_link/device_inventory.py').read_bytes()).hexdigest(), 'immutable_provider_sha256': hashlib.sha256(original.read_bytes()).hexdigest(), 'tests_command': tests_command, 'tests_exit': tests.returncode, 'classification_basis': 'Actual RTX5070Ti discrete SKU independently identified by Windows PNP/OpenCL inventory; parser requires caller classification', 'limitations': ['Read-only instantaneous NVIDIA sample, not an allocation guarantee/reservation', 'AMD/Intel schema selectors are synthetic contracts; live native CLI formats NOT_CHECKED; their free remains None', 'Integrated/shared memory is refused for dedicated budgets', 'Physical identity is reported PCI BDF, not certified serial/UUID-to-slot lifecycle mapping', 'No GPUs allocated, kernels run or models loaded by inventory capture', 'Admission API accepts trusted normalized dictionaries, not a security/authentication boundary']}
(root / 'live_acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
