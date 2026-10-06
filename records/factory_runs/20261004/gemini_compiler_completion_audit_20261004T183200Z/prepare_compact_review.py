from pathlib import Path
import hashlib,json
base=Path(r'E:\the_harness')
out=base/r'records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z'
existing=json.loads((out/'inputs.json').read_text(encoding='utf-8'))
proofdir=base/r'records\root_continuation_20261004\compiler_cleanup_refusal_proof_20261004T183508Z'
new={
 'cleanup_proof_result':proofdir/'proof_results.json',
 'cleanup_proof_test':proofdir/'test_actual_cleanup_demotions.py',
}
for key,path in new.items():
 dest=out/f'{key}.snapshot{path.suffix}';dest.write_bytes(path.read_bytes())
 existing[key]={'original':str(path),'snapshot':str(dest),'sha256':hashlib.sha256(path.read_bytes()).hexdigest().upper(),'bytes':path.stat().st_size}
(out/'inputs_compact.json').write_text(json.dumps(existing,indent=2),encoding='utf-8')

def lines(path,start,end):
 x=path.read_text(encoding='utf-8').splitlines()
 return '\n'.join(f'{i+1}: {x[i]}' for i in range(start-1,min(end,len(x))))
root=base/r'records\root_continuation_20261004'
inputs={k:base/v['original'].replace('E:\\the_harness\\','') for k,v in []}
supervisor=base/r'records\root_continuation_20261004\contained_build_policy_20261004T160430Z\contained_build_supervisor.py'
driver=base/r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py'
controller=base/r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\controller_compiler_completion_attempt5.py'
proof=(proofdir/'proof_results.json').read_text(encoding='utf-8')
muse=json.loads((out/'muse_review.snapshot.json').read_text(encoding='utf-8'))
findings=[]
for i,f in enumerate(muse['findings'],1):
 region=f.get('region','')
 reason=f.get('reason','').split('Executable')[0].strip()
 fix=f.get('minimal_fix','').split('. ')[0].strip()
 findings.append(f'{i}. {region}: concern={reason[:120]} ; suggested check={fix[:100]}')
summary='\n'.join(findings)
# Use only the exact cleanup/status lines needed for caller adjudication.
sup=(lines(supervisor,701,762))
nd=lines(driver,21,43)
ctrl=lines(controller,127,139)
spec=(base/r'records\root_continuation_20261004\COMPILER_COMPLETION_TASK_SPEC.md').read_text(encoding='utf-8')
candidate=(base/r'records\root_continuation_20261004\compiler_adapter_local_fallback_20261004T182833Z\compiler_completion_adapter.py').read_text(encoding='utf-8')
post_names='success cleanup; post-query cancel/overflow/bad-read/deadline; unexpected wait/exit types; timeout; wrong policy'
more_names='22 cases covering type guards, pre/post wait and query guards, exceptions, multiworker rejection, and cleanup request'
log=(base/r'records\root_continuation_20261004\compiler_adapter_independent_20261004T1818Z\fallback_22_GREEN.log').read_text(encoding='utf-8')
prompt=f'''Independent source-only Gemini review. No tools, shell, file reads, edits, execution, subprocesses, network, or additional model calls. All context needed is below. Audit the exact compiler adapter candidate against the pinned spec, generic caller, actual native-driver acceptance gate, and the reported Muse findings. Return only the required JSON schema.

Review the candidate independently. Trace failure states through the actual caller. In particular, determine if a hook may preserve COMPILER_ROOT_EXITED_CLEANUP_REQUIRED while cleanup is uncertain AND whether downstream acceptance can still accept it. The following four-case mock proof reports the actual caller refusal; verify its code and scope rather than assuming it generalizes. Classify each older Muse finding as CONFIRMED for this candidate, NOT_APPLICABLE/ALREADY_HANDLED, or NEEDS_EVIDENCE. Do not elevate wording/status concerns into false acceptance bugs without an end-to-end counterexample. Report only actionable current defects and meaningful missed tests. Native CPU fixtures are separate root-admitted evidence; pure mocks do not establish native behavior.

CANDIDATE SHA256 {existing['candidate']['sha256']}
SPEC SHA256 {existing['spec']['sha256']}
SUPERVISOR SHA256 {existing['supervisor']['sha256']}
NATIVE DRIVER SHA256 {existing['native_driver']['sha256']}
ATTEMPT-5 CONTROLLER SHA256 {existing['attempt5_controller']['sha256']}
CLEANUP PROOF RESULT SHA256 {existing['cleanup_proof_result']['sha256']}

EXACT TASK SPEC:\n{spec}

ACTUAL CANDIDATE:\n{candidate}

ACTUAL PINNED run_workers cleanup path (numbered source lines):\n{sup}

ACTUAL native_driver.validate_result (numbered source lines):\n{nd}

ACTUAL build controller stage acceptance (numbered source lines):\n{ctrl}

FOUR-CASE CALLER CLEANUP REFUSAL RESULT (actual FA907/emit pure mocks; no native calls):\n{proof}
FOUR-CASE TEST CASES: job close, owned-handle close, reader state, and shutdown failure. Each pure mock returned custom status with UNKNOWN_DRAIN, and actual native_driver.validate_result refused it. No native process calls.\nPOST-QUERY TEST CASES: {post_names}\nADDITIONAL CONTRACT TEST SUMMARY: {more_names}\n22-TEST PURE GREEN LOG:\n{log}

ACTUAL MUSE FINDINGS FROM REVIEW OF A DIFFERENT, EARLIER QWEN CANDIDATE. These are hypotheses to adjudicate against current fallback and caller, not presumed bugs:\n{summary}

Return exactly {{verdict, findings, safety_checks}}; each finding exactly {{region, exact_source, reason, minimal_fix}}. Include exact current source line references. Empty findings is correct if no current defect is established. No native/build/GPU acceptance claim.
'''
if len(prompt)>26000: raise SystemExit(f'prompt too large for Windows argv: {len(prompt)} chars')
(out/'gemini_prompt_compact.txt').write_text(prompt,encoding='utf-8')
print(json.dumps({'chars':len(prompt),'bytes':len(prompt.encode()),'sha256':hashlib.sha256(prompt.encode()).hexdigest().upper(),'source':existing['candidate']['sha256'],'proof_sha':existing['cleanup_proof_result']['sha256']},indent=2))

