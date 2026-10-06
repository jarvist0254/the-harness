import hashlib
import json
from pathlib import Path
import tarfile
import time

root = Path(r'E:\the_harness\records\toolchains\intel_sycl')
archive = root / 'sycl_windows.tar.gz'
target = root / 'nightly_20261004'
if target.exists():
    raise RuntimeError('Refuse existing extraction target')
started = time.monotonic()
with tarfile.open(archive, 'r:gz') as tar:
    members = tar.getmembers()
    total = sum(m.size for m in members)
    if total > 4 * 1024**3 or len(members) > 30000:
        raise RuntimeError('Archive exceeds extraction bounds')
    for m in members:
        path = (target / m.name).resolve()
        if not path.is_relative_to(target.resolve()) or not (m.isfile() or m.isdir()):
            raise RuntimeError('Unsafe archive member: ' + m.name)
    target.mkdir()
    for m in members:
        if time.monotonic() - started > 60:
            raise TimeoutError('Extraction exceeded 60 second bound')
        tar.extract(m, target)
receipt = {'members': len(members), 'uncompressed_bytes': total,
           'seconds': time.monotonic() - started, 'target': str(target),
           'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
           'scripts_executed': False, 'path_registry_changes': False}
(root / 'extraction.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
