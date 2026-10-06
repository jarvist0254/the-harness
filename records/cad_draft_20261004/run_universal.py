import json
import sys

sys.path.insert(0, r'E:\the_harness\cad')
from integrated_core import build, default_config

result = build(default_config('universal'), r'E:\the_harness\records\cad_draft_20261004\universal_revision1')
print(json.dumps({'brep_valid': result['brep_valid'], 'solid_count': result['solid_count'],
                  'actual_bbox': result['actual_printed_bbox_mm'],
                  'interferences': result['body_interferences'],
                  'status': result['status']}), flush=True)
sys.exit(0 if not result['body_interferences'] else 2)
