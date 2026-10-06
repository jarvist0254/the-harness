import hashlib, json, os, pathlib, subprocess, sys, time
from datetime import datetime, timezone

ROOT = pathlib.Path(r'E:\the_harness')
OUT = ROOT / r'records\root_continuation_20261004\cuda_l0_source_compile_20261004T202000Z'
SOURCE = ROOT / r'records\factory_runs\20261004\cuda_l0_device_dmabuf_prep_20261004T195400Z\qwen_cuda_l0_device_dmabuf_v3\source.qwen_untrusted.cpp'
PINS = {
    'source.qwen_untrusted.cpp': ('source', 'e8916bc07ee2a058f5af9371b073b2f47810071c6949480fe0c0a4b2d3064411'),
    r'toolchains\cuda_driver_headers_20261004\include\cuda.h': ('cuda.h', '7a79d67ca888061b1dfbe4739b51ad64f85a2f3ad874947ce09b2c635b4c7072'),
    r'toolchains\cuda_driver_headers_20261004\include\cudaTypedefs.h': ('cudaTypedefs.h', '77eb4072ae5da75bec31c4cf6291967e8ecbd6981ece0d47b07dbbabf781782c'),
    r'toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h': ('ze_api.h', 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'),
}
SUPERVISOR = ROOT / r'records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py'
SUPERVISOR_SHA = '3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c'
WSL = pathlib.Path(r'C:\Windows\System32\wsl.exe')
WSL_SHA = '7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757'
CONTROLLER = pathlib.Path(__file__).resolve()
COMPILER_SHA = '1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769'
MAX_STREAM = 1_048_576

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def verify_pins():
    rows=[]
    for rel,(name,want) in PINS.items():
        p = SOURCE if name=='source' else ROOT / rel
        got=sha(p)
        rows.append({'name':name,'path':str(p),'sha256':got,'expected_sha256':want,'match':got==want})
    for name,p,want in [('supervisor',SUPERVISOR,SUPERVISOR_SHA),('wsl.exe',WSL,WSL_SHA)]:
        got=sha(p)
        rows.append({'name':name,'path':str(p),'sha256':got,'expected_sha256':want,'match':got==want})
    if not all(x['match'] for x in rows):
        raise RuntimeError('pin_mismatch')
    return rows

def run(label, argv, deadline, outpath, errpath):
    start=time.monotonic()
    timed_out=False
    overflow=False
    with open(outpath,'wb') as stdout_file, open(errpath,'wb') as stderr_file:
        proc=subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout_file, stderr=stderr_file,
                              cwd=str(OUT), shell=False, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        pid=proc.pid
        try:
            while proc.poll() is None:
                if time.monotonic()-start >= deadline:
                    timed_out=True
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait(timeout=5)
                    break
                if pathlib.Path(outpath).stat().st_size>MAX_STREAM or pathlib.Path(errpath).stat().st_size>MAX_STREAM:
                    overflow=True
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait(timeout=5)
                    break
                time.sleep(.05)
            code=proc.wait(timeout=1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=5)
    if overflow or any(os.path.getsize(f)>MAX_STREAM for f in (outpath,errpath)):
        raise RuntimeError(label+'_stream_overflow')
    return {'label':label,'argv':argv,'pid':pid,'exit_code':code,'timed_out':timed_out,'elapsed_seconds':round(time.monotonic()-start,3),
            'stdout_path':str(outpath),'stdout_bytes':os.path.getsize(outpath),'stderr_path':str(errpath),'stderr_bytes':os.path.getsize(errpath),
            'pid_absent_after_wait': subprocess.Popen(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).communicate(timeout=5)[0].decode(errors='replace').find(str(pid))<0}

OUT.mkdir(parents=True, exist_ok=True)
if any(p.name != 'compile_controller.py' for p in OUT.iterdir()): raise SystemExit('refuse_nonfresh_output')
receipt={'phase':'compile_only','candidate_execution':'NOT_RUN','linking':'NOT_RUN','gpu_api_calls':'NOT_RUN','started_utc':datetime.now(timezone.utc).isoformat(), 'controller_sha256_before':sha(CONTROLLER), 'pins_before':verify_pins(), 'runs':[]}
source_mount='/mnt/e/the_harness/records/factory_runs/20261004/cuda_l0_device_dmabuf_prep_20261004T195400Z/qwen_cuda_l0_device_dmabuf_v3/source.qwen_untrusted.cpp'
inc_cuda='/mnt/e/the_harness/records/toolchains/cuda_driver_headers_20261004/include'
inc_l0='/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include'
out_mount='/mnt/e/the_harness/records/root_continuation_20261004/cuda_l0_source_compile_20261004T202000Z/candidate.o'
preflight=[
 ('compiler_version',[str(WSL),'-d','Ubuntu-24.04','--exec','/usr/bin/c++','--version'],15),
 ('compiler_path_hash',[str(WSL),'-d','Ubuntu-24.04','--exec','/usr/bin/sha256sum','/usr/bin/c++'],15),
]
for label,argv,lim in preflight:
    receipt['runs'].append(run(label,argv,lim,OUT/f'{label}.stdout.txt',OUT/f'{label}.stderr.txt'))
if any(x['exit_code']!=0 or x['timed_out'] for x in receipt['runs']):
    raise SystemExit('compiler_preflight_failed')
version_text=(OUT/'compiler_version.stdout.txt').read_text(encoding='utf-8',errors='replace')
hash_text=(OUT/'compiler_path_hash.stdout.txt').read_text(encoding='utf-8',errors='replace').strip().split()
if '13.3.0-6ubuntu2~24.04.1' not in version_text or len(hash_text)<1 or hash_text[0].lower()!=COMPILER_SHA:
    raise SystemExit('compiler_identity_mismatch')
receipt['compiler_sha256_expected']=COMPILER_SHA
receipt['compiler_version_observed']=version_text.strip()
receipt['compiler_sha256_observed']=hash_text[0].lower()
compile_argv=[str(WSL),'-d','Ubuntu-24.04','--exec','/usr/bin/timeout','--signal=TERM','--kill-after=5s','85s','/usr/bin/c++','-std=c++17','-c','-I'+inc_cuda,'-I'+inc_l0,source_mount,'-o',out_mount]
receipt['compile_argv']=compile_argv
compile_result=run('compile_only',compile_argv,100,OUT/'compile.stdout.txt',OUT/'compile.stderr.txt')
receipt['runs'].append(compile_result)
post_hash_argv=[str(WSL),'-d','Ubuntu-24.04','--exec','/usr/bin/sha256sum','/usr/bin/c++']
receipt['runs'].append(run('compiler_path_hash_after',post_hash_argv,15,OUT/'compiler_path_hash_after.stdout.txt',OUT/'compiler_path_hash_after.stderr.txt'))
post_hash_text=(OUT/'compiler_path_hash_after.stdout.txt').read_text(encoding='utf-8',errors='replace').strip().split()
if receipt['runs'][-1]['exit_code']!=0 or receipt['runs'][-1]['timed_out'] or not post_hash_text or post_hash_text[0].lower()!=COMPILER_SHA:
    raise SystemExit('compiler_identity_changed')
receipt['compiler_sha256_after']=post_hash_text[0].lower()
receipt['pins_after']=verify_pins()
receipt['controller_sha256_after']=sha(CONTROLLER)
if receipt['controller_sha256_before']!=receipt['controller_sha256_after']:
    raise RuntimeError('controller_changed_during_run')
receipt['finished_utc']=datetime.now(timezone.utc).isoformat()
obj=OUT/'candidate.o'
receipt['object_exists']=obj.exists()
receipt['object_sha256']=sha(obj) if obj.exists() else None
receipt['verdict']='COMPILE_EXIT_ZERO' if compile_result['exit_code']==0 and compile_result['timed_out'] is False else 'COMPILE_FAILED'
with open(OUT/'compile_receipt.json','w',encoding='utf-8',newline='\n') as f: json.dump(receipt,f,indent=2); f.write('\n')
print(json.dumps(receipt,indent=2))
