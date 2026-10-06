import json
import os
from pathlib import Path
import subprocess

outdir = Path(__file__).resolve().parent
hip = outdir / 'native_hip'
intel = Path(r'E:\the_harness\records\toolchains\intel_sycl\nightly_20261004')
core = r'E:\tmp\PyReExperimental\rocm\Lib\site-packages\_rocm_sdk_core'
vcvars = r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
commands = [
 ('hip_host_vs', hip, f'cmd.exe /d /s /c ""{vcvars}" >nul && cl /nologo /EHsc /O2 /I"{core}\\include" hip_module_host.cpp /Fe:hip_vector.exe /link /LIBPATH:"{core}\\lib" amdhip64.lib"'),
 ('intel_compile_vs', outdir, f'cmd.exe /d /s /c ""{vcvars}" >nul && "{intel}\\bin\\clang++.exe" -fsycl -O2 intel_vector.cpp -o intel_vector.exe -L"{intel}\\lib""'),
]
results = []
for name, cwd, command in commands:
    env = dict(os.environ)
    env['PATH'] = str(intel / 'bin') + os.pathsep + env['PATH']
    p = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        out, err = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate(timeout=10)
    (outdir / (name + '.stdout.log')).write_bytes(out)
    (outdir / (name + '.stderr.log')).write_bytes(err)
    result = {'name': name, 'command': command, 'pid': p.pid, 'exit_code': p.returncode, 'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace')}
    results.append(result)
    print(json.dumps(result), flush=True)
(outdir / 'compile_vs_results.json').write_text(json.dumps(results, indent=2) + '\n')
