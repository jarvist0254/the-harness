import hashlib,json,sys,pathlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'E:\the_harness\cad')
import FreeCAD as App
from integrated_core import build,default_config
root=pathlib.Path(r'E:\the_harness');source=root/'cad/integrated_core.py'
before=hashlib.sha256(source.read_bytes()).hexdigest()
r=build(default_config('universal'),str(root/'records/cad_draft_20261004'/'universal_revision3'))
old=App.openDocument(str(root/'records/cad_draft_20261004'/'universal_revision2'/'integrated_four_card_DRAFT.FCStd'))
new=App.openDocument(str(root/'records/cad_draft_20261004'/'universal_revision3'/'integrated_four_card_DRAFT.FCStd'))
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
(root/'records/cad_draft_20261004'/'universal_revision3'/'native_revision2_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['source_stable'] or not report['all_shapes_equivalent']:raise RuntimeError('Source changed or geometry differs')
print('REVISION3_VERIFIED '+json.dumps({'source_sha256':before,'solid_count':r['solid_count'],'brep_valid':r['brep_valid'],'actual_bbox':r['actual_printed_bbox_mm'],'body_interferences':r['body_interferences'],'all_shapes_equivalent':True}),flush=True)
