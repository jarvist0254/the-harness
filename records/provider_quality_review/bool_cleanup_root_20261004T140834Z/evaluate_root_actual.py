"""Expanded actual-source RED tests: only injected fake native APIs/threads."""
import pathlib,sys,os,json,hashlib,datetime,importlib.util,types,tempfile,unittest,subprocess,ctypes,_winapi
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
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

import ast
S=ROOT/'records/root_continuation_20261004/supervisor_cleanup_root_repair/contained_supervisor.py'
EXPECTED='4d8272aa5dbc330e4199b216bd9b3fd3d240c2c8d1c59e223e37d249c936f663'
assert hashlib.sha256(S.read_bytes()).hexdigest()==EXPECTED
tree=ast.parse(S.read_text())
ALLOWED={'__future__','hashlib','json','os','tempfile','threading','time','pathlib'}
for n in tree.body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):
  assert all(x.split('.')[0] in ALLOWED for x in ([n.module] if isinstance(n,ast.ImportFrom) else [a.name for a in n.names]))
 elif isinstance(n,ast.Expr):assert isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)
 elif isinstance(n,ast.Assign):assert isinstance(n.value,(ast.Constant,ast.Tuple))
 else:assert isinstance(n,(ast.FunctionDef,ast.ClassDef))
spec=importlib.util.spec_from_file_location('current_final_supervisor_mock_only',S);cs=importlib.util.module_from_spec(spec);spec.loader.exec_module(cs)
cs._imports=deny('candidate_uninjected_imports')
OBS=[];CONFIG={}
def spec(out):return {'run_id':'adversarial','workers':[],'env':{},'deadline':60,'startup':5,'log_limit':1024,'policy':'explicit_terminate','output':out,'seq':1}

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

BaseAPI=API;BaseKernel=Kernel;BaseScheduler=Scheduler
class API(BaseAPI):
 def WaitForSingleObject(self,handle,ms):
  if ms==0 and CONFIG.get('elapsed_launch') and not CONFIG.get('advanced'):
   CONFIG['clock'][0]+=20;CONFIG['advanced']=True
  if ms>0 and CONFIG.get('wait_consumes'):CONFIG['clock'][0]+=ms/1000.0
  return super().WaitForSingleObject(handle,ms)
 def ReadFile(self,handle,*args):
  index=[h for h,v in self.l.handles.items() if v['kind']=='read'].index(handle)+1
  if index==CONFIG.get('read_index'):
   e=OSError('per-stream failure');e.winerror=5;raise e
  return super().ReadFile(handle,*args)
class Kernel(BaseKernel):
 def TerminateJobObject(self,*args):
  if CONFIG.get('terminate_false'):
   self.calls.append(['terminate_job_bool_false']);return False
  if CONFIG.get('terminate_zero'):
   self.calls.append(['terminate_job_integer_zero']);return 0
  return super().TerminateJobObject(*args)
 def CloseHandle(self,handle):
  if CONFIG.get('job_close_raise'):
   self.l.handles[handle]['close_attempts']+=1;self.l.events.append(['job_close_exception',handle]);raise OSError('job close rejected')
  if CONFIG.get('job_close_bool_false'):
   self.l.handles[handle]['close_attempts']+=1;return False
  return super().CloseHandle(handle)
class Scheduler(BaseScheduler):
 def factory(self,*a,**kw):
  t=super().factory(*a,**kw);CONFIG['clock']=self.clock;original=t.join
  handle=(kw.get('args') if 'args' in kw else a[1])[0]
  alive=t.is_alive
  def is_alive():
   if CONFIG.get('alive_raise'):raise RuntimeError('reader state unavailable')
   return alive()
  t.is_alive=is_alive
  def join(seconds):
   self.l.events.append(['reader_join_attempt',handle,seconds])
   if not t.is_alive():return
   if CONFIG.get('first_join_raise') and not CONFIG.get('join_raised'):
    CONFIG['join_raised']=True;raise RuntimeError('first join rejected')
   if CONFIG.get('join_raise'):
    self.l.events.append(['join_exception']);raise RuntimeError('mock join failure')
   return original(seconds)
  t.join=join;return t

