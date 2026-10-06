"""Admitted pure/mock adversarial evaluation. Never launch a real worker."""
import copy, datetime, hashlib, importlib.util, json, os, pathlib, sys, tempfile, types, unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BATCH=ROOT/'records/factory_runs/20261004/supervision_qualification_20261004T121303Z'
S=BATCH/'grok_supervisor_repair/contained_supervisor.syntax_normalized.py'
V=BATCH/'grok_validator_repair/qualification_validator.corrected.py'
EXPECTED={str(S):'7641ed7e865e1a601aeb72be6942f39fb040c8bdd4cec57a34d25fb76e1f4b84',str(V):'f024298ca0d597c8cfa04f00334924f957bb268b0734fb8ff6ce1ca5fa9378f0'}
assert 'RUN_CONTAINMENT_FIXTURES' not in os.environ
for p,h in EXPECTED.items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h
FORBIDDEN=[]
def deny(label):
 def f(*a,**k):
  FORBIDDEN.append(label);raise AssertionError('REAL_NATIVE_OR_PROCESS_FORBIDDEN '+label)
 return f
# Refuse native dependency loading even if a future candidate accidentally reaches it.
import subprocess, ctypes
subprocess.Popen=deny('subprocess.Popen')
subprocess.run=deny('subprocess.run')
os.system=deny('os.system')
ctypes.WinDLL=deny('ctypes.WinDLL')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
cs=load('adversarial_supervisor',S);qv=load('adversarial_validator',V)
cs._imports=deny('supervisor._imports_uninjected')
OBS=[]
def observe(name,data):OBS.append({'case':name,'observation':data})
NOW=datetime.datetime(2026,10,4,12,0,tzinfo=datetime.timezone.utc)
def H(s):return hashlib.sha256(s.encode()).hexdigest()
BINDS={k:H(k) for k in qv.BIND_KEYS}
def device(i,cls='DISCRETE_GPU',vendor=None):
 return {'pci_id':f'0000:{i:02x}:00.0','physical_id':f'p{i}','vendor':vendor or ('NVIDIA' if i%2 else 'AMD'),'device_class':cls,
 'memory':{'kind':'DEDICATED','source':'ACTUAL_ALLOCATOR','total_bytes':8_000_000_000,'free_bytes':6_000_000_000,'reserve_bytes':2_000_000_000,'usable_bytes':6_000_000_000,'highwater_bytes':2_000_000_000,'measured_at':NOW.isoformat()},
 'kernel':{'completed':True,'tensor_sha256':H(f'tensor{i}')},'blocks':[{'block_id':f'layer{i}','owner':f'p{i}','weight_sha256':H(f'weight{i}')}]}
def numerical(ids):
 return dict(BINDS,physical_ids=ids,array_sha256=H('actual_array'),reference_sha256=H('cpu_reference'),full_count=8,finite_count=8,violation_count=0,rmse=1e-6,max_abs_error=1e-6,atol=5e-5,rtol=5e-5,predeclared_atol=5e-5,predeclared_rtol=5e-5)
