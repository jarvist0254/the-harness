import json
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parent
command = r'cmd.exe /d /s /c ""C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul && cl /nologo /EHsc /O2 /D__HIP_PLATFORM_AMD__ /I"E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core\include" hip_module_host.cpp /Fe:hip_vector.exe /link /LIBPATH:"E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core\lib" amdhip64.lib"'
p = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
result = {'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
(root / 'host_compile_revision2.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
