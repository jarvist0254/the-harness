import pathlib,subprocess,time,json,hashlib,sys
root=pathlib.Path(r'E:\the_harness');base=root/'records/cad_draft_20261004';candidate=root/'records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z/grok_cad_bboxfix/integrated_core.grok_corrected.py';sha='78fd328ecde6067b517bd06368f82b61f3cbe5d73b42877fd643ea3de44ef415';exe=r'E:\tooling\FreeCAD\app\FreeCAD_1.1.4-Windows-x86_64-py311\bin\freecadcmd.exe'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==sha
assert json.loads((base/'revision4_pure_gate.json').read_text())['failures']==0
runs=[]
for profile,height in [('compact',150),('universal',199)]:
 folder=base/(profile+'_revision4');assert not folder.exists();wrapper=base/('run_'+profile+'_revision4.py');assert not wrapper.exists()
 code=r"""import pathlib,json,hashlib,importlib.util,sys
sys.dont_write_bytecode=True
import FreeCAD as App
import Part
root=pathlib.Path(r'E:\the_harness');source=root/'records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z/grok_cad_bboxfix/integrated_core.grok_corrected.py';expected='78fd328ecde6067b517bd06368f82b61f3cbe5d73b42877fd643ea3de44ef415';before=hashlib.sha256(source.read_bytes()).hexdigest();assert before==expected
spec=importlib.util.spec_from_file_location('candidate',source);candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
folder=root/'records/cad_draft_20261004'/FOLDER
made=[];original=Part.makeBox
def capture(*args,**kwargs):
 shape=original(*args,**kwargs);v=args[3];made.append({'size_mm':list(args[:3]),'origin_mm':[v.x,v.y,v.z],'shape':shape});return shape
Part.makeBox=capture
try:state=candidate.build(candidate.default_config(PROFILE),str(folder))
finally:Part.makeBox=original
assert len(made)==22,'Unexpected primitive allocation order/count'
assert state['solid_count']==1 and state['brep_valid']
assert state['actual_printed_bbox_mm']==[188.0,200.0,HEIGHT]
assert not state['body_interferences']
posts=made[4:8];shoes=made[8:14];cards=made[18:22];metals=[made[15],made[17]]
postvols=[{'post':i,'bay':chr(65+j),'volume_mm3':p['shape'].common(c['shape']).Volume} for i,p in enumerate(posts) for j,c in enumerate(cards)]
metalvols=[{'rail':i,'bay':chr(65+j),'volume_mm3':p['shape'].common(c['shape']).Volume} for i,p in enumerate(metals) for j,c in enumerate(cards)]
assert all(abs(x['volume_mm3'])<=1e-6 for x in postvols+metalvols)
old=App.openDocument(str(root/'records/cad_draft_20261004'/OLD/'integrated_four_card_DRAFT.FCStd'))
new=App.openDocument(str(folder/'integrated_four_card_DRAFT.FCStd'))
comparison=[]
try:
 core=new.getObject('IntegratedPrintedCore_DRAFT').Shape
 corevols=[{'bay':chr(65+j),'volume_mm3':core.common(c['shape']).Volume} for j,c in enumerate(cards)]
 assert all(abs(x['volume_mm3'])<=1e-6 for x in corevols)
 for name in ['GPU_A_Envelope','GPU_B_Envelope','GPU_C_Envelope','GPU_D_Envelope','MetalDLoadRailConcept_0','MetalDLoadRailConcept_1']:
  a,b=old.getObject(name).Shape,new.getObject(name).Shape;diff=[a.cut(b).Volume,b.cut(a).Volume];ab=[a.BoundBox.XMin,a.BoundBox.XMax,a.BoundBox.YMin,a.BoundBox.YMax,a.BoundBox.ZMin,a.BoundBox.ZMax];bb=[b.BoundBox.XMin,b.BoundBox.XMax,b.BoundBox.YMin,b.BoundBox.YMax,b.BoundBox.ZMin,b.BoundBox.ZMax];equal=all(abs(x)<=1e-6 for x in diff) and all(abs(x-y)<=1e-6 for x,y in zip(ab,bb));assert equal
  comparison.append({'name':name,'old_minus_new_mm3':diff[0],'new_minus_old_mm3':diff[1],'bounds_equal':True})
finally:App.closeDocument(old.Name);App.closeDocument(new.Name)
oldstate=json.loads((root/'records/cad_draft_20261004'/OLD/'state.json').read_text());expected_shoes=[];d=oldstate['dimensions']
for c in oldstate['cards'][:3]:
 left=max(c['origin_mm'][0],-d['core_width_mm']/2);right=min(c['origin_mm'][0]+c['size_mm'][0],d['core_width_mm']/2)
 for y in [0,d['core_depth_mm']-d['rail_depth_mm']]:expected_shoes.append({'size_mm':[right-left,d['rail_depth_mm'],d['shoe_height_mm']],'origin_mm':[left,y,d['base_mm']]})
actual_shoes=[{k:x[k] for k in ['size_mm','origin_mm']} for x in shoes];assert expected_shoes==actual_shoes
receipt={'source_sha256_before':before,'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),'all_native_post_card_intersections':postvols,'all_native_metal_card_intersections':metalvols,'all_native_core_card_intersections':corevols,'six_actual_shoe_primitives_equal_revision3':True,'actual_shoes':actual_shoes,'GPU_and_metal_saved_BRep_equivalence_revision3':comparison,'state':state,'all_22_actual_Primitives':[{k:x[k] for k in ['size_mm','origin_mm']} for x in made]}
assert receipt['source_sha256_after']==before
(folder/'native_gate.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('REVISION4_NATIVE_VERIFIED '+json.dumps({'source_sha256':before,'one_valid_solid':True,'actual_bbox_mm':state['actual_printed_bbox_mm'],'core_volume_mm3':state['core_volume_mm3'],'post_card_intersection_count':16,'post_card_intersection_max_mm3':max(x['volume_mm3'] for x in postvols),'all_core_and_metal_body_intersections_mm3':0,'GPU_poses_equal_revision3':True,'shoes_equal_revision3':True}),flush=True)
""".replace('FOLDER',repr(profile+'_revision4')).replace('PROFILE',repr(profile)).replace('HEIGHT',repr(float(height))).replace('OLD',repr(profile+'_revision3'))
 wrapper.write_text(code,encoding='utf-8');cmd=[exe,str(wrapper)];start=time.monotonic();p=subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 try:o,e=p.communicate(timeout=60);timed=False
 except subprocess.TimeoutExpired:p.kill();o,e=p.communicate(timeout=5);timed=True
 (base/(profile+'_revision4.stdout.log')).write_bytes(o);(base/(profile+'_revision4.stderr.log')).write_bytes(e)
 statefile=folder/'state.json';gatefile=folder/'native_gate.json';marker='REVISION4_NATIVE_VERIFIED ' in o.decode('utf-8','replace');exception=any(t in (o+e).decode('utf-8','replace') for t in ['Traceback','Exception while processing','AssertionError','RuntimeError:'])
 q=subprocess.run(['tasklist','/FI','PID eq '+str(p.pid),'/FO','CSV','/NH'],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
 result={'profile':profile,'command':cmd,'pid':p.pid,'exit':p.returncode,'timed_out':timed,'seconds':time.monotonic()-start,'fresh_state_exists':statefile.exists(),'fresh_gate_exists':gatefile.exists(),'marker':marker,'exception_absent':not exception,'tasklist_after':q.stdout.decode('utf-8','replace'),'accepted':p.returncode==0 and not timed and statefile.exists() and gatefile.exists() and marker and not exception}
 if gatefile.exists():result['native_gate']=json.loads(gatefile.read_text())
 runs.append(result);print(json.dumps({k:v for k,v in result.items() if k!='native_gate'}),flush=True)
receipt={'candidate_sha256':sha,'accepted_CAD_source_sha256_after':hashlib.sha256((root/'cad/integrated_core.py').read_bytes()).hexdigest(),'runs':runs,'status':'PASS_DRAFT_BREP_BODY_CLEAR_ONLY' if all(x['accepted'] for x in runs) else 'FAILED_GATE','qualification':'No safe contacts, loads, slicer/print release or production interfaces qualified; no STL exported.'};(base/'native_build_revision4_runs.json').write_text(json.dumps(receipt,indent=2)+'\n');sys.exit(0 if all(x['accepted'] for x in runs) else 1)
