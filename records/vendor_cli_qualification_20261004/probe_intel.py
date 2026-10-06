import hashlib
import json
import os
from pathlib import Path
import subprocess

root = Path(r'E:\the_harness\records\toolchains\intel_sycl\nightly_20261004')
outdir = Path(__file__).resolve().parent
results = []
for name, binary, args in [('intel_clang_version', 'clang.exe', ['--version']),
                           ('intel_sycl_devices', 'sycl-ls.exe', []),
                           ('intel_sycl_verbose', 'sycl-ls.exe', ['--verbose'])]:
    path = root / 'bin' / binary
    env = dict(os.environ)
    env['PATH'] = str(root / 'bin') + os.pathsep + env['PATH']
    command = [str(path)] + args
    proc = subprocess.Popen(command, cwd=outdir, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=10)
    (outdir / (name + '.stdout.log')).write_bytes(stdout)
    (outdir / (name + '.stderr.log')).write_bytes(stderr)
    result = {'name': name, 'command': command, 'pid': proc.pid, 'exit_code': proc.returncode,
              'binary_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'environment': 'CHILD_LOCAL_PATH_ONLY',
              'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
    results.append(result)
    print(json.dumps(result), flush=True)
(outdir / 'intel_probe_results.json').write_text(json.dumps(results, indent=2) + '\n')
