import json
import os
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parent
sdk = Path(r'E:\the_harness\records\toolchains\intel_sycl\nightly_20261004')
env = dict(os.environ)
env['PATH'] = str(sdk / 'bin') + os.pathsep + env['PATH']
overrides = {'ONEAPI_DEVICE_SELECTOR': 'opencl:gpu',
             'UR_ADAPTERS_SEARCH_PATH': str(sdk / 'bin'),
             'UR_LOG_LOADER': 'level:debug;output:stderr',
             'UR_LOG_OPENCL': 'level:debug;output:stderr'}
env.update(overrides)
revision2 = '--quoted-path' in sys.argv
if revision2:
    overrides['UR_ADAPTERS_SEARCH_PATH'] = '"' + str(sdk / 'bin') + '"'
    env.update(overrides)
command = [str(sdk / 'bin/sycl-ls.exe'), '--verbose']
p = subprocess.Popen(command, env=env, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
result = {'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'child_local_overrides': overrides,
          'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace'),
          'opencl_dll_exists': Path(r'C:\Windows\System32\OpenCL.dll').exists(),
          'archive_opencl_adapter_files': [str(path) for path in sdk.rglob('*opencl*') if path.is_file() and path.suffix.lower() in ('.dll', '.lib')],
          'force_load_not_attempted': 'No actual UR OpenCL adapter DLL found; forcing the OpenCL ICD DLL as a UR adapter would use the wrong ABI'}
(root / ('intel_opencl_probe_revision2.json' if revision2 else 'intel_opencl_probe.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
