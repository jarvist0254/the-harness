import datetime,hashlib,json,pathlib,subprocess,sys,time
root=pathlib.Path(r'E:\the_harness');base=root/'records/cad_draft_20261004'
exe=pathlib.Path(r'E:\tooling\FreeCAD\app\FreeCAD_1.1.4-Windows-x86_64-py311\bin\freecadcmd.exe')
source=root/'cad/integrated_core.py';sha=hashlib.sha256(source.read_bytes()).hexdigest()
flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
runs=[]
def run(cmd,stem,timeout=60):
 start=time.monotonic();p=subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);timed=False
 try:o,e=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:p.kill();o,e=p.communicate(timeout=5);timed=True
 (base/(stem+'.stdout.log')).write_bytes(o);(base/(stem+'.stderr.log')).write_bytes(e)
 check=subprocess.run(['tasklist','/FI','PID eq '+str(p.pid),'/FO','CSV','/NH'],capture_output=True,timeout=10,creationflags=flags)
 return {'command':cmd,'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'seconds':time.monotonic()-start,'stdout':o.decode('utf-8','replace'),'stderr':e.decode('utf-8','replace'),'process_reaped':p.poll() is not None,'tasklist_after':check.stdout.decode('utf-8','replace')}
tests=run([sys.executable,'-B','-m','unittest','discover','-s','cad/tests','-v'],'revision3_tests')
for profile in ('compact','universal'):
 out=base/(profile+'_revision3')
 if out.exists():raise FileExistsError(out)
 wrapper=base/('run_'+profile+'_revision3.py')
 if wrapper.exists():raise FileExistsError(wrapper)
 text="""import hashlib,json,sys,pathlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'E:\\the_harness\\cad')
import FreeCAD as App
from integrated_core import build,default_config
root=pathlib.Path(r'E:\\the_harness');source=root/'cad/integrated_core.py'
before=hashlib.sha256(source.read_bytes()).hexdigest()
r=build(default_config(PROFILE),str(root/'records/cad_draft_20261004'/OUT))
old=App.openDocument(str(root/'records/cad_draft_20261004'/OLD/'integrated_four_card_DRAFT.FCStd'))
new=App.openDocument(str(root/'records/cad_draft_20261004'/OUT/'integrated_four_card_DRAFT.FCStd'))
comparisons=[]
try:
 old_objects={x.Name:x for x in old.Objects if hasattr(x,'Shape')}
 new_objects={x.Name:x for x in new.Objects if hasattr(x,'Shape')}
 if set(old_objects)!=set(new_objects):raise RuntimeError('Shape object name sets differ')
 for name in sorted(old_objects):
  a,b=old_objects[name].Shape,new_objects[name].Shape
  differences=[a.cut(b).Volume,b.cut(a).Volume]
  boxes=[[v.BoundBox.XMin,v.BoundBox.XMax,v.BoundBox.YMin,v.BoundBox.YMax,v.BoundBox.ZMin,v.BoundBox.ZMax] for v in (a,b)]
  same=all(abs(x)<=1e-6 for x in differences) and all(abs(x-y)<=1e-6 for x,y in zip(*boxes))
  comparisons.append({'object':name,'old_minus_new_volume_mm3':differences[0],'new_minus_old_volume_mm3':differences[1],'old_new_bounds_mm':boxes,'equivalent_within_1e_6':same})
finally:
 App.closeDocument(old.Name);App.closeDocument(new.Name)
report={'source_sha256_before':before,'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),'source_stable':before==hashlib.sha256(source.read_bytes()).hexdigest(),'object_geometry_equivalence':comparisons,'all_shapes_equivalent':all(x['equivalent_within_1e_6'] for x in comparisons),'state':r}
(root/'records/cad_draft_20261004'/OUT/'native_revision2_comparison.json').write_text(json.dumps(report,indent=2)+'\\n')
if not report['source_stable'] or not report['all_shapes_equivalent']:raise RuntimeError('Source changed or geometry differs')
print('REVISION3_VERIFIED '+json.dumps({'source_sha256':before,'solid_count':r['solid_count'],'brep_valid':r['brep_valid'],'actual_bbox':r['actual_printed_bbox_mm'],'body_interferences':r['body_interferences'],'all_shapes_equivalent':True}),flush=True)
""".replace('PROFILE',repr(profile)).replace('OUT',repr(profile+'_revision3')).replace('OLD',repr(profile+'_revision2'))
 wrapper.write_text(text,encoding='utf-8')
 result=run([str(exe),str(wrapper)],profile+'_revision3');statefile=out/'state.json';comparisonfile=out/'native_revision2_comparison.json'
 result.update({'case':profile,'source_sha256':sha,'state_fresh_present':statefile.is_file(),'comparison_fresh_present':comparisonfile.is_file(),'verified_marker': 'REVISION3_VERIFIED ' in result['stdout'],'exception_text_absent':not any(x in result['stdout']+result['stderr'] for x in ['Traceback','Exception while processing','RuntimeError:'])})
 if statefile.exists():result['state']=json.loads(statefile.read_text())
 if comparisonfile.exists():result['comparison']=json.loads(comparisonfile.read_text())
 result['execution_verified']=result['exit_code']==0 and not result['timed_out'] and result['state_fresh_present'] and result['comparison_fresh_present'] and result['verified_marker'] and result['exception_text_absent']
 result['acceptance_status']=('VALID_DRAFT_BREP_NOT_FIT_QUALIFICATION' if not result.get('state',{}).get('body_interferences') else 'REFUSED_BODY_INTERFERENCE') if result['execution_verified'] else 'FAILED_VERIFICATION'
 runs.append(result)
receipt={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha,'source_sha256_after_all_runs':hashlib.sha256(source.read_bytes()).hexdigest(),'test_run':tests,'native_runs':runs,'qualification':'DRAFT ONLY. Nominal body overlap checks do not certify safe contacts, strength, mass, receiver/PSU/cable/airflow interfaces or production fit.'}
(base/'native_build_revision3_runs.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'receipt':str(base/'native_build_revision3_runs.json'),'tests_exit':tests['exit_code'],'native':[{k:x[k] for k in ('case','pid','execution_verified','acceptance_status','process_reaped')} for x in runs]}))
if tests['exit_code'] or not all(x['execution_verified'] for x in runs):sys.exit(1)