def control():return dict(BINDS,physical_ids=['p1','p2'],kind='COMPARATOR_ONLY',scope='COMPARE_ONLY',exit_code=1,detected=True,artifact_sha256=H('corruption_artifact'))
def capacity(n):
 ids=[f'p{i}' for i in range(1,n+1)]
 cap=dict(BINDS,source='ACTUAL_ALLOCATOR',quant_sha256=H('quant'),context=2048,batch=1,requirement_bytes=8_000_000_000,
 plans=[{'physical_id':pid,'assigned_bytes':8_000_000_000//n+(8_000_000_000%n if idx==n-1 else 0)} for idx,pid in enumerate(ids)])
 for name,count in [('single',1),('three',3)]:
  cap[name]=dict(BINDS,quant_sha256=cap['quant_sha256'],context=2048,batch=1,device_count=count,physical_ids=ids[:count],failure_kind='ACTUAL_ALLOCATOR_OOM',artifact_sha256=H(name+'oom'))
 return cap
def evaluate(name,claims,devs,**fields):
 r={'schema':1,'timestamp':NOW.isoformat(),'claims':claims,'devices':devs,'bindings':dict(BINDS),**fields}
 shas=[]
 def collect(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k=='sha256' or k.endswith('_sha256'):shas.append(v)
    else:collect(v)
  elif isinstance(x,list):
   for v in x:collect(v)
 collect(r);trust=frozenset(shas);r['artifacts']=[{'sha256':h,'role':'SYNTHETIC_TEST_ONLY'} for h in sorted(trust)]
 result=qv.validate_result(r,now_utc=NOW,trusted_artifact_hashes=trust)
 observe(name,{'result':result,'receipt':r,'trusted_hashes':sorted(trust),'trust_scope':'Synthetic unit fixture; not physical hardware evidence.'});return result
class ValidatorCases(unittest.TestCase):
 def test_positive_two_vendor_baseline(self):
  r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1),device(2)],numerical=numerical(['p1','p2']),controls=[control()]);self.assertEqual(r['status'],'QUALIFIED')
 def test_four_required_exactly_three_devices(self):
  r=evaluate(self.id(),['FOUR_REQUIRED_CAPACITY'],[device(i) for i in range(1,4)],capacity=capacity(3));self.assertNotEqual(r['status'],'QUALIFIED','Three cards and no four-card run cannot prove FOUR_REQUIRED_CAPACITY')
 def test_zero_highwater_no_resident_or_kernel_capacity(self):
  ds=[device(i) for i in range(1,5)]
  for d in ds:d['memory']['highwater_bytes']=0;d.pop('kernel');d.pop('blocks')
  r=evaluate(self.id(),['DEDICATED_CAPACITY_GT_ONE_CARD','FOUR_REQUIRED_CAPACITY'],ds,capacity=capacity(4));self.assertNotEqual(r['status'],'QUALIFIED','Plans and OOM labels do not prove actual allocation or successful inference')
 def test_unrelated_workload_control(self):
  c=control();c['model_sha256']=H('other_model');c['workload_sha256']=H('other_workload');c['physical_ids']=['elsewhere']
  r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1),device(2)],numerical=numerical(['p1','p2']),controls=[c]);self.assertNotEqual(r['status'],'QUALIFIED','Trusted unrelated comparator cannot qualify current model')
 def test_cpu_participants(self):
  r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1,'CPU'),device(2,'CPU')],numerical=numerical(['p1','p2']),controls=[control()]);self.assertNotEqual(r['status'],'QUALIFIED')
 def test_other_participants(self):
  r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1,'OTHER'),device(2,'OTHER')],numerical=numerical(['p1','p2']),controls=[control()]);self.assertNotEqual(r['status'],'QUALIFIED')
 def llm(self):return dict(numerical([]),gguf_sha256=H('licensed_model'),licensed=True,attention_ops=['attention'],kv_ops=['KV_write','KV_read'],vocab=8,type='NUMERICAL_ARRAY')
 def test_llm_without_gpu(self):
  r=evaluate(self.id(),['LLM_LOGIT_PARITY'],[],llm=self.llm(),controls=[control()]);self.assertNotEqual(r['status'],'QUALIFIED','No GPU execution evidence')
 def test_observed_llm_failure_refused(self):
  e=self.llm();e['observed_failure']=True;r=evaluate(self.id(),['LLM_LOGIT_PARITY'],[],llm=e,controls=[control()]);self.assertEqual(r['status'],'REFUSED')
 def test_declared_tolerance_metric_inconsistency(self):
  e=numerical(['p1','p2']);e['max_abs_error']=0;e['rmse']=1e-5
  r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1),device(2)],numerical=e,controls=[control()]);self.assertNotEqual(r['status'],'QUALIFIED','RMSE cannot exceed max absolute error')
 def test_tolerance_loosening_refused_baseline(self):
  e=numerical(['p1','p2']);e['atol']=1;r=evaluate(self.id(),['TWO_VENDOR_NUMERICAL'],[device(1),device(2)],numerical=e,controls=[control()]);self.assertEqual(r['status'],'REFUSED')