class Cases(unittest.TestCase):
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
    sp=spec(pathlib.Path(tmp)/'out');sp['workers']=[{'worker_id':'w'+str(i),'argv':['C:\\fake.exe'],'cwd':tmp} for i in range(n)]
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
    files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text(errors='replace')} for p in sp['output'].glob('*')} if sp['output'].exists() else {}
    restarted=cs.restart_receipt(str(sp['output']),sp['run_id']) if (sp['output']/f"{sp['run_id']}_receipt.json").exists() else None
   observation={'case':self.id(),'injected':{'pipe':pipe,'dup':dup,'create':create,'construct':construct,'start':start,'mode':mode,'termination':termination,'assign':assign,'resume':resume,'read':read,'wait':wait,'query':query,'close_at':close_at,'job_close_false':job_close_false,'io':io},'result':result,'restart_receipt':restarted,'raised':error,'handle_ledger':l.handles,'ownership_events':l.events,'fake_api_calls':a.calls,'fake_kernel_calls':k.calls,'output_files':files,'mock_time':clock[0],'native_scope':'Fully fake process/job/pipe/thread operations; actual file writes confined to this evaluator folder.'}
   OBS.append(safe(observation));return l,a,k,result,error

 def assert_uncertain(self,r):
  self.assertIsNotNone(r);self.assertNotEqual(r.get('drain_proof'),'CLEANUP')
 def test_baseline(self):
  l,a,k,r,e=self.exercise(read='BROKEN');self.assertIsNone(e);self.assertEqual(r['status'],'PROCESS_COMPLETED');self.assertTrue(l.exact_once())
 def test_terminate_integer_zero(self):
  CONFIG['terminate_zero']=True
  l,a,k,r,e=self.exercise(assign=2);self.assertTrue(l.all_attempted());self.assert_uncertain(r)
 def test_job_close_integer_zero(self):
  l,a,k,r,e=self.exercise(job_close_false=True);self.assertTrue(l.all_attempted());self.assert_uncertain(r)
 def test_job_close_exception(self):
  CONFIG['job_close_raise']=True
  l,a,k,r,e=self.exercise();self.assertTrue(l.all_attempted());self.assert_uncertain(r)
 def test_terminal_journal_durable_receipt(self):
  l,a,k,r,e=self.exercise(io='TERMINAL_JOURNAL');self.assertEqual(r.get('durability'),'UNKNOWN_DURABILITY')
  last=OBS[-1]
  if last['restart_receipt'] is not None:self.assertNotEqual(last['restart_receipt']['status'],'PROCESS_COMPLETED','Restart must not return stale successful receipt after failed terminal commit')
 def test_total_monotonic_join_budget(self):
  clock=[0.0];calls=[]
  class T:
   def join(self,seconds):calls.append(seconds);clock[0]+=seconds
   def is_alive(self):return True
  with patch.object(cs,'_monotonic',side_effect=lambda:clock[0]):
   if 'deadline' in cs._join.__code__.co_varnames:cs._join([T() for _ in range(8)],2,2)
   else:cs._join([T() for _ in range(8)],2)
  OBS.append({'case':self.id(),'join_timeouts':calls,'mock_elapsed':clock[0],'scope':'Fake blocked readers; no real waits'})
  self.assertLessEqual(clock[0],2.001,'One join budget must cover all readers')
 def assert_parent_owned_cleanup(self,l,r):
  self.assertTrue(all(v['close_attempts']>=1 for v in l.handles.values() if v['owner']!='reader'),'All parent-owned handles require close attempts')
  readers={h for h,v in l.handles.items() if v['kind']=='read'};attempts={x[1] for x in l.events if x[0]=='reader_join_attempt'}
  self.assertEqual(readers,attempts,'Every reader must get a join attempt');self.assert_uncertain(r);self.assertNotEqual(r['status'],'PROCESS_COMPLETED')
 def test_join_exception_unknown(self):
  CONFIG['join_raise']=True
  l,a,k,r,e=self.exercise(mode='DEFERRED');self.assert_parent_owned_cleanup(l,r)
 def test_log_write_rejection(self):
  l,a,k,r,e=self.exercise(io='LOG_WRITE');self.assertTrue(l.all_attempted());self.assertEqual(r.get('durability'),'UNKNOWN_DURABILITY')
 def test_receipt_write_rejection(self):
  l,a,k,r,e=self.exercise(io='RECEIPT_WRITE');self.assertTrue(l.all_attempted());self.assertEqual(r.get('durability'),'UNKNOWN_DURABILITY')
 def test_terminate_boolean_false(self):
  CONFIG['terminate_false']=True;l,a,k,r,e=self.exercise(assign=2);self.assertTrue(l.all_attempted());self.assert_uncertain(r)
 def test_job_close_boolean_false(self):
  CONFIG['job_close_bool_false']=True;l,a,k,r,e=self.exercise();self.assertTrue(l.all_attempted());self.assert_uncertain(r)
 def test_cleanup_clock_starts_after_work(self):
  CONFIG['elapsed_launch']=True;l,a,k,r,e=self.exercise();calls=[c for c in a.calls if c[0]=='wait_root' and c[2]>0];self.assertTrue(calls,'Twenty-second successful work must receive a fresh cleanup wait budget')
 def test_alive_exception_remaining_cleanup(self):
  CONFIG['alive_raise']=True;l,a,k,r,e=self.exercise();self.assert_parent_owned_cleanup(l,r)
 def test_shutdown_and_all_joins_share_deadline(self):
  CONFIG['wait_consumes']=True
  l,a,k,r,e=self.exercise(n=4,mode='BLOCKED',wait='FAILED');self.assertLessEqual(OBS[-1]['mock_time'],8.5,'Root waits and eight reader joins must share one eight-second cleanup deadline');self.assert_uncertain(r)
 def test_first_join_exception_attempts_all_readers(self):
  CONFIG['first_join_raise']=True
  l,a,k,r,e=self.exercise(n=4,mode='BLOCKED',wait='FAILED');readers={h for h,v in l.handles.items() if v['kind']=='read'};attempted={event[1] for event in l.events if event[0]=='reader_join_attempt'};self.assertEqual(readers,attempted,'An earlier join exception must not skip remaining reader join attempts');self.assert_uncertain(r)
 def test_job_close_failure_persisted_uncertainty(self):
  l,a,k,r,e=self.exercise(job_close_false=True);saved=OBS[-1]['restart_receipt'];self.assertIsNotNone(saved);self.assertNotEqual(saved['status'],'PROCESS_COMPLETED');self.assertNotEqual(saved['drain_proof'],'CLEANUP')
 def test_writer_close_failure_persisted_uncertainty(self):
  l,a,k,r,e=self.exercise(close_at=1);saved=OBS[-1]['restart_receipt'];self.assertIsNotNone(saved);self.assertNotEqual(saved['status'],'PROCESS_COMPLETED');self.assertNotEqual(saved['drain_proof'],'CLEANUP')
 def tearDown(self):CONFIG.clear()
