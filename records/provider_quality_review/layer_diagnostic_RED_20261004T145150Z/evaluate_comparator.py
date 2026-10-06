"""Independent actual-source comparator RED: synthetic bytes only, native blocked."""
import pathlib,sys,os,json,hashlib,ast,importlib.util,struct,tempfile,unittest,copy,subprocess,ctypes,_winapi,socket
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=ROOT/'records/factory_runs/20261004/layer_diagnostic_20261004T144323Z/qwen_capture_comparator/capture_comparator.py'
EXPECTED_SHA='56a55d66798f476cc0cd39d0fd21942b046d24e13985e76af41ecf85ca9de1da'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA
assert 'RUN_CONTAINMENT_FIXTURES' not in os.environ
FORBIDDEN=[];OBS=[];OUTCOMES=[]
def deny(label):
 def f(*a,**k):FORBIDDEN.append(label);raise AssertionError('FORBIDDEN '+label)
 return f
for name in dir(_winapi):
 if callable(getattr(_winapi,name)):setattr(_winapi,name,deny('_winapi.'+name))
for name in ['Popen','run','call','check_call','check_output','getoutput','getstatusoutput']:setattr(subprocess,name,deny('subprocess.'+name))
for name in ['system','startfile','fork','forkpty','posix_spawn','posix_spawnp','spawnl','spawnle','spawnlp','spawnlpe','spawnv','spawnve','spawnvp','spawnvpe','execl','execle','execlp','execlpe','execv','execve','execvp','execvpe']:
 if hasattr(os,name):setattr(os,name,deny('os.'+name))
for name in ['WinDLL','CDLL','OleDLL','PyDLL','LoadLibrary']:
 if hasattr(ctypes,name):setattr(ctypes,name,deny('ctypes.'+name))
class NoDLL:
 def __getattr__(self,name):return deny('DLL.'+name)
ctypes.windll=NoDLL();ctypes.cdll=NoDLL();ctypes.oledll=NoDLL();ctypes.pydll=NoDLL()
socket.socket=deny('socket.socket');socket.create_connection=deny('socket.create_connection');socket.getaddrinfo=deny('socket.getaddrinfo')
class DenyImports:
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','numpy','cupy','pyopencl','vulkan','tensorflow','jax','requests','aiohttp','urllib','http'}:FORBIDDEN.append('import.'+fullname);raise AssertionError('FORBIDDEN_IMPORT '+fullname)
sys.meta_path.insert(0,DenyImports())
tree=ast.parse(SOURCE.read_bytes());allowed={'json','hashlib','math','os','struct','typing'}
for n in tree.body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):assert all(x.split('.')[0] in allowed for x in ([n.module] if isinstance(n,ast.ImportFrom) else [a.name for a in n.names]))
 else:
  assert isinstance(n,(ast.ClassDef,ast.FunctionDef));assert not n.decorator_list
  if isinstance(n,ast.ClassDef):assert all(isinstance(x,(ast.Pass,ast.FunctionDef)) for x in n.body)
  else:assert all(isinstance(x,ast.Constant) for x in n.args.defaults+n.args.kw_defaults if x is not None)
