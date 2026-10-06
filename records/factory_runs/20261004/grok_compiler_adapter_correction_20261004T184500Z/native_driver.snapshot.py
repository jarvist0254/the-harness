"""Prepared native CPU driver. Execution requires separately pinned ROOT admission."""
import argparse, hashlib, importlib.util, json, os, pathlib, subprocess, sys, threading, time
HERE=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\contained_build_policy_20261004T160430Z\contained_build_supervisor.py')
BASE_SHA='fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3'
PY_SHA='3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
CUSTOM='COMPILER_ROOT_EXITED_CLEANUP_REQUIRED'
CASES=('success','resident_success','resident_failure','timeout','cancel')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def pairs(xs):
 d={}
 for k,v in xs:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
def read(p):return json.loads(pathlib.Path(p).read_text(),object_pairs_hook=pairs)
def write(p,data):
 p=pathlib.Path(p);tmp=p.with_suffix('.part')
 with tmp.open('w',encoding='utf-8') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def validate_result(case,r,restart,success_reason):
 if case not in CASES:raise ValueError('unknown fixture case')
 status=CUSTOM if case in ('success','resident_success') else {'resident_failure':'FAILED','timeout':'TIMEOUT','cancel':'CANCELLED'}[case]
 if r.get('status')!=status:raise ValueError('exact terminal status')
 if case in ('success','resident_success') and (not isinstance(success_reason,str) or not success_reason or r.get('failure_reason')!=success_reason):raise ValueError('exact compiler-root reason')
 if case in ('resident_failure','timeout','cancel') and r.get('failure_reason')!={'resident_failure':'nonzero_exit','timeout':'deadline','cancel':'cancelled'}[case]:raise ValueError('terminal reason')
 if type(r.get('job_active_count')) is not int or r['job_active_count']!=0 or r.get('drain_proof')!='CLEANUP' or r.get('whole_tree_certificate') is not False or r.get('durability')=='UNKNOWN_DURABILITY':raise ValueError('cleanup/durability refusal')
 if r.get('containment_policy')!='kill_on_close' or r.get('reattach') is not False or r.get('replay') is not False:raise ValueError('policy refusal')
 workers=r.get('workers',[])
 if len(workers)!=1:raise ValueError('one owned root required')
 w=workers[0]
 if w.get('assigned') is not True or w.get('resumed') is not True or type(w.get('pid')) is not int or w['pid']<=0 or type(w.get('exit_code')) is not int:raise ValueError('owned root state')
 if case in ('success','resident_success') and w['exit_code']!=0:raise ValueError('root zero required')
 if case=='resident_failure' and w['exit_code']!=3:raise ValueError('root3 required')
 if case in ('timeout','cancel') and w['exit_code']!=1:raise ValueError('running root termination not established')
 if any(restart.get(k)!=r.get(k) for k in ('run_id','status','failure_reason','workers','logs','job_active_count','drain_proof','containment_policy')) or restart.get('replay') is not False or restart.get('reattach') is not False or restart.get('whole_tree_certificate') is not False:raise ValueError('restart refusal')
 logs=r.get('logs',{})
 if set(logs)!={w['worker_id']}:raise ValueError('root logs')
 log=logs[w['worker_id']];markers={}
 for stream in ('stdout','stderr'):
  if log.get(stream+'_overflow') is not False or type(log.get(stream+'_bytes')) is not int or not 0<=log[stream+'_bytes']<=4096:raise ValueError('bounded stream refusal')
  if not isinstance(log.get(stream),str):raise ValueError('missing captured stream')
  rows=[json.loads(line,object_pairs_hook=pairs) for line in log[stream].splitlines()]
  expected=['child','root'] if case in ('resident_success','resident_failure') else ['root']
  if [x.get('role') for x in rows]!=expected:raise ValueError('complete marker sequence')
  for row in rows:
   if row.get('fixture')!='COMPILER_COMPLETION_CPU_V1' or row.get('stream')!=stream or type(row.get('pid')) is not int or row['pid']<=0:raise ValueError('marker origin')
  root=rows[-1]
  if root['pid']!=w['pid'] or root.get('mode')!=case:raise ValueError('actual root marker')
  if len(rows)==2 and (rows[0].get('mode')!='resident_child' or rows[0].get('hold_seconds')!=60 or rows[0]['pid']!=root.get('owned_child_pid') or rows[0]['pid']==w['pid']):raise ValueError('actual resident-child marker')
  markers[stream]=rows
 if [{k:v for k,v in x.items() if k!='stream'} for x in markers['stdout']]!=[{k:v for k,v in x.items() if k!='stream'} for x in markers['stderr']]:raise ValueError('stream markers mismatch')
 return {'root_pid':w['pid'],'child_pid':markers['stdout'][0]['pid'] if case in ('resident_success','resident_failure') else None}
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def gate(args):
 if sha(args.admission)!=args.admission_sha256:raise ValueError('external ROOT admission pin')
 a=read(args.admission)
 if a.get('authorization')!='ROOT_COMPILER_CPU_FIXTURE_ADMITTED':raise ValueError('not natively admitted')
 if str(pathlib.Path(args.adapter).resolve())!=a.get('adapter_path') or args.adapter_sha256!=a.get('adapter_sha256') or args.install_symbol!=a.get('install_symbol'):raise ValueError('actual adapter binding')
 files={'driver':pathlib.Path(__file__),'worker':HERE/'worker.py','supervisor':BASE,'adapter':pathlib.Path(args.adapter),'interpreter':pathlib.Path(sys.executable)}
 pins={k:sha(v) for k,v in files.items()}
 if pins['supervisor']!=BASE_SHA or pins['interpreter']!=PY_SHA or any(pins[k]!=a.get(k+'_sha256') for k in files):raise ValueError('exact runtime source pins')
 return a,files,pins
