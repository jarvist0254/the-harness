import ast,hashlib,importlib.util,json,os,pathlib,sys,unittest
root=pathlib.Path(r'E:\the_harness');source=root/'records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z/grok_cad_bboxfix/integrated_core.grok_corrected.py';old=root/'cad/integrated_core.py';expected='78fd328ecde6067b517bd06368f82b61f3cbe5d73b42877fd643ea3de44ef415'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
assert hashlib.sha256(old.read_bytes()).hexdigest()=='326133a489430f5167bec29a87c28af8ea652e2fe40701d64c153399b85f372c'
tree=ast.parse(source.read_text());assert all(isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) or (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)) for n in tree.body)
assert all((isinstance(n,ast.Import) and all(a.name in {'copy','json','math'} for a in n.names)) or (isinstance(n,ast.ImportFrom) and n.module=='pathlib') for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
candidate=load('revision4_candidate',source);accepted=load('revision3_accepted',old)
def intersection(a,b):
 return max(0,min(a['origin_mm'][0]+a['size_mm'][0],b['origin_mm'][0]+b['size_mm'][0])-max(a['origin_mm'][0],b['origin_mm'][0]))*max(0,min(a['origin_mm'][1]+a['size_mm'][1],b['origin_mm'][1]+b['size_mm'][1])-max(a['origin_mm'][1],b['origin_mm'][1]))*max(0,min(a['origin_mm'][2]+a['size_mm'][2],b['origin_mm'][2]+b['size_mm'][2])-max(a['origin_mm'][2],b['origin_mm'][2]))
def shoes(p):
 d=p['dimensions'];out=[]
 for c in p['cards'][:3]:
  l=max(c['origin_mm'][0],-d['core_width_mm']/2);r=min(c['origin_mm'][0]+c['size_mm'][0],d['core_width_mm']/2)
  for y in (0,d['core_depth_mm']-d['rail_depth_mm']):out.append({'origin_mm':[l,y,d['base_mm']],'size_mm':[r-l,d['rail_depth_mm'],d['shoe_height_mm']]})
 return out
RESULT=[]
class IndependentCases(unittest.TestCase):
 def test_exact_poses_shoes_post_clearances_and_height(self):
  for profile,height in [('compact',150.0),('universal',199.0)]:
   p=candidate.plan_layout(candidate.default_config(profile));previous=accepted.plan_layout(accepted.default_config(profile));self.assertEqual(p['cards'],previous['cards']);self.assertEqual(p['gpu_bbox_mm'],previous['gpu_bbox_mm']);self.assertEqual(shoes(p),shoes(previous));self.assertEqual(p['printed_bbox_mm'],[188,200,height]);self.assertEqual(p['print_bbox_mm'],[200,188,height]);self.assertEqual(len(p['post_boxes']),4)
   for pb in p['post_boxes']:
    self.assertEqual(pb['size_mm'][2],height);self.assertEqual(pb['origin_mm'][2],0)
    for c in p['cards']:self.assertEqual(intersection(pb,c),0)
   clearances=[]
   for i in range(2):
    pb=p['post_boxes'][2*i];right=p['cards'][i]['origin_mm'][0]+p['cards'][i]['size_mm'][0];left=p['cards'][i+1]['origin_mm'][0];clearances.append([pb['origin_mm'][0]-right,left-(pb['origin_mm'][0]+pb['size_mm'][0])]);self.assertEqual(clearances[-1],[1,1])
   RESULT.append({'profile':profile,'GPU_poses_equal':True,'six_clipped_shoes_equal':True,'post_boxes':p['post_boxes'],'gap_side_clearance_mm':clearances,'printed_bbox_mm':p['printed_bbox_mm'],'all_16_post_body_box_intersection_volumes_mm3':[intersection(pb,c) for pb in p['post_boxes'] for c in p['cards']]})
 def test_old_invalid_dimension_gates_retained(self):
  for values in [{'rail_depth_mm':1},{'core_depth_mm':10},{'d_beam_height_mm':20},{'post_mm':12}]:
   c=candidate.default_config();c.update(values)
   with self.assertRaises(ValueError):candidate.plan_layout(c)
  c=candidate.default_config();c['cards'][3]['length_mm']=100
  with self.assertRaises(ValueError):candidate.plan_layout(c)
 def test_unclipped_oversize_rejected(self):
  c=candidate.default_config();c['cards'][0]['height_mm']=250
  with self.assertRaises(ValueError):candidate.plan_layout(c)
 def test_unknown_interfaces_and_draft_labels_retained(self):
  for profile in ['compact','universal']:
   p=candidate.plan_layout(candidate.default_config(profile));self.assertFalse(p['production_release']);self.assertFalse(p['measured_interfaces']);self.assertIn('loads',p['unknown_interfaces']);self.assertIn('NO_PRODUCTION_STL',p['claims'])
os.environ['CANDIDATE_PATH']=str(source);provider=load('revision4_provider_tests',source.parent/'tests.candidate.py')
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(IndependentCases),unittest.defaultTestLoader.loadTestsFromModule(provider)]);r=unittest.TextTestRunner(verbosity=2).run(suite)
(root/'records/cad_draft_20261004/revision4_pure_gate.json').write_text(json.dumps({'source_sha256':expected,'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'profiles':RESULT,'AST_top_level_stdlib_definitions_only':True,'accepted_source_sha256_after':hashlib.sha256(old.read_bytes()).hexdigest()},indent=2)+'\n');sys.exit(0 if r.wasSuccessful() else 1)
