"""Independent actual-file RED controls; synthetic only, no hardware qualification."""
import pathlib,hashlib,importlib.util,math,unittest,json,builtins,sys
SOURCE=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_vulkan_numeric_state_ledger\source.qwen_untrusted.py')
PIN='6dfb6a72a1310d23cf435c73f32dcd0b6a57b85cef774c9a47c8748ce3e68dc1'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==PIN
TRAPS=[]
original_import=builtins.__import__
def guarded(name,*a,**kw):
 if name.split('.')[0] in {'ctypes','_winapi','subprocess','multiprocessing','socket','pyopencl','numpy','torch','cupy'}:
  TRAPS.append(name);raise AssertionError('native/process/network/GPU dependency forbidden')
 return original_import(name,*a,**kw)
builtins.__import__=guarded
spec=importlib.util.spec_from_file_location('actual_delivered_ledger',SOURCE);sl=importlib.util.module_from_spec(spec);spec.loader.exec_module(sl)
COUNT=151936
ZERO=[0.0]*COUNT
ZERO_SHA=hashlib.sha256(sl.canonical_payload_bytes(ZERO,ZERO)).hexdigest()
def runtime():
 return {'requested_ctx':128,'actual_ctx':256,'pinned_ggml_pad':256,'n_batch':32,'n_ubatch':32,'tokens':list(range(16)),'dll_hashes':[format(i,'064x') for i in range(1,6)],'device_order':['Vulkan0','Vulkan1'],'cpu_vs_gpu_origins':{'cpu':'CPU_REFERENCE','gpu':'VULKAN_GPU_GRAPH'},'build_id':'declared_synthetic_only','exe_sha256':'1'*64,'requested_kv':256,'actual_kv':256,'child_f16_disabled':True,'fusion_disabled':True,'coopmat_disabled':True,'coopmat2_disabled':True}
def compare_one(cpu,gpu):
 left=list(ZERO);right=list(ZERO);left[0]=cpu;right[0]=gpu
 # Payload encoding is an API adapter. Error/RMSE are independent one-element analytic values.
 pin=hashlib.sha256(sl.canonical_payload_bytes(left,right)).hexdigest();error=abs(cpu-gpu)
 return sl.compare_logits(left,right,pin,error,error/math.sqrt(COUNT),COUNT)
class Tests(unittest.TestCase):
 def test_valid_zero_is_diagnostic_no_hardware_pass(self):
  out=sl.compare_logits(ZERO,ZERO,ZERO_SHA,0.0,0.0,COUNT)
  self.assertEqual(out['state'],'DIAGNOSTIC_ONLY');self.assertFalse(out['model_pass']);self.assertFalse(out['transport_corruption_proof'])
 def test_cpu_reference_threshold_rejects_001005(self):
  out=compare_one(0.0,0.01005)
  self.assertEqual(out['state'],'FAILED_NUMERIC');self.assertEqual(out['fail_count'],1)
 def test_cpu_reference_threshold_accepts_reverse_boundary(self):
  out=compare_one(0.01005,0.0)
  self.assertEqual(out['state'],'DIAGNOSTIC_ONLY');self.assertEqual(out['fail_count'],0)
 def test_float_count_refused(self):
  self.assertEqual(sl.compare_logits(ZERO,ZERO,ZERO_SHA,0.0,0.0,float(COUNT))['state'],'NOT_CHECKED')
 def test_float_context_refused(self):
  data=runtime();data['requested_ctx']=128.0;self.assertFalse(sl.validate_runtime_metadata(data))
 def test_float_model_bytes_refused(self):
  data={'model_key':'original_q8','sha256':'9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031','size':639446688.0,'quant':'q8_0','source_commit':'0faee5004297c3bcfa40b7bf11750127b8c1fd7d'}
  self.assertFalse(sl.validate_model_metadata(data))
 def test_records_cannot_mutate_prior_state(self):
  ledger=sl.StateLedger().append({'state':'FAILED_NUMERIC','experiment_id':'old'})
  try:ledger.records()[0]['state']='DIAGNOSTIC_ONLY'
  except TypeError:return
  self.assertEqual(ledger.records()[0]['state'],'FAILED_NUMERIC')
 def test_records_cannot_mutate_model_pass(self):
  ledger=sl.StateLedger().append({'state':'PENDING','experiment_id':'x'})
  try:ledger.records()[0]['model_pass']=True
  except TypeError:return
  self.assertFalse(json.loads(ledger.candidate_plan())['records'][0]['model_pass'])
 def test_input_nested_metadata_cannot_change_ledger(self):
  record={'state':'PENDING','experiment_id':'x','metadata':{'pins':['original']}}
  ledger=sl.StateLedger().append(record);record['metadata']['pins'][0]='forged'
  self.assertEqual(ledger.records()[0]['metadata']['pins'],['original'])
 def test_constructor_does_not_bypass_validation(self):
  with self.assertRaises(ValueError):sl.StateLedger(records=[{'state':'READY','experiment_id':'x','model_pass':True}])
 def test_terminal_cannot_restart_by_omitting_prior(self):
  ledger=sl.StateLedger().append({'state':'FAILED_NUMERIC','experiment_id':'x'})
  with self.assertRaises(ValueError):ledger.append({'state':'RUNNING','experiment_id':'x'})
 def test_terminal_cannot_restart_with_forged_prior(self):
  ledger=sl.StateLedger().append({'state':'FAILED_NUMERIC','experiment_id':'x'})
  with self.assertRaises(ValueError):ledger.append({'state':'RUNNING','experiment_id':'x','prior_state':'PENDING'})
 def test_anonymous_duplicate_dll_hashes_not_fresh_five(self):
  data=runtime();data['dll_hashes']=['0'*64]*5
  self.assertFalse(sl.validate_runtime_metadata(data))
 def test_huge_int_logit_refuses_without_exception(self):
  left=list(ZERO);left[0]=10**400
  out=sl.compare_logits(left,ZERO,'0'*64,0.0,0.0,COUNT)
  self.assertIn(out['state'],('NOT_CHECKED','FAILED_RUNTIME'))
 def test_huge_int_metric_refuses_without_exception(self):
  out=sl.compare_logits(ZERO,ZERO,ZERO_SHA,10**400,0.0,COUNT)
  self.assertEqual(out['state'],'NOT_CHECKED')
 def test_unhashable_model_key_refuses_without_exception(self):
  self.assertFalse(sl.validate_model_metadata({'model_key':[]}))
 def test_no_native_import_calls(self):self.assertEqual(TRAPS,[])
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=2).run(suite)
 pathlib.Path(__file__).with_name('actual_red_results.json').write_text(json.dumps({'scope':'SYNTHETIC_PURE_ONLY','tests':result.testsRun,'failures':[str(x[0]) for x in result.failures],'errors':[str(x[0]) for x in result.errors],'native_dependency_traps':TRAPS,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)
