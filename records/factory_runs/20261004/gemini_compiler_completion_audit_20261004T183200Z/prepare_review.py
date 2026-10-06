from pathlib import Path
import hashlib, json
base = Path(r'E:\the_harness')
out = base / r'records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z'
inputs = {
    'candidate': base / r'records\root_continuation_20261004\compiler_adapter_local_fallback_20261004T182833Z\compiler_completion_adapter.py',
    'spec': base / r'records\root_continuation_20261004\COMPILER_COMPLETION_TASK_SPEC.md',
    'supervisor': base / r'records\root_continuation_20261004\contained_build_policy_20261004T160430Z\contained_build_supervisor.py',
    'native_driver': base / r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py',
    'attempt5_controller': base / r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\controller_compiler_completion_attempt5.py',
    'driver_tests': base / r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\test_driver_acceptance_pure.py',
    'postquery_tests': base / r'records\root_continuation_20261004\compiler_adapter_independent_20261004T1818Z\test_post_query_guards.py',
    'more_contract_tests': base / r'records\root_continuation_20261004\compiler_adapter_independent_20261004T1818Z\test_more_contract.py',
    'pure_green_log': base / r'records\root_continuation_20261004\compiler_adapter_independent_20261004T1818Z\fallback_22_GREEN.log',
    'muse_review': base / r'records\factory_runs\20261004\muse_adversarial_20261004T172000Z\compiler_completion_audit\run_output\parsed_review.json',
    'muse_reconciliation': base / r'records\factory_runs\20261004\muse_adversarial_20261004T172000Z\compiler_completion_audit\run_output\parser_reconciliation.json',
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
source_lines = inputs['supervisor'].read_text(encoding='utf-8').splitlines()
def func(name):
    start = next(i for i,line in enumerate(source_lines) if line.startswith(f'def {name}('))
    end = next((i for i in range(start+1,len(source_lines)) if source_lines[i].startswith('def ') or source_lines[i].startswith('class ')), len(source_lines))
    return '\n'.join(f'{i+1}: {source_lines[i]}' for i in range(start,end))
blocks = 'PINNED SUPERVISOR _shutdown and run_workers EXCERPTS WITH FILE LINE NUMBERS\n\n'+func('_shutdown')+'\n\n'+func('run_workers')
(out/'supervisor_critical_excerpt.txt').write_text(blocks,encoding='utf-8')
views = {}
for key,path in inputs.items():
    dest = out / f'{key}.snapshot{path.suffix}'
    dest.write_bytes(path.read_bytes())
    views[key] = {'original':str(path),'snapshot':str(dest),'sha256':sha(path),'bytes':path.stat().st_size}
views['supervisor_critical_excerpt']={'path':str(out/'supervisor_critical_excerpt.txt'),'sha256':sha(out/'supervisor_critical_excerpt.txt'),'bytes':(out/'supervisor_critical_excerpt.txt').stat().st_size}
(out/'inputs.json').write_text(json.dumps(views,indent=2),encoding='utf-8')
spec=inputs['spec'].read_text(encoding='utf-8')
candidate=inputs['candidate'].read_text(encoding='utf-8')
critical=(out/'supervisor_critical_excerpt.txt').read_text(encoding='utf-8')
review=json.loads(inputs['muse_review'].read_text(encoding='utf-8'))
checks='\n'.join(f'- {i+1}. {x}' for i,x in enumerate(review.get('findings',[])))
# Each finding is rendered without transformation except JSON encoding for unambiguous text.
findings=json.dumps(review.get('findings',[]),ensure_ascii=False,indent=2)
prompt=f'''You are Gemini doing an independent, source-only correctness review for a bounded compiler-completion adapter. Review the actual candidate below against the exact specification and actual caller gates. Do not execute code, use tools, read other files, modify files, launch jobs, or make provider calls. All relevant source and evidence are embedded here.

Candidate SHA256: {views['candidate']['sha256']}
ROOT task spec SHA256: {views['spec']['sha256']}
Pinned supervisor SHA256: {views['supervisor']['sha256']}
Actual caller native_driver SHA256: {views['native_driver']['sha256']}
Actual attempt-5 build controller SHA256: {views['attempt5_controller']['sha256']}

Review tasks:
1. Independently audit the candidate hook and its limits against the spec, especially wait/exit semantics, boundary checks, event/deadline races, unsupported worker/policy configurations, exceptions, and import/install side effects.
2. Independently trace the actual caller acceptance path. Determine whether a custom hook status can be accepted if `_shutdown` or log/handle cleanup is uncertain. Distinguish a status-label concern from an actual false-accept path. Cite exact lines from the embedded supervisor excerpts and native driver/controller.
3. Assess the actual Muse findings below, which came from a different earlier Qwen candidate, against this local fallback and the caller gates. For each finding either confirm as a real candidate defect, mark not applicable/already handled, or explain what additional discriminating evidence is needed. Do not repeat a concern as a bug without tracing it into an acceptance decision.
4. Check the supplied independent pure-test sources and 22-test green log only as supporting evidence. Identify missed concrete cases. Do not infer native behavior from pure tests.
5. Return only confirmed, actionable findings in the required schema. If no confirmed defect exists, return an empty findings array and state what remains unverified in safety_checks. Do not prescribe broad rewrite, relax deadlines, or claim GPU/build success.

EXACT ROOT TASK SPEC:
{spec}

ACTUAL CANDIDATE SOURCE:
{candidate}

PINNED SUPERVISOR `_shutdown` AND `run_workers` SOURCE EXCERPTS:
{critical}

ACTUAL ACCEPTANCE CALLER SOURCES:
--- native_driver.py ---
{inputs['native_driver'].read_text(encoding='utf-8')}
--- controller_compiler_completion_attempt5.py ---
{inputs['attempt5_controller'].read_text(encoding='utf-8')}
--- test_driver_acceptance_pure.py ---
{inputs['driver_tests'].read_text(encoding='utf-8')}

INDEPENDENT POST-QUERY CONTRACT TESTS:
--- test_post_query_guards.py ---
{inputs['postquery_tests'].read_text(encoding='utf-8')}
--- test_more_contract.py ---
{inputs['more_contract_tests'].read_text(encoding='utf-8')}
--- fallback_22_GREEN.log ---
{inputs['pure_green_log'].read_text(encoding='utf-8')}

ACTUAL MUSE REVIEW OF THE PREVIOUS QWEN CANDIDATE (NOT THIS FALLBACK):
Original Muse JSONL parser did not recognize Muse's native event envelope; one terminal object was separately extracted and accepted by the existing strict review intake. Muse provider run exited zero; use/tool/subagent usage was UNKNOWN. The candidate in that older review differs from the fallback under review here. Treat each item as a hypothesis to re-evaluate against current source/caller, not as established fact:
{findings}

OUTPUT CONTRACT: return exactly one JSON object with keys verdict, findings, safety_checks. verdict is a short string. findings is an array of objects, each having exactly region, exact_source, reason, minimal_fix (all nonempty strings; include exact line references where available). safety_checks is an array of nonempty strings. No markdown fences or text outside JSON. Do not claim this review authorizes native builds, GPU runs, or acceptance.
'''
(out/'gemini_prompt.txt').write_text(prompt,encoding='utf-8')
schema={'type':'object','additionalProperties':False,'properties':{'verdict':{'type':'string'},'findings':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'region':{'type':'string'},'exact_source':{'type':'string'},'reason':{'type':'string'},'minimal_fix':{'type':'string'}},'required':['region','exact_source','reason','minimal_fix']}},'safety_checks':{'type':'array','items':{'type':'string'}}},'required':['verdict','findings','safety_checks']}
(out/'gemini_schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
print(json.dumps({'folder':str(out),'prompt_bytes':(out/'gemini_prompt.txt').stat().st_size,'prompt_sha256':sha(out/'gemini_prompt.txt'),'candidate_sha256':views['candidate']['sha256'],'snapshot_count':len(views)},indent=2))