sp=importlib.util.spec_from_file_location('actual_comparator_RED',SOURCE);c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
helper=ROOT/'records/provider_quality_review/layer_diagnostic_root_20261004T144825Z/independent_fixtures.py'
sp=importlib.util.spec_from_file_location('independent_synthetic_fixtures',helper);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
def snapshot(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
class Cases(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=HERE);self.folder=pathlib.Path(self.temp.name);self.cpu,self.gpu,self.expected=h.fixture_pair(self.folder);self.cm=self.load(self.cpu);self.gm=self.load(self.gpu)
 def tearDown(self):self.temp.cleanup()
 def load(self,p):return json.loads((p/'manifest.json').read_text())
 def save(self):
  for p,m in [(self.cpu,self.cm),(self.gpu,self.gm)]:(p/'manifest.json').write_text(json.dumps(m))
 def replace_bytes(self,p,m,index,values):
  data=struct.pack('<'+str(len(values))+'f',*values);node=m['captures'][index];(p/node['file']).write_bytes(data);node['sha256']=h.digest(data)
 def call(self,**kw):
  before=snapshot(self.folder);error=None;result=None
  try:result=c.compare_artifacts(str(self.cpu),str(self.gpu),expected=self.expected,**kw)
  except c.CaptureError as e:error={'type':'CaptureError','message':str(e)}
  except Exception as e:error={'type':type(e).__name__,'message':str(e)}
  after=snapshot(self.folder);OBS.append({'case':self.id(),'result':result,'error':error,'input_unchanged':before==after,'source_sha256':EXPECTED_SHA,'scope':'Synthetic byte files; metadata pins are caller declarations, not native authenticity'})
  self.assertEqual(before,after,'Comparator must not write input artifacts');return result,error
 def refuse(self,**kw):
  r,e=self.call(**kw);self.assertTrue(e and e['type']=='CaptureError' or isinstance(r,dict) and r.get('result')=='NOT_CHECKED','Malformed artifact must refuse, not label numeric divergence/match: '+str((r,e)))
 def test_equal_baseline(self):
  r,e=self.call();self.assertIsNone(e);self.assertEqual(r['result'],'DIAGNOSTIC_MATCH');self.assertEqual(r['comparator'],'COMPARATOR_ONLY')
 def test_updated_hash_real_corruption_first_observed(self):
  self.replace_bytes(self.gpu,self.gm,1,[1.,1000000.,-2.,3.,4.,5.,6.,7.]);self.replace_bytes(self.gpu,self.gm,2,[2.,1000000.,-2.,3.,4.,5.,6.,7.]);self.save();r,e=self.call();self.assertIsNone(e);self.assertEqual(r['result'],'DIAGNOSTIC_DIVERGENCE');self.assertEqual(r['first_divergent_ordinal'],1);self.assertAlmostEqual(r['stats']['max_abs'],1);self.assertEqual(r['stats']['failed_count'],1)
 def test_global_scale_false_match(self):
  self.replace_bytes(self.gpu,self.gm,0,[.02,1000000.,-2.,3.,4.,5.,6.,7.]);self.save();r,e=self.call();self.assertIsNone(e);self.assertEqual(r['result'],'DIAGNOSTIC_DIVERGENCE')
 def test_small_noise_reported_for_every_capture(self):
  self.replace_bytes(self.gpu,self.gm,0,[.001,1000000.,-2.,3.,4.,5.,6.,7.]);self.save();r,e=self.call();self.assertIsNone(e);self.assertEqual(r['result'],'DIAGNOSTIC_MATCH');self.assertTrue(any(isinstance(v,list) and len(v)==3 for v in r.values()),'Every observed capture needs statistics even when within tolerance')
 def test_metadata_shape_mismatch(self):
  self.gm['captures'][0]['dims']=[4,2,1,1];self.gm['captures'][0]['strides']=[4,16,32,32];self.save();self.refuse()
 def test_metadata_op_mismatch(self):self.gm['captures'][0]['op']='OTHER_OP';self.save();self.refuse()
 def test_missing_nodes(self):self.gm['captures'].pop();self.save();self.refuse()
 def test_extra_nodes(self):
  node=copy.deepcopy(self.gm['captures'][-1]);node.update(name='result_norm',ordinal=3);self.gm['captures'].append(node);self.save();self.refuse()
 def test_order_difference(self):
  self.gm['captures'][0],self.gm['captures'][1]=self.gm['captures'][1],self.gm['captures'][0]
  for i,n in enumerate(self.gm['captures']):n['ordinal']=i
  self.save();self.refuse()
 def test_duplicate_name(self):self.gm['captures'][1]['name']=self.gm['captures'][0]['name'];self.save();self.refuse()
 def test_canonical_alias(self):self.cm['captures'][0]['name']='attn_norm-00';self.gm['captures'][0]['name']='attn_norm-00';self.save();self.refuse()
 def test_nested_duplicate_json_key(self):
  raw=(self.gpu/'manifest.json').read_text().replace('"source_sha256":','"source_sha256":"'+self.expected['source_sha256']+'","source_sha256":',1);(self.gpu/'manifest.json').write_text(raw);self.refuse()
 def test_actual_hash_mismatch(self):
  path=self.gpu/self.gm['captures'][0]['file'];raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:]);self.refuse()
 def test_truncated_with_true_hash(self):
  n=self.gm['captures'][0];path=self.gpu/n['file'];raw=path.read_bytes()[:-4];path.write_bytes(raw);n['sha256']=h.digest(raw);self.save();self.refuse()
 def test_trailing_with_true_hash(self):
  n=self.gm['captures'][0];path=self.gpu/n['file'];raw=path.read_bytes()+b'\0'*4;path.write_bytes(raw);n['sha256']=h.digest(raw);self.save();self.refuse()
 def test_missing_expected_authority(self):self.expected={};self.refuse()
 def test_tokens_both_short(self):self.cm['origin']['tokens']=[0,1];self.gm['origin']['tokens']=[0,1];self.save();self.refuse()
 def test_tokens_different_passes(self):self.gm['origin']['tokens']=list(reversed(range(16)));self.save();self.refuse()
 def test_authority_extra(self):self.gm['origin']['qualification']='GPU_PASS';self.save();self.refuse()
 def test_manifest_extra(self):self.gm['production_pass']=True;self.save();self.refuse()
 def test_node_extra(self):self.gm['captures'][0]['reference_scale']=1000000;self.save();self.refuse()
 def test_manifest_budget(self):
  path=self.gpu/'manifest.json';path.write_text(path.read_text()+' '*131073);self.refuse()
 def test_aggregate_actual_file_budget(self):
  raw=b'\0'*(1<<20);path=self.cpu/'shared.bin'
  with path.open('wb') as f:
   for _ in range(16):f.write(raw)
  digest=hashlib.sha256()
  with path.open('rb') as f:
   for chunk in iter(lambda:f.read(1<<20),b''):digest.update(chunk)
  nodes=[]
  for i in range(5):nodes.append({'ordinal':i,'name':'attn_norm-'+str(i),'op':'NORM','dtype':'F32_LE','dims':[4194304,1,1,1],'strides':[4,16777216,16777216,16777216],'nbytes':16777216,'sha256':digest.hexdigest(),'file':'shared.bin'})
  self.cm['captures']=nodes;self.save();self.refuse()
 def test_symlink_root_inside_owned_folder(self):
  link=self.folder/'gpu_alias'
  try:os.symlink(self.gpu,link,target_is_directory=True)
  except OSError as e:self.skipTest('NOT_CHECKED symlink creation unavailable: '+str(e))
  self.gpu=link;self.refuse()
 def test_symlink_file_inside_owned_folder(self):
  original=self.gpu/self.gm['captures'][0]['file'];target=self.folder/'inside_owned_external.bin';target.write_bytes(original.read_bytes());original.unlink()
  try:os.symlink(target,original)
  except OSError as e:self.skipTest('NOT_CHECKED symlink creation unavailable: '+str(e))
  self.refuse()
