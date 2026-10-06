"""Independent synthetic controls against exact rejected directed-receipt source."""
import builtins,copy,hashlib,importlib.machinery,importlib.util,json,pathlib,sys,unittest
R=pathlib.Path(__file__).resolve().parent
SOURCE=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\qwen_directed_receipt\source.OVER_BUDGET_UNTRUSTED_REVIEW_ONLY.txt')
PIN='671c3706c5064aae55811020ec845402b1cfa010a224338ca78b42038261b56f'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==PIN
TRAPS=[];original=builtins.__import__
def guard(name,*args,**kw):
 if name.split('.')[0] in {'ctypes','_winapi','subprocess','multiprocessing','socket','pyopencl','numpy','torch','cupy'}:
  TRAPS.append(name);raise AssertionError('native/process/network/GPU dependency denied')
 return original(name,*args,**kw)
builtins.__import__=guard
loader=importlib.machinery.SourceFileLoader('actual_directed_receipt',str(SOURCE));spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)
def h(text):return hashlib.sha256(text.encode()).hexdigest()
def fixture():
 # Independently reconstructed small declarative fixture; no claimed real runtime.
 source={'vendor':'nvidia','uuid':'00000000-0000-0000-0000-000000000001','pci':'0000:01:00.0','allocation_id':h('nv-allocation'),'api':'CUDA_SYNTHETIC','path':'cuMemGetHandleForAddressRange','kind':'device'}
 target={'vendor':'intel','uuid':'00000000-0000-0000-0000-000000000002','pci':'0000:03:00.0','allocation_id':h('intel-allocation'),'api':'L0_SYNTHETIC','path':'ze_external_memory_import_fd','kind':'device'}
 artifacts={name:h(name) for name in ('source_executable','target_executable','build','payload','controller','baseline')}
 trusted={'schema':'p2p.trusted/v1','authorities':[{'id':h('root-authority'),'name':'root'}],'artifacts':copy.deepcopy(artifacts),'devices':[copy.deepcopy(source),copy.deepcopy(target)],'evaluation_unix':1000000,'max_staleness_seconds':300}
 receipt={'schema':'p2p.transfer.receipt/v1','direction':'nv_device_dmabuf_export_to_intel_imported_view','source':source,'target':target,'artifacts':artifacts,'sync':{'producer_event_hash':h('producer'),'consumer_event_hash':h('consumer')},'controls':{'cpu_staging':False,'host_pointer_equality_only':False,'clean_baseline_hash':artifacts['baseline'],'producer_corruption_before_copy_hash':h('corrupt')},'payload':{'bytes':4096,'baseline_hash':artifacts['baseline'],'consumer_result_hash':h('corrupt'),'parity_hash':h('corrupt')},'export':{'fd_hash':h('fd'),'backing_allocation_id':source['allocation_id'],'bytes':4096},'import':{'external_type':'ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF','imported_fd_hash':h('fd'),'allocation_id':target['allocation_id'],'bytes':4096},'residency':{'source_device_resident':True,'target_device_resident':True,'measurement_hash':h('self-reported-unregistered-measurement'),'timestamp_unix':1000000}}
 return receipt,trusted
OBSERVED={}
class Controls(unittest.TestCase):
 def evaluate(self,label,r,t):
  before=copy.deepcopy((r,t));o=m.validate(r,trusted=t);OBSERVED[label]=o;self.assertEqual((r,t),before);return o
 def test_consistent_but_untrusted_clean_baseline_must_refuse(self):
  r,t=fixture();r['payload']['baseline_hash']=r['controls']['clean_baseline_hash']=h('unrelated-clean-baseline')
  o=self.evaluate('baseline_unbound_to_trusted',r,t)
  self.assertNotEqual(o['status'],'EVIDENCE_CONSISTENT','matching receipt/control hashes do not match trusted baseline')
 def test_same_physical_uuid_and_pci_must_not_classify_peer(self):
  r,t=fixture();r['target']['uuid']=r['source']['uuid'];r['target']['pci']=r['source']['pci'];t['devices'][1]=copy.deepcopy(r['target'])
  o=self.evaluate('same_physical_identity',r,t)
  self.assertNotEqual(o['classification'],'DEVICE_P2P','different vendor labels cannot distinguish same physical identity')
 def test_unregistered_self_reported_residency_not_device_p2p(self):
  r,t=fixture();o=self.evaluate('unregistered_measurement',r,t)
  self.assertNotEqual(o['classification'],'DEVICE_P2P','boolean residency and arbitrary measurement hash are not bound to registry')
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 (R/'actual_results.json').write_text(json.dumps({'scope':'SYNTHETIC_PURE_ONLY','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'tests':result.testsRun,'failures':[str(x[0]) for x in result.failures],'errors':[str(x[0]) for x in result.errors],'observed':OBSERVED,'native_import_traps':TRAPS},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)
