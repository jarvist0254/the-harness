import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parent
executable = Path('E:/tooling/FreeCAD/app/FreeCAD_1.1.4-Windows-x86_64-py311/bin/freecadcmd.exe')
script = root / 'export_preview_geometry.py'
environment = os.environ.copy()
environment['QT_QPA_PLATFORM'] = 'offscreen'
started = time.monotonic()
with (root / 'preview_export.stdout.log').open('wb') as out, (root / 'preview_export.stderr.log').open('wb') as err:
    process = subprocess.Popen([str(executable), str(script)], env=environment,
                               stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
    timed_out = False
    try:
        code = process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        code = process.wait(timeout=10)
target = root / 'preview_geometry.json'
receipt = {'command': [str(executable), str(script)], 'pid': process.pid,
           'process_exit_code': code, 'timed_out': timed_out,
           'seconds': time.monotonic()-started,
           'geometry_present': target.is_file(),
           'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest()}
(root / 'preview_export_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
if timed_out or code or not target.is_file():
    raise SystemExit(1)
geometry = json.loads(target.read_text())
if set(geometry) != {'compact', 'universal'} or any(not v['shapes'] for v in geometry.values()):
    raise SystemExit(1)