class FakeAPI:
 def __init__(self,fail_pipe=None,fail_dup=None,bad_read=False,wait_error=False):self.calls=[];self.next=100;self.pipe_n=0;self.dup_n=0;self.fail_pipe=fail_pipe;self.fail_dup=fail_dup;self.bad_read=bad_read;self.wait_error=wait_error;self.alloc=[];self.proc=[]
 def new(self,kind):self.next+=1;self.alloc.append((kind,self.next));return self.next
 def GetCurrentProcess(self):return -1
 def DuplicateHandle(self,*args):
  self.dup_n+=1
  if self.dup_n==self.fail_dup:raise OSError('injected duplicate failure')
  return self.new('duplicate')
 def CreatePipe(self,*args):
  self.pipe_n+=1
  if self.pipe_n==self.fail_pipe:raise OSError('injected pipe failure')
  return self.new('read'),self.new('write')
 def CreateProcess(self,*args):
  ph,th=self.new('process'),self.new('thread');self.proc.append((ph,th));self.calls.append(('fake_create_process',ph,th));return ph,th,10000+ph,1
 def CloseHandle(self,h):self.calls.append(('close',h))
 def ReadFile(self,*args):return ('INVALID_DATA',0) if self.bad_read else (b'',109)
 def TerminateProcess(self,h,code):self.calls.append(('terminate_process',h))
 def WaitForSingleObject(self,h,ms):
  self.calls.append(('wait',h,ms))
  if self.wait_error:raise OSError('injected wait failure')
  return 0
 def GetExitCodeProcess(self,h):self.calls.append(('exit_code',h));return 0
class FakeKernel:
 def __init__(self,fail_terminate=False):self.calls=[];self.fail_terminate=fail_terminate
 def CreateJobObjectW(self,*args):self.calls.append(('create_job',));return 900
 def AssignProcessToJobObject(self,j,h):self.calls.append(('assign',h));return 1
 def ResumeThread(self,h):self.calls.append(('resume',h));return 1
 def TerminateJobObject(self,j,code):self.calls.append(('terminate_job',));return not self.fail_terminate
 def CloseHandle(self,h):self.calls.append(('close_job',h));return 1
class FakeCT:
 def set_last_error(self,x):pass
 def get_last_error(self):return 5
class Startup:
 def __init__(self):self.dwFlags=0
class ImmediateThread:
 count=0;fail_second=False
 def __init__(self,target,args,daemon):self.target=target;self.args=args
 def start(self):
  type(self).count+=1
  if type(self).fail_second and type(self).count==2:raise RuntimeError('injected second reader start')
  self.target(*self.args)
 def is_alive(self):return False
 def join(self,timeout):pass

