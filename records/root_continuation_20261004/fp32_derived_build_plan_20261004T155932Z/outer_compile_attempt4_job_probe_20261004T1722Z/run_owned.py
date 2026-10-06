import pathlib,subprocess,threading,time,hashlib,json,os,sys,shutil
P=pathlib.Path(__file__).resolve().parent.parent
OUT=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(r'E:\the_harness\records\build_vulkan_fp32_staging_20261004T155932Z')
PY=pathlib.Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')
TRACE=ROOT/'evidence/attempt4_job_probe/job_members.jsonl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):
 f=OUT/name;t=f.with_suffix('.part');t.write_text(json.dumps(obj,indent=2));os.replace(t,f)
A=P/'ROOT_BUILD_ATTEMPT4_ADMISSION.json';C=P/'controller_attempt4_job_probe.py';H=P/'job_member_trace.py';a=json.loads(A.read_text())
files=[PY,C,H,A,P/'CONTRACT.json',pathlib.Path(a['variant_path']),ROOT/'source/ggml/src/ggml-vulkan/ggml-vulkan.cpp',ROOT/'build_owned_configure_attempt4.cmd',ROOT/'build_owned_build_attempt4.cmd']
before={str(f):sha(f) for f in files};assert before[str(PY)]=='3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260';assert before[str(C)]==a['controller_sha256'];assert before[str(H)]=='8127c5263bb2526c4205b4ecc5aa3f2094ac7e134c0b910b8a6ea0f18ef793dd';assert before[str(A)]=='ee0da539c2ab1bd5cad23adb68f59acf92dc26b673192349730afe2b7fc144fa'
cmd=[str(PY),'-B',str(C),'--runtime-admission',str(A),'--runtime-admission-sha256',before[str(A)]]
proc=subprocess.Popen(cmd,cwd=P,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
start=time.monotonic();lock=threading.Lock();capture={'bytes':0,'overflow':False,'reader_errors':[]};handles=[]
def reader(pipe,name):
 try:
  with (OUT/name).open('wb') as f:
   while True:
    b=pipe.read(4096)
    if not b:break
    with lock:
     keep=max(0,min(len(b),2097152-capture['bytes']));capture['bytes']+=keep
     if keep<len(b):capture['overflow']=True
    f.write(b[:keep]);f.flush()
 except Exception as e:capture['reader_errors'].append(type(e).__name__+':'+str(e))
 finally:pipe.close()
for pipe,name in ((proc.stdout,'controller.stdout.raw.log'),(proc.stderr,'controller.stderr.raw.log')):
 t=threading.Thread(target=reader,args=(pipe,name),daemon=True);t.start();handles.append(t)
write('launch_receipt.json',{'pid':proc.pid,'command':cmd,'source_pins_before':before,'outer_deadline_seconds':330,'aggregate_log_cap':2097152,'scope':'Single ROOT admitted CPU build diagnostic, no GPU'})
last=-15;trace_seen=0;timeout=False
while proc.poll() is None:
 elapsed=time.monotonic()-start
 if elapsed>=330 or capture['overflow']:
  timeout=elapsed>=330;proc.kill();break
 if elapsed-last>=15:
  last=elapsed;obs=[]
  if TRACE.exists():
   raw=TRACE.read_bytes()
   assert len(raw)<=131072
   for line in raw.splitlines()[trace_seen:]:
    try:row=json.loads(line);obs.append(row)
    except Exception:obs.append({'status':'PARTIAL_JSON_UNKNOWN'})
   trace_seen=len(raw.splitlines())
  write('outer_progress.json',{'pid':proc.pid,'elapsed_seconds':elapsed,'status':'RUNNING','new_job_member_observations':obs,'capture':capture})
  print(json.dumps({'elapsed_seconds':round(elapsed,1),'pid':proc.pid,'new_observations':obs}),flush=True)
 time.sleep(.5)
proc.wait(timeout=15)
for t in handles:t.join(timeout=5)
assert not any(t.is_alive() for t in handles)
after={str(f):sha(f) for f in files};check=subprocess.run([r'C:\Windows\System32\tasklist.exe','/FI','PID eq '+str(proc.pid)],capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
presence=check.stdout.decode(errors='replace');absent=check.returncode==0 and 'No tasks are running' in presence
source=ROOT/'evidence/attempt4_job_probe';copies=[]
if source.exists():
 for path in source.rglob('*'):
  if path.is_file():
   rel=path.relative_to(source);dest=OUT/'actual_runtime_evidence'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);assert sha(path)==sha(dest);copies.append({'source':str(path),'copy':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
r={'pid':proc.pid,'exit_code':proc.returncode,'seconds':time.monotonic()-start,'outer_timeout':timeout,'reaped':proc.poll() is not None,'pid_absent_after_wait':absent,'pid_absence_stdout':presence,'pid_absence_stderr':check.stderr.decode(errors='replace'),'capture':capture,'source_pins_before':before,'source_pins_after':after,'source_pins_unchanged':before==after,'copied_runtime_evidence':copies,'scope':'Bounded owned CPU compile diagnostic; no GPU, no whole-tree certificate'};write('outer_run_receipt.json',r);print(json.dumps({k:r[k] for k in ('pid','exit_code','seconds','outer_timeout','pid_absent_after_wait','source_pins_unchanged')}),flush=True)
