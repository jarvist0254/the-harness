"""Expanded actual-source RED tests: only injected fake native APIs/threads."""
import pathlib,sys,os,json,hashlib,datetime,importlib.util,types,tempfile,unittest,subprocess,ctypes,_winapi
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=ROOT/'records/root_continuation_20261004/provider_quality_review/adversarial_eval/test_actual_candidates.py'
assert hashlib.sha256(OLD.read_bytes()).hexdigest()=='e5bc15f1fcfe822115ae46c09c16fd7c765d8a624fb254ce4b99a03359d05872'
assert 'RUN_CONTAINMENT_FIXTURES' not in os.environ
FORBIDDEN=[]
def deny(label):
 def call(*a,**kw):FORBIDDEN.append(label);raise AssertionError('FORBIDDEN_REAL_CALL '+label)
 return call
# Guard all actual CPython native callable exports before candidate loading.
for name in dir(_winapi):
 if callable(getattr(_winapi,name)):setattr(_winapi,name,deny('_winapi.'+name))
for name in ['Popen','run','call','check_call','check_output','getoutput','getstatusoutput']:setattr(subprocess,name,deny('subprocess.'+name))
for name in ['system','startfile','spawnl','spawnle','spawnlp','spawnlpe','spawnv','spawnve','spawnvp','spawnvpe','execl','execle','execlp','execlpe','execv','execve','execvp','execvpe']:
 if hasattr(os,name):setattr(os,name,deny('os.'+name))
for name in ['WinDLL','CDLL','OleDLL','PyDLL','LoadLibrary']:
 if hasattr(ctypes,name):setattr(ctypes,name,deny('ctypes.'+name))
class NoDLL:
 def __getattr__(self,name):raise AssertionError('FORBIDDEN_DLL_ATTRIBUTE '+name)