def presence(pid):
 c=subprocess.run([r'C:\Windows\System32\tasklist.exe','/FI','PID eq '+str(pid)],capture_output=True,timeout=3,creationflags=subprocess.CREATE_NO_WINDOW)
 text=c.stdout.decode(errors='replace');return {'pid':pid,'absent':c.returncode==0 and 'No tasks are running' in text,'exit':c.returncode,'stdout':text,'scope':'Point-in-time read-only lookup, no PID control'}
def run_case_child(args):
 a,files,pins=gate(args);folder=pathlib.Path(args.case_dir).resolve(strict=True)
 if (HERE/'native_runs').resolve() not in folder.parents:raise ValueError('owned case confinement')
 module=load(BASE,'private_pinned_compiler_supervisor');adapter=load(args.adapter,'actual_root_admitted_adapter')
 install=getattr(adapter,args.install_symbol);old_wait=module._wait_run;install(module)
 if module._wait_run is old_wait:raise ValueError('adapter did not install private hook')
 cancel=threading.Event();stop=threading.Event();cancel_error=[];thread=None
 if args.case=='cancel':
  def cancel_after_ready():
   end=time.monotonic()+1
   while not stop.is_set():
    if (folder/'root_ready.json').exists():
     if stop.wait(.1):return
     cancel.set();return
    if time.monotonic()>=end:cancel_error.append('root readiness timeout');cancel.set();return
    stop.wait(.005)
  thread=threading.Thread(target=cancel_after_ready,daemon=True);thread.start()
 manifest={'version':1,'run_id':'compiler_'+args.case,'workers':[{'worker_id':args.case,'argv':[sys.executable,'-B',str(files['worker']),'--mode',args.case,'--case-dir',str(folder)],'executable_sha256':pins['interpreter'],'cwd':str(HERE)}],'deadline_seconds':1 if args.case=='timeout' else 5,'startup_seconds':1,'log_limit_bytes':4096,'containment_policy':'kill_on_close'}
 try:r=module.run_workers(manifest,str(folder/'supervisor'),cancel_event=cancel)
 finally:
  stop.set()
  if thread is not None:thread.join(timeout=1)
 restart=module.restart_receipt(str(folder/'supervisor'),manifest['run_id']);ids=validate_result(args.case,r,restart,a['success_reason'])
 if cancel_error or (thread is not None and thread.is_alive()):raise ValueError('cancellation readiness refusal')
 for role,pid in (('root',ids['root_pid']),('child',ids['child_pid'])):
  if pid is None:continue
  ready=read(folder/(role+'_ready.json'))
  if ready!={'role':role,'mode':'resident_child' if role=='child' else args.case,'pid':pid}:raise ValueError('actual READY binding')
 for log in r['logs'].values():
  for stream in ('stdout','stderr'):
   path=(folder/'supervisor'/log[stream+'_path']).resolve(strict=True)
   if (folder/'supervisor').resolve() not in path.parents or path.read_bytes().decode('utf-8',errors='replace')!=log[stream] or path.stat().st_size!=log[stream+'_bytes']:raise ValueError('actual stream files')
 checks=[presence(pid) for pid in ids.values() if pid is not None]
 after={k:sha(v) for k,v in files.items()}
 if after!=pins or sha(args.admission)!=args.admission_sha256 or not all(x['absent'] for x in checks):raise ValueError('pins/PID refusal')
 write(folder/'case_result.json',{'case':args.case,'accepted':True,'result':r,'restart':restart,'pins_before':pins,'pins_after':after,'pid_checks':checks,'scope':'Actual bounded CPU fixture only; not GPU or arbitrary controller-loss certification'})
 return 0
