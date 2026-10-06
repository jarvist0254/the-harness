import json,sys
sys.path.insert(0, 'E:\\the_harness\\cad')
from integrated_core import build,default_config
r=build(default_config('compact'),'E:\\the_harness\\records\\cad_draft_20261004\\compact_revision2')
print(json.dumps({"status":r["status"],"solid_count":r["solid_count"],"body_interferences":r["body_interferences"]}),flush=True)
