from pathlib import Path
import hashlib,json
base=Path(r'E:\the_harness')
out=base/r'records\factory_runs\20261004\grok_compiler_adapter_correction_20261004T184500Z'
paths={
 'candidate':base/r'records\root_continuation_20261004\compiler_adapter_local_fallback_20261004T182833Z\compiler_completion_adapter.py',
 'spec':base/r'records\root_continuation_20261004\COMPILER_COMPLETION_TASK_SPEC.md',
 'gemini':base/r'records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z\gemini_review_attempt2.pending_root_qa.json',
 'gemini_intake':base/r'records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z\gemini_intake_reconciliation.json',
 'muse':base/r'records\factory_runs\20261004\muse_adversarial_20261004T172000Z\compiler_completion_audit\run_output\parsed_review.json',
 'proof':base/r'records\root_continuation_20261004\compiler_cleanup_refusal_proof_20261004T183508Z\proof_results.json',
 'proof_tests':base/r'records\root_continuation_20261004\compiler_cleanup_refusal_proof_20261004T183508Z\test_actual_cleanup_demotions.py',
 'native_driver':base/r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py',
 'attempt5_controller':base/r'records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\controller_compiler_completion_attempt5.py',
 'runtime_query_helper':base/r'records\root_continuation_20261004\fixture_runtime_win32_query_revision2.py',
 'pure_green':base/r'records\root_continuation_20261004\compiler_adapter_independent_20261004T1818Z\fallback_22_GREEN.log',
}
manifest={}
for k,p in paths.items():
 b=p.read_bytes(); d=out/f'{k}.snapshot{p.suffix}'; d.write_bytes(b)
 manifest[k]={'original':str(p),'snapshot':str(d),'sha256':hashlib.sha256(b).hexdigest().upper(),'bytes':len(b)}
(out/'inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
source='\n\n'.join(f'--- {k} SHA256 {v["sha256"]} ---\n{Path(v["original"]).read_text(encoding="utf-8")}' for k,v in manifest.items())
prompt=f'''You are Grok Build Fast acting as a conservative corrective editor for a compiler-only adapter. Inputs are fully embedded. Do not use tools, execute code, read files, search, use network, create subagents, or modify any original artifact. Return one strict JSON object only. Review first, then propose the smallest source patch only if you can demonstrate a current defect. Preserve the candidate byte-for-byte if no actionable issue survives end-to-end tracing. Do not force cosmetic edits or fabricate exactly three changes.

Primary target: local adapter SHA {manifest['candidate']['sha256']}. Required behavior is in the exact ROOT spec. Gemini's exact review is embedded (V2 strict accepted, PASS/zero findings/12 checks); the full Muse review is also embedded but was against a different previous Qwen candidate. ROOT's 4-case actual supervisor/caller mock proof shows shutdown/owned-close/reader/job-close failures all produce UNKNOWN_DRAIN and the native driver refuses each; no native calls were made. Independently verify this before deciding whether the earlier Muse cleanup concern applies. The root owns applying, testing, and any native fixture admission.

Primary target corrections (if needed): return `adapter_changes` as zero or more exact search/replace pairs. Each search must match the target uniquely and replacement must preserve all unaffected behavior. Provide a concrete failing pure test or source-grounded counterexample for every proposed change. Do not edit generic supervisor or caller files.

Secondary QA target: helper `{manifest['runtime_query_helper']['original']}` SHA {manifest['runtime_query_helper']['sha256']}. This is a separate 3-line native runtime query error correction. Review whether `GetExitCodeProcess` zero result should raise an OSError/WinError so the existing native cleanup/refusal path catches it, rather than returning a false value or unrelated exception. Do not mix this helper patch into the adapter source; provide separate `helper_changes`, zero or more exact search/replace pairs, and tests needed. The helper is source-only in this task; do not run it.

Output JSON schema:
{{
  "verdict": "NO_SOURCE_CHANGES" or "PROPOSED_PATCHES",
  "adapter_findings": [{{"region":"...","exact_source":"...","reason":"...","minimal_fix":"..."}}],
  "adapter_changes": [{{"search":"...","replace":"..."}}],
  "helper_findings": [{{"region":"...","exact_source":"...","reason":"...","minimal_fix":"..."}}],
  "helper_changes": [{{"search":"...","replace":"..."}}],
  "tests": ["concrete pure test cases for each proposed patch; otherwise explain no new case is needed"],
  "rationale": ["..."],
  "safety_checks": ["..." ]
}}
Require 0..4 adapter changes and 0..3 helper changes; arrays may be empty. Exact object keys only. Do not claim code was applied, tests passed, native runtime succeeded, or broader build/GPU acceptance.

COMPLETE PINNED SOURCE AND REVIEW CONTEXT:
{source}
'''
if len(prompt.encode('utf-8'))>262144: raise SystemExit('prompt exceeds 256 KiB')
(out/'grok_prompt.txt').write_text(prompt,encoding='utf-8')
print(json.dumps({'folder':str(out),'prompt_bytes':(out/'grok_prompt.txt').stat().st_size,'prompt_sha256':hashlib.sha256((out/'grok_prompt.txt').read_bytes()).hexdigest().upper(),'candidate_sha256':manifest['candidate']['sha256'],'input_count':len(manifest)},indent=2))