def bounded_child(command,folder,timeout):
 proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 state={'total':0,'overflow':False,'errors':[]};lock=threading.Lock();threads=[]
 def capture(pipe,name):
  try:
   with (folder/name).open('wb') as f:
    while True:
     block=pipe.read(4096)
     if not block:break
     with lock:
      keep=max(0,min(len(block),131072-state['total']));state['total']+=keep;state['overflow']|=keep<len(block)
     f.write(block[:keep])
  except Exception as exc:state['errors'].append(type(exc).__name__)
  finally:pipe.close()
 for pipe,name in ((proc.stdout,'controller.stdout.log'),(proc.stderr,'controller.stderr.log')):
  t=threading.Thread(target=capture,args=(pipe,name),daemon=True);t.start();threads.append(t)
 end=time.monotonic()+timeout;timed=False
 while proc.poll() is None:
  if state['overflow'] or time.monotonic()>=end:timed=True;proc.kill();break
  time.sleep(.01)
 proc.wait(timeout=3)
 for t in threads:t.join(timeout=1)
 check=presence(proc.pid)
 return {'controller_pid':proc.pid,'controller_exit':proc.returncode,'outer_timeout':timed,'capture':state,'reader_joined':not any(t.is_alive() for t in threads),'controller_pid_check':check}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--adapter',required=True);parser.add_argument('--adapter-sha256',required=True);parser.add_argument('--install-symbol',required=True);parser.add_argument('--admission',required=True);parser.add_argument('--admission-sha256',required=True);parser.add_argument('--run',action='store_true');parser.add_argument('--case',choices=CASES);parser.add_argument('--case-dir');args=parser.parse_args()
 if not args.run:print(json.dumps({'status':'NOT_CHECKED','reason':'explicit separate ROOT native admission and --run required'}));return 2
 if os.name!='nt':raise ValueError('Windows fixture only')
 a,files,pins=gate(args)
 if args.case:return run_case_child(args)
 runs=HERE/'native_runs';runs.mkdir(exist_ok=True);folder=runs/('suite_'+str(time.time_ns()));folder.mkdir();end=time.monotonic()+50;cases=[];ok=False
 try:
  for case in CASES:
   cf=folder/case;cf.mkdir();remaining=end-time.monotonic()
   if remaining<=0:raise TimeoutError('50-second work budget, 60-second outer admission required')
   cmd=[sys.executable,'-B',str(pathlib.Path(__file__).resolve()),'--run','--case',case,'--case-dir',str(cf),'--adapter',args.adapter,'--adapter-sha256',args.adapter_sha256,'--install-symbol',args.install_symbol,'--admission',args.admission,'--admission-sha256',args.admission_sha256]
   outer=bounded_child(cmd,cf,min(15,remaining));outer['case']=case;cases.append(outer)
   if outer['controller_exit']!=0 or outer['outer_timeout'] or outer['capture']['overflow'] or outer['capture']['errors'] or not outer['reader_joined'] or not outer['controller_pid_check']['absent']:raise ValueError('actual case controller refusal '+case)
   actual=read(cf/'case_result.json');validate_result(case,actual['result'],actual['restart'],a['success_reason'])
   if actual['pins_before']!=pins or actual['pins_after']!=pins or not all(x.get('absent') is True for x in actual['pid_checks']):raise ValueError('actual case evidence refusal')
   outer['actual']=actual
  ok=True
 finally:
  integrity_error=None;after=None
  try:
   after={k:sha(v) for k,v in files.items()}
   ok=ok and after==pins and sha(args.admission)==args.admission_sha256
  except Exception as exc:
   integrity_error=type(exc).__name__+': '+str(exc);ok=False
  write(folder/'suite_receipt.json',{'status':'FIVE_CPU_FIXTURES_PASS' if ok else 'REFUSED','cases':cases,'pins_before':pins,'pins_after':after,'integrity_error':integrity_error,'scope':'Fixed compiler-root policy CPU fixtures only; no GPU/model/controller-loss certificate'})
 print(json.dumps({'status':'FIVE_CPU_FIXTURES_PASS' if ok else 'REFUSED','suite_receipt':str(folder/'suite_receipt.json')}));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