def mutation_case(section,key,value,both=False):
 def test(self):
  for m in ([self.cm,self.gm] if both else [self.gm]):
   target=m if section=='manifest' else m['origin'] if section=='origin' else m['captures'][0];target[key]=value
  self.save();self.refuse()
 return test
mutations=[('manifest','schema','UNKNOWN'),('manifest','status','READY'),('manifest','diagnostic_intrusive',False),('manifest','qualification','GPU_PASS'),('origin','pinned_commit','a'*40),('origin','source_sha256','a'*64),('origin','executable_sha256','b'*64),('origin','workload_sha256','c'*64),('origin','model_sha256','d'*64),('origin','model_bytes',639446688.0),('origin','n_ctx_actual',256.0),('origin','role','CPU_REFERENCE'),('origin','devices',['Vulkan1','Vulkan0']),('origin','devices',['Vulkan0','Vulkan0']),('origin','vulkan_disable_f16',False),('origin','flash_attention',True),('node','ordinal',0.0),('node','ordinal',False),('node','dims',[True,8,1,1]),('node','strides',[4.0,32.0,32.0,32.0]),('node','nbytes',32.0),('node','dtype','F32_BE'),('node','file','../escape.bin'),('node','file','C:\\outside.bin'),('node','file','node.bin:ads')]
for section,key,value in mutations:setattr(Cases,'test_mutation_'+section+'_'+key+('_'+str(value)[:18].replace(' ','_') if key in ['devices','ordinal','file'] else ''),mutation_case(section,key,value))
def nonfinite_case(value,side):
 def test(self):
  self.replace_bytes(self.cpu if side=='cpu' else self.gpu,self.cm if side=='cpu' else self.gm,0,[value,1000000.,-2.,3.,4.,5.,6.,7.]);self.save();self.refuse()
 return test
for value,name in [(float('nan'),'nan'),(float('inf'),'inf'),(-float('inf'),'minus_inf')]:
 for side in ['cpu','gpu']:setattr(Cases,'test_nonfinite_'+side+'_'+name,nonfinite_case(value,side))
def tolerance_case(value):
 def test(self):self.refuse(atol=value,rtol=value)
 return test
for value,name in [(True,'bool'),(-1,'negative'),(float('nan'),'nan'),(float('inf'),'inf'),(.02,'widened'),(0,'narrowed')]:setattr(Cases,'test_tolerance_'+name,tolerance_case(value))
class Capture(unittest.TextTestResult):
 def addFailure(self,test,err):super().addFailure(test,err);OUTCOMES.append({'case':test.id(),'outcome':'FAIL','trace':self._exc_info_to_string(err,test)})
 def addError(self,test,err):super().addError(test,err);OUTCOMES.append({'case':test.id(),'outcome':'ERROR','trace':self._exc_info_to_string(err,test)})
 def addSuccess(self,test):super().addSuccess(test);OUTCOMES.append({'case':test.id(),'outcome':'PASS'})
 def addSkip(self,test,reason):super().addSkip(test,reason);OUTCOMES.append({'case':test.id(),'outcome':'NOT_CHECKED','reason':reason})
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2,resultclass=Capture).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases));assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA
 payload={'scope':'SYNTHETIC_COMPARATOR_ONLY_NOT_GPU_OR_MODEL_QUALIFICATION','source':str(SOURCE),'source_sha256':EXPECTED_SHA,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'not_checked':len(result.skipped),'forbidden_calls':FORBIDDEN,'outcomes':OUTCOMES,'observations':OBS,'adapter':'Actual Qwen result key result, first_divergent_ordinal, stats; malformed artifacts must CaptureError or resultNOT_CHECKED, not numeric divergence. Output root/file writes remain external caller responsibility.','limits':['Metadata pin matching does not authenticate execution or original model.','144-node cap cannot get otherwise-valid145names under142canonical-name whitelist.','Synthetic fixture storage maximumabout16MiB, no candidate16MiBfullfloatcomparison.','No provider-generated tests executed.']}
 (HERE/'RED_results.json').write_text(json.dumps(payload,indent=2));print(json.dumps({k:v for k,v in payload.items() if k not in ('outcomes','observations')},indent=2));sys.exit(0 if result.wasSuccessful() and not FORBIDDEN else 1)
