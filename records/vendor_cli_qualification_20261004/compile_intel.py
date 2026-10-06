import hashlib
import json
import os
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parent
sdk = Path(r'E:\the_harness\records\toolchains\intel_sycl\nightly_20261004')
env = dict(os.environ)
env['PATH'] = str(sdk / 'bin') + os.pathsep + env['PATH']
env['LIB'] = str(sdk / 'lib') + os.pathsep + env.get('LIB', '')
command = [str(sdk / 'bin/clang++.exe'), '-fsycl', '-O2', str(root / 'intel_vector.cpp'), '-o', str(root / 'intel_vector.exe')]
p = subprocess.Popen(command, env=env, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
(root / 'intel_compile.stdout.log').write_bytes(out)
(root / 'intel_compile.stderr.log').write_bytes(err)
result = {'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'source_sha256': hashlib.sha256((root / 'intel_vector.cpp').read_bytes()).hexdigest(), 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
(root / 'intel_compile.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
if p.returncode == 0:
    run = subprocess.Popen([str(root / 'intel_vector.exe')], env=env, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        out, err = run.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        run.kill()
        out, err = run.communicate(timeout=10)
    result = {'command': [str(root / 'intel_vector.exe')], 'pid': run.pid, 'exit_code': run.returncode, 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
    (root / 'intel_native_run.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
