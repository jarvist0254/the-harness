"""DRAFT root-admitted BUILD_ONLY variant controller; no execution at import.
Must not execute before actual variant hash/pure+native gates are admitted by root.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,threading,time,datetime,subprocess,sys
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
def qualified_receipts(a):
 variant=a['variant_sha256']
 keys=('pure44_receipt','boundary_receipt','native_suite_receipt')
 for key in keys:
  if digest(a[key+'_path'])!=a[key+'_sha256']:raise ValueError('qualification receipt pin '+key)
 pure=read_json(a['pure44_receipt_path'])
 if pure.get('source_sha256')!=variant or pure.get('tests_run')!=44 or pure.get('failures')!=0 or pure.get('errors')!=0 or pure.get('actual_native_process_calls')!=[] or pure.get('ast_import_gate')!='PASS':raise ValueError('pure44 actual result')
 if len(pure.get('outcomes',[]))!=44 or any(x.get('outcome')!='PASS' for x in pure['outcomes']):raise ValueError('pure44 outcomes')
 boundary=read_json(a['boundary_receipt_path'])
 if boundary.get('case')!='boundary' or boundary.get('status')!='PURE_TESTS_PASS' or boundary.get('exit_code')!=0 or boundary.get('hashes_unchanged') is not True or boundary.get('hashes_before',{}).get('candidate')!=variant or boundary.get('hashes_after',{}).get('candidate')!=variant or boundary.get('pid_absent_after_wait') is not True:raise ValueError('boundary actual result')
 if digest(a['boundary_stderr_path'])!=a['boundary_stderr_sha256'] or b'Ran 5 tests' not in pathlib.Path(a['boundary_stderr_path']).read_bytes() or b'\nOK' not in pathlib.Path(a['boundary_stderr_path']).read_bytes():raise ValueError('boundary actual five tests')
 native=read_json(a['native_suite_receipt_path'])
 expected={'natural':('PROCESS_COMPLETED',None),'nonzero':('FAILED','nonzero_exit'),'timeout':('TIMEOUT','deadline'),'cancel':('CANCELLED','cancelled'),'overflow':('FAILED','LOG_LIMIT')}
 if native.get('source_sha256')!=variant or native.get('overall')!='FIXTURE_EXPECTATIONS_MET' or native.get('containment_policy')!='kill_on_close' or [x.get('case_id') for x in native.get('cases',[])]!=list(expected):raise ValueError('native actual five cases')
 for case in native['cases']:
  result=case.get('supervisor',{});name=case['case_id'];status,reason=expected[name]
  if case.get('outer_failure') or case.get('controller_timeout') is not False or case.get('controller_exit_code')!=0 or case.get('controller_pid_absent_after_wait') is not True or case.get('worker_pids_absent_after_cleanup') is not True or case.get('source_and_runtime_hashes_unchanged') is not True or case.get('controller_source_hash_after')!=variant or case.get('restart_commit_verified') is not True or case.get('restart_matches') is not True or case.get('capture_limit_ok') is not True:raise ValueError('native case refusal '+name)
  if result.get('status')!=status or (reason is not None and result.get('failure_reason')!=reason) or result.get('drain_proof')!='CLEANUP' or result.get('job_active_count')!=0 or result.get('whole_tree_certificate') is not False:raise ValueError('native semantic gates '+name)
  before=case.get('source_and_runtime_hashes_before',{});after=case.get('source_and_runtime_hashes_after',{})
  if before!=after or before.get('source')!=variant or before.get('worker')!=native.get('worker_sha256') or case.get('controller_worker_hash_after')!=native.get('worker_sha256'):raise ValueError('native raw source/runtime pins '+name)
  restart=case.get('restart_receipt',{})
  if any(restart.get(k)!=result.get(k) for k in ('run_id','status','failure_reason','drain_proof','workers','logs')) or restart.get('reattach') is not False or restart.get('replay') is not False or restart.get('job_active_count')!=0 or restart.get('whole_tree_certificate') is not False:raise ValueError('native durable restart '+name)
  workers=result.get('workers',[])
  if len(workers)!=(4 if name=='natural' else 1) or any(x.get('assigned') is not True or x.get('resumed') is not True for x in workers):raise ValueError('native ownership '+name)
  if name=='natural':
   if any(x.get('exit_code')!=0 for x in workers) or len(result.get('logs',{}))!=4:raise ValueError('natural exits/log count')
   for worker in workers:
    log=result['logs'].get(worker['worker_id'],{})
    if log.get('stdout','').strip()!=worker['worker_id']+':stdout' or log.get('stderr','').strip()!=worker['worker_id']+':stderr' or log.get('stdout_overflow') is not False or log.get('stderr_overflow') is not False:raise ValueError('natural actual outputs')
  if name=='nonzero' and workers[0].get('exit_code')!=3:raise ValueError('nonzero discriminator')
  if name=='overflow':
   log=result.get('logs',{}).get(workers[0]['worker_id'],{})
   if log.get('stdout_overflow') is not True or log.get('stdout_bytes')!=1024:raise ValueError('overflow discriminator')
 return {'pure44':44,'boundary':5,'native_fixed_cases':5,'source_sha256':variant,'scope':'Fixed fixtures only; not a 600-second workload or arbitrary controller loss certification'}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--runtime-admission',required=True);parser.add_argument('--runtime-admission-sha256',required=True);args=parser.parse_args()
 if digest(args.runtime_admission)!=args.runtime_admission_sha256:raise ValueError('trusted caller admission pin')
 a=read_json(args.runtime_admission);required={'authorization','plan_sha256','controller_sha256','variant_path','variant_sha256','pure_controls_pass','native_admitted','derived_root','derived_manifest_sha256','configure_cmd_sha256','build_cmd_sha256','cmd_exe','cmd_exe_sha256','copied_clean_manifest_sha256','toolchain_original_pins_sha256','evidence_admission_snapshot_sha256','pure44_receipt_path','pure44_receipt_sha256','boundary_receipt_path','boundary_receipt_sha256','boundary_stderr_path','boundary_stderr_sha256','native_suite_receipt_path','native_suite_receipt_sha256','adapter_path','adapter_sha256','adapter_install_symbol','compiler_success_reason','compiler_native_suite_path','compiler_native_suite_sha256'}
 if set(a)!=required or a['authorization']!='ROOT_BUILD_ONLY_NATIVE_ADMITTED' or a['pure_controls_pass'] is not True or a['native_admitted'] is not True:raise ValueError('strict admission')
 if digest(HERE/'CONTRACT.json')!=a['plan_sha256'] or digest(__file__)!=a['controller_sha256']:raise ValueError('plan/controller binding')
 cfg=read_json(HERE/'CONTRACT.json')
 if a['variant_sha256']!='fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3' or cfg['containment']['base_sha256']!='3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c':raise ValueError('explicit ROOT-admitted FA907 variant and original3CB lineage binding')
 qualification=qualified_receipts(a)
 root=pathlib.Path(a['derived_root']).resolve()
 if str(root).casefold()!=cfg['proposed_new_root'].casefold():raise ValueError('root confinement')
 evidence=root/'evidence'
 run_evidence=evidence/'attempt5_compiler_root_cleanup'
 if run_evidence.exists():raise ValueError('fresh compiler completion attempt output directory required')
 evidence_pins={'derived_manifest.json':a['derived_manifest_sha256'],'copied_clean_manifest.json':a['copied_clean_manifest_sha256'],'toolchain_original_pins.json':a['toolchain_original_pins_sha256'],'admission_snapshot.json':a['evidence_admission_snapshot_sha256']}
 for name,pin in evidence_pins.items():
  if digest(evidence/name)!=pin:raise ValueError('evidence pin '+name)
 derived=read_json(evidence/'derived_manifest.json');original=read_json(evidence/'copied_clean_manifest.json');pins=read_json(evidence/'toolchain_original_pins.json')
 def verify_all():
  if digest(__file__)!=a['controller_sha256'] or digest(args.runtime_admission)!=args.runtime_admission_sha256 or digest(HERE/'CONTRACT.json')!=a['plan_sha256']:raise ValueError('controller/admission/plan changed')
  for name,pin in evidence_pins.items():
   if digest(evidence/name)!=pin:raise ValueError('evidence changed '+name)
  qualified_receipts(a)
  if digest(a['adapter_path'])!=a['adapter_sha256'] or digest(a['compiler_native_suite_path'])!=a['compiler_native_suite_sha256']:raise ValueError('compiler adapter/evidence pins changed')
  if digest(HERE/'job_member_trace.py')!='8127c5263bb2526c4205b4ecc5aa3f2094ac7e134c0b910b8a6ea0f18ef793dd':raise ValueError('diagnostic helper changed')
  for stage in ('configure','build'):
   if digest(root/('build_owned_'+stage+'_attempt5.cmd'))!=a[stage+'_cmd_sha256']:raise ValueError('stage command changed '+stage)
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
  if digest(root/('build_owned_'+stage+'_attempt5.cmd'))!=a[stage+'_cmd_sha256']:raise ValueError('stage command pins')
 # The exact ROOT-admitted variant has side-effect-free imports; native calls only in run_workers.
 spec=importlib.util.spec_from_file_location('root_admitted_build_only_variant',a['variant_path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 if digest(HERE/'job_member_trace.py')!='8127c5263bb2526c4205b4ecc5aa3f2094ac7e134c0b910b8a6ea0f18ef793dd':raise ValueError('diagnostic helper pin')
 run_evidence.mkdir()
 probe_spec=importlib.util.spec_from_file_location('root_admitted_job_member_trace',HERE/'job_member_trace.py');probe_module=importlib.util.module_from_spec(probe_spec);probe_spec.loader.exec_module(probe_module)
 tracer=probe_module.install(module,run_evidence)
 if digest(a['adapter_path'])!=a['adapter_sha256'] or digest(a['compiler_native_suite_path'])!=a['compiler_native_suite_sha256'] or digest(HERE/'native_driver.py')!='e4327908e0da6f668ba7ae51cf92fb641bb7c4e02dde019722a863b8217c3c1d':raise ValueError('compiler policy pins')
 check_spec=importlib.util.spec_from_file_location('pure_fixture_evidence_validator',HERE/'native_driver.py');check_module=importlib.util.module_from_spec(check_spec);check_spec.loader.exec_module(check_module)
 suite=read_json(a['compiler_native_suite_path'])
 if suite.get('status')!='FIVE_CPU_FIXTURES_PASS' or [x.get('case') for x in suite.get('cases',[])]!=list(check_module.CASES) or suite.get('pins_before')!=suite.get('pins_after') or suite['pins_before'].get('supervisor')!=a['variant_sha256'] or suite['pins_before'].get('adapter')!=a['adapter_sha256'] or suite['pins_before'].get('driver')!='e4327908e0da6f668ba7ae51cf92fb641bb7c4e02dde019722a863b8217c3c1d':raise ValueError('actual compiler CPU fixtures binding')
 for case in suite['cases']:
  actual=case.get('actual',{})
  check_module.validate_result(case['case'],actual['result'],actual['restart'],a['compiler_success_reason'])
  if case.get('controller_exit')!=0 or case.get('outer_timeout') is not False or case.get('reader_joined') is not True or case.get('capture',{}).get('overflow') is not False or case['capture'].get('errors')!=[] or case.get('controller_pid_check',{}).get('absent') is not True or actual.get('pins_before')!=suite['pins_before'] or actual.get('pins_after')!=suite['pins_before'] or not actual.get('pid_checks') or not all(x.get('absent') is True for x in actual['pid_checks']):raise ValueError('actual compiler case refusal')
 adapter_spec=importlib.util.spec_from_file_location('root_admitted_compiler_completion_adapter',a['adapter_path']);adapter_module=importlib.util.module_from_spec(adapter_spec);adapter_spec.loader.exec_module(adapter_module)
 getattr(adapter_module,a['adapter_install_symbol'])(module)
 results=[];all_completed=False;failure=None;integrity_failure=None
 try:
  for stage,deadline in [('configure',120),('build',600)]:
   out=run_evidence/(stage+'_contained');progress=run_evidence/(stage+'_progress.json');cancel=threading.Event();stop=threading.Event();start=time.monotonic();heartbeat_errors=[]
   def heartbeat():
    while not stop.is_set():
     try:atomic_json(progress,{'stage':stage,'status':'RUNNING','elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'deadline_seconds':deadline,'scope':'Compiler/shader only; root can read supervisor journal for owned PID'})
     except Exception as e:heartbeat_errors.append(str(e));cancel.set();return
     stop.wait(15)
   manifest={'version':1,'run_id':'fp32_'+stage,'deadline_seconds':deadline,'startup_seconds':10,'log_limit_bytes':131072,'containment_policy':'kill_on_close','workers':[{'worker_id':stage,'argv':[a['cmd_exe'],'/d','/c',str(root/('build_owned_'+stage+'_attempt5.cmd'))],'executable_sha256':a['cmd_exe_sha256'],'cwd':str(root)}]}
   atomic_json(run_evidence/(stage+'_manifest.json'),manifest)
   beat=None
   try:
    beat=threading.Thread(target=heartbeat,daemon=True);beat.start()
    result=module.run_workers(manifest,str(out),cancel_event=cancel)
   finally:
    stop.set()
    if beat is not None and beat.ident is not None:beat.join(timeout=2)
   if beat.is_alive() or heartbeat_errors:raise RuntimeError('uncertain heartbeat durability')
   results.append(result);atomic_json(run_evidence/(stage+'_result_copy.json'),result)
   verify_all()
   if result.get('status')!='COMPILER_ROOT_EXITED_CLEANUP_REQUIRED' or result.get('failure_reason')!=a['compiler_success_reason'] or result.get('drain_proof')!='CLEANUP' or result.get('job_active_count')!=0 or result.get('whole_tree_certificate') is not False or result.get('durability')=='UNKNOWN_DURABILITY':raise RuntimeError('refused stage result/cleanup')
   workers=result.get('workers',[])
   if len(workers)!=1 or workers[0].get('exit_code')!=0 or workers[0].get('assigned') is not True or workers[0].get('resumed') is not True:raise RuntimeError('worker state')
   for stream in ('stdout','stderr'):
    if result.get('logs',{}).get(stage,{}).get(stream+'_overflow') is not False:raise RuntimeError('stream overflow/unknown')
   check=subprocess.run([str(pathlib.Path(a['cmd_exe']).parent/'tasklist.exe'),'/FI','PID eq '+str(workers[0]['pid'])],capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
   presence=check.stdout.decode(errors='replace')
   atomic_json(run_evidence/(stage+'_pid_absence.json'),{'pid':workers[0]['pid'],'tasklist_exit':check.returncode,'stdout':presence,'stderr':check.stderr.decode(errors='replace')})
   if check.returncode!=0 or 'No tasks are running' not in presence:raise RuntimeError('PID absence not verified')
   atomic_json(progress,{'stage':stage,'status':'COMPLETED','elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_worker_receipt':str(out)})
  outputs=[]
  for name in cfg['runtime_dlls']:
   f=root/'build_attempt5/bin'/name
   if not f.is_file():raise RuntimeError('missing fresh DLL '+name)
   outputs.append({'path':str(f),'bytes':f.stat().st_size,'sha256':digest(f)})
  atomic_json(run_evidence/'fresh_dll_manifest.json',outputs)
  all_completed=True
 except BaseException as exc:
  failure=type(exc).__name__+': '+str(exc)
  raise
 finally:
  try:
   verify_all()
   if digest(a['variant_path'])!=a['variant_sha256'] or digest(a['cmd_exe'])!=a['cmd_exe_sha256']:raise RuntimeError('runner/executable changed after build')
  except BaseException as exc:
   integrity_failure=type(exc).__name__+': '+str(exc);all_completed=False
  result_write_failure=None
  try:
   atomic_json(run_evidence/'controller_result.json',{'diagnostic_trace':tracer.metadata,'stages':results,'all_completed':all_completed,'failure':failure,'integrity_failure':integrity_failure,'qualification':qualification,'controller_sha256':a['controller_sha256'],'root_admission_sha256':args.runtime_admission_sha256,'scope':'Fixed contained compiler tree only; no GPU run or reproducible-build claim'})
  except BaseException as exc:
   result_write_failure=type(exc).__name__+': '+str(exc)
   print('controller result write failed: '+result_write_failure,file=sys.stderr)
  if failure is None and (integrity_failure or result_write_failure):raise RuntimeError(integrity_failure or result_write_failure)
if __name__=='__main__':main()
