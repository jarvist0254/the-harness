import subprocess,json,time,os
from pathlib import Path
out=Path(r'E:\the_harness\records\rpc_four_worker_20261004')
vc=r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
ninja=r'C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
configure='cmake -S repos/llama.cpp -B records/build_cpu_rpc -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="'+ninja+'" -DGGML_RPC=ON -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DCMAKE_SUPPRESS_REGENERATION=ON'
cmd='cmd.exe /d /s /c ""'+vc+'" >nul && '+configure+' && cmake --build records/build_cpu_rpc --target ggml-rpc-server --parallel 4"'
with open(out/'build_retry_stdout.log','w') as stdout,open(out/'build_retry_stderr.log','w') as stderr:
 p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
 (out/'build_retry_process.json').write_text(json.dumps({'supervisor_pid':os.getpid(),'build_pid':p.pid,'timeout_seconds':600,'max_jobs':4,'command':cmd},indent=2))
 try: code=p.wait(timeout=600)
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); code=124
 (out/'build_retry_exit.json').write_text(json.dumps({'exit_code':code}))
 raise SystemExit(code)
