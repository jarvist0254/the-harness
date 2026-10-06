import hashlib
import json
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parent
compiler = r'E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core\bin\hipcc.exe'
command = [compiler, '--offload-arch=gfx1036', '-O2', str(root / 'hip_vector.cpp'), '-o', str(root / 'hip_vector.exe')]
p = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
(root / 'compile.stdout.log').write_bytes(out)
(root / 'compile.stderr.log').write_bytes(err)
receipt = {'command': command, 'pid': p.pid, 'exit_code': p.returncode,
           'source_sha256': hashlib.sha256((root / 'hip_vector.cpp').read_bytes()).hexdigest(),
           'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
(root / 'compile.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(p.returncode)
