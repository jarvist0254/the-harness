import json
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parent
command = [r'E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core\bin\hipcc.exe', '--genco', '--offload-arch=gfx1036', '-D__HIPCC_RTC__', '-O2', str(root / 'affine_device.cpp'), '-o', str(root / 'affine_gfx1036.hsaco')]
p = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
(root / 'device_only_compile.stdout.log').write_bytes(out)
(root / 'device_only_compile.stderr.log').write_bytes(err)
result = {'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'mode': 'EXPERIMENTAL_DEVICE_ONLY_RTC_HEADER_CONFIGURATION', 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
(root / 'device_only_compile.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