ctypes.windll=NoDLL();ctypes.cdll=NoDLL();ctypes.oledll=NoDLL();ctypes.pydll=NoDLL()
spec=importlib.util.spec_from_file_location('old_fixture_helpers',OLD);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.HERE=HERE;cs=h.cs;qv=h.qv;cs._imports=deny('candidate_uninjected_imports')
OBS=[];GAPS=[]
def safe(x):
 if isinstance(x,bytes):return {'bytes_length':len(x),'sha256':hashlib.sha256(x).hexdigest()}
 if isinstance(x,dict):return {str(k):safe(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [safe(v) for v in x]
 return x
class Ledger:
 def __init__(self):self.next=100;self.handles={};self.events=[];self.close_count=0;self.fail_close_at=None
 def alloc(self,kind,owner):
  self.next+=1;self.handles[self.next]={'kind':kind,'owner':owner,'close_attempts':0,'close_successes':0};self.events.append(['allocated',self.next,kind,owner]);return self.next
 def close(self,x):
  self.close_count+=1;entry=self.handles[x];entry['close_attempts']+=1;self.events.append(['close_attempt',x])
  if self.close_count==self.fail_close_at:self.events.append(['close_failure',x]);raise OSError('injected close failure')
  entry['close_successes']+=1;entry['owner']='CLOSED';self.events.append(['close_success',x])
 def transfer(self,x,owner):self.handles[x]['owner']=owner;self.events.append(['transfer',x,owner])
 def all_attempted(self):return all(x['close_attempts']>=1 for x in self.handles.values())
 def exact_once(self):return all(x['close_attempts']==1 and x['close_successes']==1 for x in self.handles.values())
class API:
 def __init__(self,ledger,pipe=None,dup=None,create=None,read='EOF',wait='OK',exit_error=False):self.l=ledger;self.pipe_fail=pipe;self.dup_fail=dup;self.create_fail=create;self.read=read;self.wait=wait;self.exit_error=exit_error;self.calls=[];self.pn=self.dn=self.cn=0;self.roots=[]
 def GetCurrentProcess(self):return -1
 def DuplicateHandle(self,*a):
  self.dn+=1
  if self.dn==self.dup_fail:raise OSError('duplicate '+str(self.dn))
  return self.l.alloc('duplicate','launch')
 def CreatePipe(self,*a):
  self.pn+=1
  if self.pn==self.pipe_fail:raise OSError('pipe '+str(self.pn))
  return self.l.alloc('read','launch'),self.l.alloc('write','launch')
 def CreateProcess(self,*a):
  self.cn+=1
  if self.cn==self.create_fail:raise OSError('create '+str(self.cn))
  ph,th=self.l.alloc('process','supervisor'),self.l.alloc('thread','supervisor');self.roots.append((ph,th));self.calls.append(['fake_create',ph,th]);return ph,th,10000+ph,1
 def CloseHandle(self,x):self.l.close(x)
 def ReadFile(self,*a):
  if self.read in ('ERROR','BROKEN'):
   e=OSError('simulated native pipe exception');e.winerror=109 if self.read=='BROKEN' else 5;raise e
  if self.read=='BAD':return 'not bytes',0
  if self.read=='BOOL_ERROR':return b'',True
  if self.read=='ERR_CODE':return b'',5
  return b'',109
 def TerminateProcess(self,x,code):self.calls.append(['terminate_root',x]);return None
 def WaitForSingleObject(self,x,ms):
  self.calls.append(['wait_root',x,ms]);self.l.events.append(['wait_root',x,ms])
  if self.wait=='RAISE':raise OSError('wait failure')
  if self.wait=='FAILED':return 0xffffffff
  if self.wait=='TIMEOUT':return 258
  return 0
 def GetExitCodeProcess(self,x):
  self.calls.append(['exit_code',x])
  if self.exit_error:raise OSError('get exit failure')
  return 0
class Kernel:
 def __init__(self,l,terminate='OK',assign=None,resume=None,close_false=False):self.l=l;self.calls=[];self.termination=terminate;self.an=self.rn=0;self.assign_fail=assign;self.resume_fail=resume;self.close_false=close_false
 def CreateJobObjectW(self,*a):self.job=self.l.alloc('job','supervisor');return self.job
 def AssignProcessToJobObject(self,j,p):
  self.an+=1;self.calls.append(['assign',p]);return self.an!=self.assign_fail
 def ResumeThread(self,t):self.rn+=1;self.calls.append(['resume',t]);return 0xffffffff if self.rn==self.resume_fail else 1
 def TerminateJobObject(self,*a):
  self.calls.append(['terminate_job']);self.l.events.append(['terminate_job'])
  if self.termination=='RAISE':raise OSError('terminate job failure')
  return self.termination!='FALSE'
 def CloseHandle(self,x):
  if self.close_false:self.l.handles[x]['close_attempts']+=1;self.l.events.append(['close_failure_bool',x]);return 0
  self.l.close(x);return 1
class CT:
 def set_last_error(self,x):pass
 def get_last_error(self):return 5
class Startup:
 def __init__(self):self.dwFlags=0
class Scheduler:
 def __init__(self,l,cancel,clock,construct=None,start=None,mode='IMMEDIATE'):self.l=l;self.cancel=cancel;self.clock=clock;self.construct_fail=construct;self.start_fail=start;self.mode=mode;self.created=0;self.started=0;self.threads=[]
 def factory(self,target,args,daemon):
  self.created+=1
  if self.created==self.construct_fail:raise RuntimeError('thread constructor failure')
  sch=self
  class T:
   def __init__(self):self.alive=False
   def start(self):
    sch.started+=1
    if sch.started==sch.start_fail:raise RuntimeError('thread start failure')
    sch.l.transfer(args[0],'reader');self.alive=True
    if sch.mode=='IMMEDIATE':target(*args);self.alive=False
   def is_alive(self):return self.alive
   def join(self,seconds):
    sch.clock[0]+=seconds
    if sch.mode=='CANCEL_JOIN':sch.cancel.set()
    if sch.mode!='BLOCKED':target(*args);self.alive=False
  t=T();self.threads.append(t);return t
class SupervisorExpanded(unittest.TestCase):
 def exercise(self,*,pipe=None,dup=None,create=None,construct=None,start=None,mode='IMMEDIATE',termination='OK',assign=None,resume=None,read='EOF',wait='OK',exit_error=False,query='OK',close_at=None,job_close_false=False,io=None,n=2):
  l=Ledger();l.fail_close_at=close_at;a=API(l,pipe,dup,create,read,wait,exit_error);k=Kernel(l,termination,assign,resume,job_close_false);clock=[0.0];cancel=cs.threading.Event();sch=Scheduler(l,cancel,clock,construct,start,mode);result=None;error=None
  def mono():clock[0]+=0.01;return clock[0]
  def sleep(s):clock[0]+=s
  def account(*a):
   if query=='RAISE':raise OSError('accounting failure')
   return None if query=='FAIL' else (0,len(a_api.roots))
  a_api=a
  deps={'_winapi':a,'ctypes':CT(),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda x:3),'subprocess':types.SimpleNamespace(STARTUPINFO=Startup,STARTF_USESTDHANDLES=256,list2cmdline=lambda x:' '.join(x))}
  with tempfile.TemporaryDirectory(dir=HERE) as tmp:
   sp=h.spec(pathlib.Path(tmp)/'out');sp['workers']=[{'worker_id':'w'+str(i),'argv':['C:\\fake.exe'],'cwd':tmp} for i in range(n)]
   original_journal=cs._journal;original_write=cs._atomic_write;journal_calls=[0]
   def journal(spec,event):
    journal_calls[0]+=1
    if (io=='START_JOURNAL' and journal_calls[0]==1) or (io=='RESUME_JOURNAL' and event['event']=='resumed') or (io=='TERMINAL_JOURNAL' and event['event']=='terminal'):raise OSError('journal write rejected')
    return original_journal(spec,event)
   def atomic(path,data):
    if io=='LOG_WRITE' and str(path).endswith('.log'):raise OSError('log write rejected')
    if io=='RECEIPT_WRITE' and str(path).endswith('_receipt.json'):raise OSError('receipt write rejected')
    return original_write(path,data)
   with patch.object(cs,'_validate',return_value=sp),patch.object(cs,'_imports',return_value=deps),patch.object(cs,'_kernel',return_value=k),patch.object(cs,'_accounting',side_effect=account),patch.object(cs,'_monotonic',side_effect=mono),patch.object(cs,'_sleep',side_effect=sleep),patch.object(cs.threading,'Thread',sch.factory),patch.object(cs,'_journal',side_effect=journal),patch.object(cs,'_atomic_write',side_effect=atomic):
    try:result=cs.run_workers({},str(sp['output']),cancel_event=cancel)
    except Exception as e:error={'type':type(e).__name__,'message':str(e)}
   files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sp['output'].glob('*')} if sp['output'].exists() else {}
  observation={'case':self.id(),'injected':{'pipe':pipe,'dup':dup,'create':create,'construct':construct,'start':start,'mode':mode,'termination':termination,'assign':assign,'resume':resume,'read':read,'wait':wait,'query':query,'close_at':close_at,'job_close_false':job_close_false,'io':io},'result':result,'raised':error,'handle_ledger':l.handles,'ownership_events':l.events,'fake_api_calls':a.calls,'fake_kernel_calls':k.calls,'output_files':files,'mock_time':clock[0],'native_scope':'Fully fake process/job/pipe/thread operations; actual file writes confined to this evaluator folder.'}
  OBS.append(safe(observation));return l,a,k,result,error
 def test_successful_fake_baseline(self):
  l,a,k,r,e=self.exercise();self.assertIsNone(e);self.assertEqual(r['status'],'PROCESS_COMPLETED');self.assertTrue(l.exact_once())
 def allocation(self,**kw):
  l,a,k,r,e=self.exercise(n=kw.pop('n',1),**kw);self.assertTrue(l.exact_once(),'All successfully allocated handles must close exactly once')
 def test_first_pipe(self):self.allocation(pipe=1)
 def test_second_pipe(self):self.allocation(pipe=2)
 def test_stdin_duplicate(self):self.allocation(dup=1)
 def test_stdout_duplicate(self):self.allocation(dup=2)
 def test_stderr_duplicate(self):self.allocation(dup=3)
 def test_first_thread_construct(self):self.allocation(construct=1)
 def test_second_thread_construct(self):self.allocation(construct=2)
 def test_first_thread_start(self):self.allocation(start=1)
 def test_second_thread_start(self):self.allocation(start=2)
 def test_second_process_create(self):self.allocation(create=2,n=2)
 def test_second_assign(self):
  l,a,k,r,e=self.exercise(assign=2);self.assertTrue(l.exact_once());self.assertEqual(k.rn,1);self.assertTrue(all(any(c[0]=='wait_root' and c[1]==p for c in a.calls) for p,t in a.roots))
 def test_second_resume(self):
  l,a,k,r,e=self.exercise(resume=2);self.assertTrue(l.exact_once());self.assertEqual(r['status'],'FAILED')
 def termination_waits(self,**kw):
  if kw.get('termination','OK')!='OK':kw['assign']=2
  l,a,k,r,e=self.exercise(**kw);
  if kw.get('termination','OK')!='OK':
   at=next(i for i,x in enumerate(l.events) if x[0]=='terminate_job');self.assertTrue(all(any(c[0]=='wait_root' and c[1]==p for c in l.events[at+1:]) for p,t in a.roots),'Failed job termination must not skip subsequent root waits')
  self.assertTrue(all(any(c[0]=='wait_root' and c[1]==p for c in a.calls) for p,t in a.roots),'Every exact owned root still needs wait attempts');self.assertTrue(l.all_attempted(),'Cleanup cannot skip owned handles');self.assertTrue(r is None or r.get('drain_proof')!='CLEANUP')
 def test_terminate_false(self):self.termination_waits(termination='FALSE',read='BAD')
 def test_terminate_raises(self):self.termination_waits(termination='RAISE',read='BAD')
 def test_wait_raises(self):self.termination_waits(wait='RAISE')
 def test_wait_failed(self):self.termination_waits(wait='FAILED')
 def test_wait_timeout(self):self.termination_waits(wait='TIMEOUT')
 def test_exit_raises(self):self.termination_waits(exit_error=True)
 def test_query_raises(self):self.termination_waits(query='RAISE')
 def test_query_failure(self):self.termination_waits(query='FAIL')
 def close_failure(self,**kw):
  l,a,k,r,e=self.exercise(**kw);self.assertTrue(l.all_attempted(),'One close failure cannot prevent later closes');self.assertTrue(r is None or r.get('drain_proof')!='CLEANUP','Failed handle release cannot be called cleanup-proven')
 def test_close_first(self):self.close_failure(close_at=1)
 def test_close_reader(self):self.close_failure(close_at=6)
 def test_close_root_thread(self):self.close_failure(close_at=15)
 def test_close_job_false(self):self.close_failure(job_close_false=True)
 def read_rejects(self,read):
  l,a,k,r,e=self.exercise(read=read);self.assertTrue(r is None or r['status']!='PROCESS_COMPLETED','Pipe errors cannot silently complete');self.assertTrue(l.all_attempted())
 def test_pipe_bad_data(self):self.read_rejects('BAD')
 def test_pipe_bool_error(self):self.read_rejects('BOOL_ERROR')
 def test_pipe_error_code(self):self.read_rejects('ERR_CODE')
 def test_pipe_raises(self):self.read_rejects('ERROR')
 def test_cancel_during_join(self):
  l,a,k,r,e=self.exercise(mode='CANCEL_JOIN');self.assertIsNone(e);self.assertEqual(r['status'],'CANCELLED')
 def test_blocked_reader_uncertain(self):
  l,a,k,r,e=self.exercise(mode='BLOCKED');self.assertTrue(r is None or r['status']!='PROCESS_COMPLETED');self.assertTrue(r is None or r['drain_proof']=='UNKNOWN')
 def io_rejects(self,io):
  l,a,k,r,e=self.exercise(io=io);self.assertTrue(l.all_attempted());self.assertTrue(all(any(c[0]=='wait_root' and c[1]==p for c in a.calls) for p,t in a.roots));self.assertTrue(r is None or r['status']!='PROCESS_COMPLETED')
 def test_start_journal(self):self.io_rejects('START_JOURNAL')
 def test_resumed_journal(self):self.io_rejects('RESUME_JOURNAL')
 def test_log_write(self):self.io_rejects('LOG_WRITE')
 def test_receipt_write(self):self.io_rejects('RECEIPT_WRITE')
 def test_terminal_journal(self):self.io_rejects('TERMINAL_JOURNAL')

 def test_native_broken_pipe_healthy_eof(self):
  l,a,k,r,e=self.exercise(read='BROKEN');self.assertIsNone(e);self.assertEqual(r['status'],'PROCESS_COMPLETED');self.assertTrue(l.exact_once())

