"""DRAFT root-admitted BUILD_ONLY variant controller; no execution at import.
Must not execute before actual variant hash/pure+native gates are admitted by root.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,threading,time,datetime,subprocess
HERE=pathlib.Path(__file__).resolve().parent
def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def read_json(p):
 def pairs(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('duplicate keys')
   d[k]=v
  return d
 return json.loads(pathlib.Path(p).read_text(),object_pairs_hook=pairs)
def atomic_json(path,obj):
 path=pathlib.Path(path);tmp=path.with_suffix('.part')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--runtime-admission',required=True);parser.add_argument('--runtime-admission-sha256',required=True);args=parser.parse_args()
 if digest(args.runtime_admission)!=args.runtime_admission_sha256:raise ValueError('trusted caller admission pin')
 a=read_json(args.runtime_admission);required={'authorization','plan_sha256','controller_sha256','variant_path','variant_sha256','pure_controls_pass','native_admitted','derived_root','derived_manifest_sha256','configure_cmd_sha256','build_cmd_sha256','cmd_exe','cmd_exe_sha256'}
 if set(a)!=required or a['authorization']!='ROOT_BUILD_ONLY_NATIVE_ADMITTED' or a['pure_controls_pass'] is not True or a['native_admitted'] is not True:raise ValueError('strict admission')
 if digest(HERE/'CONTRACT.json')!=a['plan_sha256'] or digest(__file__)!=a['controller_sha256']:raise ValueError('plan/controller binding')
 cfg=read_json(HERE/'CONTRACT.json');root=pathlib.Path(a['derived_root']).resolve()
 if str(root).casefold()!=cfg['proposed_new_root'].casefold():raise ValueError('root confinement')
 evidence=root/'evidence';assert digest(evidence/'derived_manifest.json')==a['derived_manifest_sha256']
 derived=read_json(evidence/'derived_manifest.json');original=read_json(evidence/'copied_clean_manifest.json');pins=read_json(evidence/'toolchain_original_pins.json')
 def verify_all():
  for item in derived:
   f=root/'source'/item['path']
   if f.stat().st_size!=item['bytes'] or digest(f)!=item['sha256']:raise ValueError('derived source changed')
  for item in original:
   f=pathlib.Path(cfg['baseline_source'])/item['path']
   if f.stat().st_size!=item['bytes'] or digest(f)!=item['sha256']:raise ValueError('original source changed')
  for item in pins:
   if digest(item['path'])!=item['sha256']:raise ValueError('original toolchain/DLL changed')
 verify_all()
 if digest(a['variant_path'])!=a['variant_sha256'] or digest(a['cmd_exe'])!=a['cmd_exe_sha256']:raise ValueError('runner executable pins')
 for stage in ('configure','build'):
  if digest(root/('build_owned_'+stage+'.cmd'))!=a[stage+'_cmd_sha256']:raise ValueError('stage command pins')
 # The exact ROOT-admitted variant has side-effect-free imports; native calls only in run_workers.
 spec=importlib.util.spec_from_file_location('root_admitted_build_only_variant',a['variant_path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 results=[];all_completed=False
 try:
  for stage,deadline in [('configure',60),('build',600)]:
   out=evidence/(stage+'_contained');progress=evidence/(stage+'_progress.json');cancel=threading.Event();stop=threading.Event();start=time.monotonic();heartbeat_errors=[]
   def heartbeat():
    while not stop.is_set():
     try:atomic_json(progress,{'stage':stage,'status':'RUNNING','elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'deadline_seconds':deadline,'scope':'Compiler/shader only; root can read supervisor journal for owned PID'})
     except Exception as e:heartbeat_errors.append(str(e));cancel.set();return
     stop.wait(15)
   beat=threading.Thread(target=heartbeat,daemon=True);beat.start()
   manifest={'version':1,'run_id':'fp32_'+stage,'deadline_seconds':deadline,'startup_seconds':10,'log_limit_bytes':131072,'containment_policy':'kill_on_close','workers':[{'worker_id':stage,'argv':[a['cmd_exe'],'/d','/c',str(root/('build_owned_'+stage+'.cmd'))],'executable_sha256':a['cmd_exe_sha256'],'cwd':str(root)}]}
   atomic_json(evidence/(stage+'_manifest.json'),manifest)
   try:result=module.run_workers(manifest,str(out),cancel_event=cancel)
   finally:stop.set();beat.join(timeout=2)
   if beat.is_alive() or heartbeat_errors:raise RuntimeError('uncertain heartbeat durability')
   results.append(result);atomic_json(evidence/(stage+'_result_copy.json'),result)
   verify_all()
   if result.get('status')!='PROCESS_COMPLETED' or result.get('drain_proof')!='CLEANUP' or result.get('job_active_count')!=0:raise RuntimeError('refused stage result/cleanup')
   workers=result.get('workers',[])
   if len(workers)!=1 or workers[0].get('exit_code')!=0 or workers[0].get('assigned') is not True or workers[0].get('resumed') is not True:raise RuntimeError('worker state')
   for stream in ('stdout','stderr'):
    if result.get('logs',{}).get(stage,{}).get(stream+'_overflow') is not False:raise RuntimeError('stream overflow/unknown')
   check=subprocess.run([str(pathlib.Path(a['cmd_exe']).parent/'tasklist.exe'),'/FI','PID eq '+str(workers[0]['pid'])],capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
   presence=check.stdout.decode(errors='replace')
   atomic_json(evidence/(stage+'_pid_absence.json'),{'pid':workers[0]['pid'],'tasklist_exit':check.returncode,'stdout':presence,'stderr':check.stderr.decode(errors='replace')})
   if check.returncode!=0 or 'No tasks are running' not in presence:raise RuntimeError('PID absence not verified')
   atomic_json(progress,{'stage':stage,'status':'COMPLETED','elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_worker_receipt':str(out)})
  outputs=[]
  for name in cfg['runtime_dlls']:
   f=root/'build/bin'/name
   if not f.is_file():raise RuntimeError('missing fresh DLL '+name)
   outputs.append({'path':str(f),'bytes':f.stat().st_size,'sha256':digest(f)})
  atomic_json(evidence/'fresh_dll_manifest.json',outputs)
  all_completed=True
 finally:
  verify_all()
  if digest(a['variant_path'])!=a['variant_sha256'] or digest(a['cmd_exe'])!=a['cmd_exe_sha256']:raise RuntimeError('runner/executable changed after build')
  atomic_json(evidence/'controller_result.json',{'stages':results,'all_completed':all_completed,'scope':'Fixed contained compiler tree only; no GPU run or reproducible-build claim'})
if __name__=='__main__':main()
