import importlib.util,pathlib,types,unittest,ctypes,subprocess,os,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\contained_build_policy_20261004T160430Z\contained_build_supervisor.py')
DRIVER=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py')
TRAPS=[]
def deny(*a,**k):TRAPS.append('native/process');raise AssertionError('native/process forbidden')
ctypes.WinDLL=deny;subprocess.Popen=deny;os.system=deny
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE)=='fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3'
assert sha(DRIVER)=='e4327908e0da6f668ba7ae51cf92fb641bb7c4e02dde019722a863b8217c3c1d'
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
driver=load(DRIVER,'actual_driver')
class MemoryPath:
 def __init__(self,name='memory'):self.name=name
 def mkdir(self):pass
 def is_dir(self):return True
 def __truediv__(self,name):return MemoryPath(name)
class Tests(unittest.TestCase):
 def check(self,kind):
  m=load(BASE,'actual_fa907_'+kind);writes=[];journal=[]
  spec={'output':MemoryPath(),'run_id':'mock_'+kind,'policy':'kill_on_close','log_limit':4096}
  m._windows=lambda:True;m._validate=lambda *args:spec;m._imports=lambda:{'_winapi':types.SimpleNamespace()};m._kernel=lambda deps:types.SimpleNamespace(CloseHandle=lambda job:0 if kind=='job_close' else 1);m._open_job=lambda *a:object();m._enable_kill_on_close=lambda *a:None
  m._journal=lambda *args:journal.append(args[1]);m._atomic_write=lambda path,data:writes.append((path.name,data));m._monotonic=lambda:0
  def launch(deps,kernel,job,spec,owned,threads,slots,overflow,cancel):
   owned.append({'worker_id':'success','pid':100,'exit_code':0,'assigned':True,'resumed':True,'ph':object(),'th':object()})
   for stream in ('stdout','stderr'):
    row={'fixture':'COMPILER_COMPLETION_CPU_V1','role':'root','mode':'success','pid':100,'stream':stream,'requested_exit':0}
    slots.append({'worker_id':'success','stream':stream,'data':(json.dumps(row)+'\n').encode(),'overflow':False,'bad_read':kind=='reader','closed':kind!='reader'})
   return 'COMPILER_ROOT_EXITED_CLEANUP_REQUIRED','compiler_root_exited_zero'
  m._launch_and_wait=launch;m._shutdown=lambda *a:(0,'UNKNOWN_DRAIN' if kind=='shutdown' else 'CLEANUP');m._join=lambda *a:True;m._close_owned=lambda *a:kind!='owned_close'
  r=m.run_workers({},'NO_REAL_FILESYSTEM')
  self.assertEqual(r['status'],'COMPILER_ROOT_EXITED_CLEANUP_REQUIRED');self.assertEqual(r['drain_proof'],'UNKNOWN_DRAIN')
  with self.assertRaisesRegex(ValueError,'cleanup/durability refusal'):driver.validate_result('success',r,r,'compiler_root_exited_zero')
  self.assertEqual(TRAPS,[])
  RESULTS.append({'case':kind,'status':r['status'],'drain_proof':r['drain_proof'],'caller_refused':True,'memory_writes':len(writes),'native_process_calls':list(TRAPS)})
 def test_shutdown_unknown(self):self.check('shutdown')
 def test_reader_bad_unclosed(self):self.check('reader')
 def test_owned_close_false(self):self.check('owned_close')
 def test_job_close_false(self):self.check('job_close')
RESULTS=[]
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=2).run(suite)
 (ROOT/'proof_results.json').write_text(json.dumps({'scope':'ACTUAL_FA907_RUN_WORKERS_AND_EMIT_PURE_MOCK_ONLY','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'results':RESULTS,'native_calls':TRAPS,'base_sha256':sha(BASE),'driver_sha256':sha(DRIVER)},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)