def deps(api):return {'_winapi':api,'ctypes':FakeCT(),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda fd:3),'subprocess':types.SimpleNamespace(STARTUPINFO=Startup,STARTF_USESTDHANDLES=256,list2cmdline=lambda av:' '.join(av))}
def spec(out):return {'run_id':'adversarial','workers':[{'worker_id':'w1','argv':['C:\\fake.exe'],'cwd':str(out.parent)}],'env':{},'deadline':10,'startup':5,'log_limit':1024,'policy':'explicit_terminate','output':out,'seq':1}
class SupervisorCases(unittest.TestCase):
 def run_fake(self,api,k,account=lambda *a:(0,1)):
  with tempfile.TemporaryDirectory(dir=HERE) as tmp:
   sp=spec(pathlib.Path(tmp)/'output');ImmediateThread.count=0;ImmediateThread.fail_second=False
   with patch.object(cs,'_validate',return_value=sp),patch.object(cs,'_imports',return_value=deps(api)),patch.object(cs,'_kernel',return_value=k),patch.object(cs,'_accounting',side_effect=account),patch.object(cs.threading,'Thread',ImmediateThread):
    try:return cs.run_workers({},str(sp['output']))
    finally:observe(self.id(),{'fake_api_calls':api.calls,'fake_kernel_calls':k.calls,'allocated_fake_handles':api.alloc})
 def spawn_fake(self,api,fail_second=False):
  k=FakeKernel();owned=[];threads=[];slots=[];ImmediateThread.count=0;ImmediateThread.fail_second=fail_second
  with tempfile.TemporaryDirectory(dir=HERE) as tmp,patch.object(cs.threading,'Thread',ImmediateThread):
   sp=spec(pathlib.Path(tmp)/'output')
   try:
    with self.assertRaises((OSError,RuntimeError)):cs._spawn(deps(api),k,900,sp,sp['workers'][0],owned,threads,slots,threading_event())
   finally:observe(self.id(),{'fake_api_calls':api.calls,'fake_kernel_calls':k.calls,'allocated_fake_handles':api.alloc,'slots':[{k:(v.decode('utf-8','replace') if isinstance(v,bytes) else v) for k,v in s.items()} for s in slots]})
  return api
 def test_second_pipe_failure_no_leaks(self):
  a=self.spawn_fake(FakeAPI(fail_pipe=2));closed=[c[1] for c in a.calls if c[0]=='close'];self.assertEqual(set(closed),{h for _,h in a.alloc},'Successful first pipe pair must remain owned')
 def test_second_writer_duplicate_failure_no_leaks(self):
  a=self.spawn_fake(FakeAPI(fail_dup=3));closed=[c[1] for c in a.calls if c[0]=='close'];self.assertEqual(set(closed),{h for _,h in a.alloc},'Successful stdout duplicate must remain owned')
 def test_second_reader_start_no_double_close(self):
  a=self.spawn_fake(FakeAPI(),True);reads=[h for kind,h in a.alloc if kind=='read'];closed=[c[1] for c in a.calls if c[0]=='close'];self.assertTrue(all(closed.count(h)==1 for h in reads),'Started reader already owns its handle; _spawn must not also close it')
 def test_failed_job_termination_still_waits_roots(self):
  a=FakeAPI();k=FakeKernel(True);owned=[{'ph':123,'th':456,'pid':10000,'exit_code':None}]
  r=cs._shutdown(deps(a),k,900,owned,True);observe(self.id(),{'result':r,'fake_api_calls':a.calls,'fake_kernel_calls':k.calls});self.assertTrue(any(c[0]=='wait' and c[1]==123 for c in a.calls),'Job termination failure cannot skip exact owned-root waits')
 def test_wait_exception_still_closes_owned_handles(self):
  a=FakeAPI(wait_error=True);k=FakeKernel()
  try:self.run_fake(a,k)
  except OSError:pass
  roots=[h for pair in a.proc for h in pair];closed=[c[1] for c in a.calls if c[0]=='close'];self.assertTrue(roots and all(h in closed for h in roots),'Cleanup wait exception must not bypass handle closure')
 def test_query_exception_still_closes_owned_handles(self):
  a=FakeAPI();k=FakeKernel()
  def fail_query(*args):raise OSError('injected accounting query exception')
  try:self.run_fake(a,k,fail_query)
  except OSError:pass
  roots=[h for pair in a.proc for h in pair];closed=[c[1] for c in a.calls if c[0]=='close'];self.assertTrue(roots and all(h in closed for h in roots),'Cleanup query exception must not bypass handle closure')
 def test_bad_read_never_process_completed(self):
  r=self.run_fake(FakeAPI(bad_read=True),FakeKernel());observe(self.id(),{'result':r});self.assertNotEqual(r['status'],'PROCESS_COMPLETED','Malformed reader result cannot establish successful execution logs')
def threading_event():return cs.threading.Event()
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
 report={'source_sha256':EXPECTED,'observations':OBS,'tests_run':result.testsRun,'failure_count':len(result.failures),'error_count':len(result.errors),'failures':[{'test':t.id(),'traceback':tb} for t,tb in result.failures],'errors':[{'test':t.id(),'traceback':tb} for t,tb in result.errors],'native_process_launches_blocked':True,'forbidden_real_api_attempts':FORBIDDEN,'RUN_CONTAINMENT_FIXTURES_present':False,'scope':'All evidence synthetic pure/mock. No worker process, native job, GPU or provider launched.'}
 (HERE/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 sys.exit(0 if result.wasSuccessful() and not FORBIDDEN else 1)
