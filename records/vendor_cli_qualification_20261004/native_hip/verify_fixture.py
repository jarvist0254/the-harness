import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
binary = root / 'hip_vector.exe'
assert binary.exists(), 'Native HIP fixture executable is not implemented yet'
sdk = Path(r'E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core')
env = dict(os.environ)
env['PATH'] = str(sdk / 'bin') + os.pathsep + env['PATH']
results = []
for name, args, expected_exit in [('default', [], 0), ('corruption', ['--inject-corruption'], 1)]:
    command = [str(binary)] + args
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         cwd=root, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        out, err = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate(timeout=10)
        raise AssertionError('HIP execution exceeded 60 seconds')
    (root / (name + '.stdout.log')).write_bytes(out)
    (root / (name + '.stderr.log')).write_bytes(err)
    result = {'command': command, 'pid': p.pid, 'exit_code': p.returncode,
              'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
    results.append(result)
    (root / 'runs.json').write_text(json.dumps(results, indent=2) + '\n')
    assert p.returncode == expected_exit, result
    receipt = json.loads(out)
    assert receipt['arch'] == 'gfx1036', receipt
    assert receipt['kernel_completed'] is True, receipt
    assert receipt['buffer_bytes'] <= 1024 * 1024, receipt
    assert (receipt['mismatch_count'] == 0) == (expected_exit == 0), receipt
print('PASS: native HIP kernel parity and real-output corruption discrimination')