def close_case(index):
 def test(self):
  l,a,k,r,e=self.exercise(close_at=index);self.assertTrue(l.all_attempted(),'All handles need close attempts despite earlier failure');self.assert_uncertain(r)
 return test
def read_case(index):
 def test(self):
  CONFIG['read_index']=index;l,a,k,r,e=self.exercise();self.assertTrue(l.all_attempted());self.assertNotEqual(r['status'],'PROCESS_COMPLETED')
 return test
for i in range(1,20):setattr(Cases,'test_close_failure_%02d'%i,close_case(i))
for i in range(1,5):setattr(Cases,'test_read_failure_%02d'%i,read_case(i))
class Capture(unittest.TextTestResult):
 def addFailure(self,test,err):super().addFailure(test,err);OUTCOMES.append({'case':test.id(),'outcome':'FAIL','trace':self._exc_info_to_string(err,test)})
 def addError(self,test,err):super().addError(test,err);OUTCOMES.append({'case':test.id(),'outcome':'ERROR','trace':self._exc_info_to_string(err,test)})
 def addSuccess(self,test):super().addSuccess(test);OUTCOMES.append({'case':test.id(),'outcome':'PASS'})
OUTCOMES=[]
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2,resultclass=Capture).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
 assert hashlib.sha256(S.read_bytes()).hexdigest()==EXPECTED
 payload={'scope':'MOCK_ONLY_NOT_NATIVE_QUALIFICATION','source':str(S),'source_sha256':EXPECTED,'ast_import_gate':'PASS','actual_native_process_calls':FORBIDDEN,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'outcomes':OUTCOMES,'observations':OBS,'limitations':['Manifest validation and typed native ABI are injected, not qualified.','Fake scheduling demonstrates selected interleavings, not real concurrency.','CPython CloseHandle raises on failure and returns None on success; those tests use exceptions. Only ctypes job BOOL failure uses integer zero.']}
 (HERE/'root_results.json').write_text(json.dumps(payload,indent=2))
 print(json.dumps({k:v for k,v in payload.items() if k not in ('outcomes','observations')},indent=2))
 sys.exit(0 if result.wasSuccessful() and not FORBIDDEN else 1)
