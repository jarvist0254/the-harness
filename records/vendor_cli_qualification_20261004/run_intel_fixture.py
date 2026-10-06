import json
import os
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parent
sdk = Path(r'E:\the_harness\records\toolchains\intel_sycl\nightly_20261004')
env = dict(os.environ)
env['PATH'] = str(sdk / 'bin') + os.pathsep + env['PATH']
results = []
for name, args in [('default', []), ('corruption', ['--inject-corruption'])]:
    command = [str(root / 'intel_vector.exe')] + args
    p = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        out, err = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate(timeout=10)
    result = {'name': name, 'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
    results.append(result)
    print(json.dumps(result), flush=True)
(root / 'intel_native_runs.json').write_text(json.dumps(results, indent=2) + '\n')