class ValidatorExpanded(unittest.TestCase):
 def fixture(self,claims=None):
  ds=[h.device(i) for i in range(1,5)];cap=h.capacity(4);nums=h.numerical(['p1','p2','p3','p4']);control=h.control();control['physical_ids']=nums['physical_ids'];control['full_count']=8;control['dimensions']=[1,8];control['measured_at']=h.NOW.isoformat()
  for d in ds:
   d['memory']['highwater_bytes']=2_000_000_000;d['memory']['artifact_sha256']=h.H('allocator-'+d['physical_id'])
   d['kernel'].update(h.BINDS,physical_ids=[d['physical_id']],full_count=8,dimensions=[1,8],measured_at=h.NOW.isoformat())
   d['blocks'][0].update(h.BINDS,resident_bytes=2_000_000_000,measured_at=h.NOW.isoformat(),artifact_sha256=h.H('residency-'+d['physical_id']))
  nums.update(dimensions=[1,8],measured_at=h.NOW.isoformat())
  cap['four']=dict(nums,status='PASS',quant_sha256=cap['quant_sha256'],context=2048,batch=1,device_count=4,controls=[control])
  body={'schema':1,'timestamp':h.NOW.isoformat(),'bindings':dict(h.BINDS),'claims':claims or ['FOUR_REQUIRED_CAPACITY'],'devices':ds,'capacity':cap,'numerical':nums,'controls':[control]}
  return body
 def check(self,body,missing_hash=None):
  found=[]
  def collect(x):
   if isinstance(x,dict):
    for k,v in x.items():
     if k=='sha256' or k.endswith('_sha256'):found.append(v)
     else:collect(v)
   elif isinstance(x,list):
    for v in x:collect(v)
  collect(body);trust=set(found);body['artifacts']=[{'sha256':x,'role':'SYNTHETIC_TEST'} for x in sorted(trust)]
  if missing_hash:trust.discard(missing_hash)
  r=qv.validate_result(body,now_utc=h.NOW,trusted_artifact_hashes=frozenset(trust));OBS.append({'case':self.id(),'receipt':body,'trusted_hashes':sorted(trust),'result':r,'scope':'Synthetic structured evidence only; no measurements/hardware proof.'});return r
 def rejects(self,body,missing_hash=None):self.assertNotEqual(self.check(body,missing_hash)['status'],'QUALIFIED')
 def test_four_baseline(self):self.assertEqual(self.check(self.fixture())['status'],'QUALIFIED')
 def test_only_three_card_count(self):
  b=self.fixture();b['devices']=b['devices'][:3];b['capacity']['plans']=b['capacity']['plans'][:3]
  counts=[2_666_666_667,2_666_666_667,2_666_666_666]
  for d,p,n in zip(b['devices'],b['capacity']['plans'],counts):d['memory']['highwater_bytes']=n;d['blocks'][0]['resident_bytes']=n;p['assigned_bytes']=n
  b['capacity']['four']['device_count']=3;b['capacity']['four']['physical_ids']=['p1','p2','p3'];b['numerical']['physical_ids']=['p1','p2','p3'];b['controls'][0]['physical_ids']=['p1','p2','p3'];self.rejects(b)
 def test_highwater_only_zero(self):
  b=self.fixture()
  for d in b['devices']:d['memory']['highwater_bytes']=0
  self.rejects(b)
 def test_missing_gpu_completion_only(self):
  b=self.fixture();b['devices'][0]['kernel']['completed']=False;self.rejects(b)
 def test_missing_four_success_only(self):
  b=self.fixture();b['capacity'].pop('four');self.rejects(b)
 def test_failed_four_success_only(self):
  b=self.fixture();b['capacity']['four']['status']='FAIL';b['capacity']['four']['violation_count']=1;self.rejects(b)
 def test_unrelated_control_workload_only(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['controls'][0]['workload_sha256']=h.H('another_workload');self.rejects(b)
 def test_control_dimensions_only(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['controls'][0]['dimensions']=[2,4];self.rejects(b)
 def test_control_physical_ids_only(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['controls'][0]['physical_ids']=['p1','p2'];self.rejects(b)
 def test_rmse_only_contradiction(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['numerical']['rmse']=1e-5;b['numerical']['max_abs_error']=0;self.rejects(b)
 def test_nonnumeric_control_exit(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['controls'][0]['exit_code']='1';self.rejects(b)
 def test_bad_artifact_trust(self):
  b=self.fixture();self.rejects(b,b['devices'][0]['memory']['artifact_sha256'])
 def test_cpu_participants_consistent_host_memory(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL'])
  for d in b['devices']:d['device_class']='CPU';d['memory']['kind']='SHARED_HOST'
  self.rejects(b)
 def test_other_participants(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL'])
  for d in b['devices']:d['device_class']='OTHER';d['memory']['kind']='UNKNOWN';d['memory']['source']='UNKNOWN'
  self.rejects(b)
 def llm_fixture(self):
  b=self.fixture(['LLM_LOGIT_PARITY']);b['llm']=dict(h.numerical([]),type='NUMERICAL_ARRAY',licensed=True,gguf_sha256=h.BINDS['model_sha256'],attention_ops=['attention'],kv_ops=['kv_update'],vocab=8,dimensions=[1,8]);b['devices']=[];b['controls'][0]['physical_ids']=[];b.pop('capacity');b.pop('numerical');return b
 def test_no_gpu_llm_consistent_control_ids(self):self.rejects(self.llm_fixture())
 def test_observed_failed_llm_parity(self):
  b=self.llm_fixture();b['llm']['observed_failure']=True;self.rejects(b)
 def test_unbound_llm_model(self):
  b=self.llm_fixture();b['devices']=[h.device(i) for i in range(1,5)];b['llm']['physical_ids']=['p1','p2','p3','p4'];b['controls'][0]['physical_ids']=['p1','p2','p3','p4'];b['llm']['gguf_sha256']=h.H('different_model');self.rejects(b)
 def test_missing_tolerance_declaration(self):
  b=self.fixture(['TWO_VENDOR_NUMERICAL']);b['numerical'].pop('predeclared_atol');b['numerical'].pop('predeclared_rtol');self.rejects(b)

if __name__=='__main__':
 GAPS.extend([
  'Old documented capacity schema has no four-success/resident-byte artifact fields. Supplementary four-run evidence was supplied explicitly but ignored by candidate; failures show an architectural gate gap, not an assertion that its old schema authenticates these extra fields.',
  'Provider ROOT_STATIC_ADMISSION is ignored; external exact hashes establish this evaluator authorization. No manufactured runtime assertion about an undocumented admission API.',
  'Real ABI behavior and actual concurrency are not established by fake threads or handles. Blocking/join schedules are deterministic simulations.',
  'Final journal write failure after an atomic terminal receipt may raise after cleanup. Whether restart accepts that partial sequence is a documented design gap, not a manufactured durability claim.'
 ])
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SupervisorExpanded),unittest.defaultTestLoader.loadTestsFromTestCase(ValidatorExpanded)])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 forbidden=FORBIDDEN+h.FORBIDDEN
 receipt={'source_sha256':h.EXPECTED,'source_sha256_after':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in h.EXPECTED},'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'failure_details':[{'case':t.id(),'traceback':s} for t,s in result.failures],'error_details':[{'case':t.id(),'traceback':s} for t,s in result.errors],'case_observations':OBS,'native_api_attempts':forbidden,'native_calls':0,'real_workers':0,'GPU_calls':0,'fixture_env_present':False,'test_gaps':GAPS,'classification':'EXPANDED_ACTUAL_IMPORT_MOCK_ONLY_RED_BASELINE'}
 (HERE/'RED_results.json').write_text(json.dumps(safe(receipt),indent=2)+'\n',encoding='utf-8')
 sys.exit(0 if result.wasSuccessful() and not forbidden else 1)
