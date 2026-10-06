"""Bounded help/version/device inventory only; no kernels or environment installation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

OUT = Path(__file__).resolve().parent
CORE = Path(r'E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core')
commands = [
    ('hipconfig_version', [str(CORE / 'bin/hipconfig.exe'), '--version']),
    ('hipconfig_full', [str(CORE / 'bin/hipconfig.exe'), '--full']),
    ('hipcc_version', [str(CORE / 'bin/hipcc.exe'), '--version']),
    ('clang_version', [str(CORE / 'lib/llvm/bin/clang++.exe'), '--version']),
    ('hipinfo_devices', [str(CORE / 'bin/hipInfo.exe')]),
    ('clinfo_list', [str(CORE / 'bin/clinfo.exe'), '-l']),
]
results = []
for name, command in commands:
    binary = Path(command[0])
    if not binary.is_file():
        results.append({'name': name, 'command': command, 'status': 'TOOL_UNAVAILABLE'})
        continue
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=OUT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        stdout, stderr = proc.communicate(timeout=10)
    (OUT / (name + '.stdout.log')).write_bytes(stdout)
    (OUT / (name + '.stderr.log')).write_bytes(stderr)
    result = {'name': name, 'command': command, 'pid': proc.pid,
              'exit_code': proc.returncode, 'timed_out': timed_out,
              'elapsed_seconds': time.monotonic() - start,
              'binary_sha256': digest, 'binary_bytes': binary.stat().st_size,
              'environment': 'INHERITED_UNMODIFIED',
              'stdout': stdout.decode('utf-8', errors='replace'),
              'stderr': stderr.decode('utf-8', errors='replace')}
    results.append(result)
    print(json.dumps(result), flush=True)
(OUT / 'probe_results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
