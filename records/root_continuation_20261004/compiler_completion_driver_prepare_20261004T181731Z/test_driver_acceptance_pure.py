import unittest, importlib.util, pathlib, json, copy, ctypes, subprocess, os
TRAPS=[]
def deny(*args,**kwargs):TRAPS.append('native/process');raise AssertionError('native/process forbidden')
ctypes.WinDLL=deny;subprocess.Popen=deny;os.system=deny
spec=importlib.util.spec_from_file_location('actual_prepared_driver',pathlib.Path(__file__).parent/'native_driver.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sample(case='resident_success'):
 root={'fixture':'COMPILER_COMPLETION_CPU_V1','role':'root','mode':case,'pid':100,'requested_exit':3 if case=='resident_failure' else 0 if case in ('success','resident_success') else None}
 if case in ('resident_success','resident_failure'):root['owned_child_pid']=101
 rows=[{'fixture':'COMPILER_COMPLETION_CPU_V1','role':'child','mode':'resident_child','pid':101,'hold_seconds':60},root] if 'resident' in case else [root]
 log={}
 for stream in ('stdout','stderr'):
  value=''.join(json.dumps(dict(x,stream=stream))+'\n' for x in rows)
  log.update({stream:value,stream+'_bytes':len(value.encode()),stream+'_overflow':False})
 status=m.CUSTOM if case in ('success','resident_success') else {'resident_failure':'FAILED','timeout':'TIMEOUT','cancel':'CANCELLED'}[case]
 reason='mock_root_zero' if status==m.CUSTOM else {'resident_failure':'nonzero_exit','timeout':'deadline','cancel':'cancelled'}[case]
 r={'run_id':'mock','status':status,'failure_reason':reason,'job_active_count':0,'drain_proof':'CLEANUP','whole_tree_certificate':False,'containment_policy':'kill_on_close','reattach':False,'replay':False,'workers':[{'worker_id':case,'pid':100,'assigned':True,'resumed':True,'exit_code':3 if case=='resident_failure' else 1 if case in ('timeout','cancel') else 0}],'logs':{case:log}}
 return r,copy.deepcopy(r)
class Tests(unittest.TestCase):
 def test_all_five_synthetic_shapes(self):
  for case in m.CASES:
   r,restart=sample(case);self.assertEqual(m.validate_result(case,r,restart,'mock_root_zero')['root_pid'],100)
 def refused(self,mutator):
  r,restart=sample();mutator(r)
  with self.assertRaises((ValueError,KeyError)):m.validate_result('resident_success',r,restart,'mock_root_zero')
 def test_generic_status_refused(self):self.refused(lambda r:r.update(status='PROCESS_COMPLETED'))
 def test_wrong_custom_reason_refused(self):self.refused(lambda r:r.update(failure_reason='other'))
 def test_job_still_active_refused(self):self.refused(lambda r:r.update(job_active_count=1))
 def test_bad_drain_refused(self):self.refused(lambda r:r.update(drain_proof='UNKNOWN_DRAIN'))
 def test_bad_durability_refused(self):self.refused(lambda r:r.update(durability='UNKNOWN_DURABILITY'))
 def test_wrong_exit_refused(self):self.refused(lambda r:r['workers'][0].update(exit_code=3))
 def test_assignment_bool_refused(self):self.refused(lambda r:r['workers'][0].update(assigned=1))
 def test_overflow_refused(self):self.refused(lambda r:r['logs']['resident_success'].update(stdout_overflow=True))
 def test_missing_actual_child_refused(self):self.refused(lambda r:r['logs']['resident_success'].update(stdout=r['logs']['resident_success']['stdout'].splitlines()[-1]+'\n'))
 def test_mismatched_stream_pid_refused(self):self.refused(lambda r:r['logs']['resident_success'].update(stderr=r['logs']['resident_success']['stderr'].replace('101','102')))
 def test_restart_mismatch_refused(self):
  r,restart=sample();restart['replay']=True
  with self.assertRaises(ValueError):m.validate_result('resident_success',r,restart,'mock_root_zero')
 def test_duplicate_keys_refused(self):self.refused(lambda r:r['logs']['resident_success'].update(stdout=r['logs']['resident_success']['stdout'].replace('"pid": 101','"pid": 101, "pid": 102')))
 def test_no_native_traps_invoked(self):self.assertEqual(TRAPS,[])
if __name__=='__main__':unittest.main(verbosity=2)
