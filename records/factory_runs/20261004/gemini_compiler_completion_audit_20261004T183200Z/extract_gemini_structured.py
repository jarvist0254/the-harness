from pathlib import Path
import json,hashlib
p=Path(r'E:\the_harness\records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z')
r=json.loads((p/'gemini_stdout_attempt2.json').read_text(encoding='utf-8'))
a=r.get('structured_output')
if not isinstance(a,dict) or set(a)!={'verdict','findings','safety_checks'}: raise SystemExit('strict structured output keys mismatch')
(p/'gemini_review_attempt2.pending_root_qa.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
raw=(p/'gemini_stdout_attempt2.json').read_bytes()
rec={'extraction':'agy structured_output field; response string also contains toolAction/toolSummary UI fields and was not selected','provider_status':r.get('status'),'provider_exit_code':0,'original_wrapper_status':'PARSE_OR_SCHEMA_ERROR','original_wrapper_parse_error':'PropertyNotFoundException because response string has extra toolAction/toolSummary keys','structured_output_keys':sorted(a),'verdict':a.get('verdict'),'findings_count':len(a.get('findings',[])),'safety_checks_count':len(a.get('safety_checks',[])),'num_turns':r.get('num_turns'),'usage':r.get('usage'),'tool_calls':'UNKNOWN','subagents':'UNKNOWN','stderr_warning':'--mode plan has no effect while slash command expansion is disabled','stdout_sha256':hashlib.sha256(raw).hexdigest().upper(),'review_sha256':hashlib.sha256((p/'gemini_review_attempt2.pending_root_qa.json').read_bytes()).hexdigest().upper()}
(p/'gemini_intake_reconciliation.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rec,ensure_ascii=False,indent=2))
