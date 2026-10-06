from pathlib import Path
import hashlib,json
base=Path(r'E:\the_harness')
out=base/r'records\factory_runs\20261004\qwen_numeric_state_ledger_reviews_20261004T190300Z'
items={
 'source':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_vulkan_numeric_state_ledger\source.qwen_untrusted.py',
 'tests':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_vulkan_numeric_state_ledger\tests_source.qwen_untrusted.txt',
 'spec':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_vulkan_numeric_state_ledger.spec.txt',
}
manifest={}
for k,p in items.items():
 b=p.read_bytes(); dest=out/f'{k}.snapshot{p.suffix}'; dest.write_bytes(b)
 manifest[k]={'original':str(p),'snapshot':str(dest),'sha256':hashlib.sha256(b).hexdigest().upper(),'bytes':len(b)}
(out/'inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
source=items['source'].read_text(encoding='utf-8')
tests=items['tests'].read_text(encoding='utf-8')
spec=items['spec'].read_text(encoding='utf-8')
prompt=f'''Independent Gemini code review. This is a pure Python numerical-diagnostic state ledger and strict result validator; review source and tests against the exact spec. Do not use tools, execute code, modify files, access other paths, query services, or infer hardware results. Cite exact source/test line numbers and give concrete counterexamples with minimal fixes. Prioritize fail-closed validation, provenance/hash binding, finite numeric and strict integer/boolean handling, full 151936-logit parity accounting, immutable append-only history, legal state transitions, distinguishing numeric failure/runtime failure/NOT_CHECKED/comparator controls, and avoiding unsupported P2P/GPU status claims. Review test quality against actual code; identify missing tests that would catch a real defect. Return only the specified strict JSON review schema; do not write replacement source.

Timeline correction: the spec includes an older Q8_0/F32 failure as context. ROOT now reports separate later derived-F32 normal and reverse-order runs with zero failures among all 151936 logits at fixed 0.01/0.01 tolerance. Treat those as a separately measured root result, not as proof from this candidate or review. Preserve the older failures as their own immutable records. A wrong-flag bad_arg control was discovered and is pending correction; do not claim that control passed. No mixed-vendor P2P, dedicated VRAM, four-card capacity, or accepted model qualification follows from these results.

Exact delivered source SHA256: {manifest['source']['sha256']}
Exact delivered tests SHA256: {manifest['tests']['sha256']}
Exact specification SHA256: {manifest['spec']['sha256']}

SPECIFICATION:
{spec}

UNTRUSTED CANDIDATE SOURCE:
{source}

UNTRUSTED CANDIDATE TESTS:
{tests}

Output exactly one JSON object with keys verdict, findings, safety_checks. verdict is a short string. findings is an array of objects having exactly region, exact_source, reason, minimal_fix (all strings, cite line references). safety_checks is an array of nonempty strings. Do not use markdown fences or add surrounding prose. Empty findings is valid only if no confirmed defect is found. No source/test execution or native/GPU acceptance claim.
'''
if len(prompt)>30000: raise SystemExit(f'prompt too long for Windows command line: {len(prompt)}')
(out/'gemini_prompt.txt').write_text(prompt,encoding='utf-8')
schema={'type':'object','additionalProperties':False,'properties':{'verdict':{'type':'string'},'findings':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'region':{'type':'string'},'exact_source':{'type':'string'},'reason':{'type':'string'},'minimal_fix':{'type':'string'}},'required':['region','exact_source','reason','minimal_fix']}},'safety_checks':{'type':'array','items':{'type':'string'}}},'required':['verdict','findings','safety_checks']}
(out/'gemini_schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
print(json.dumps({'folder':str(out),'prompt_chars':len(prompt),'source_sha256':manifest['source']['sha256'],'tests_sha256':manifest['tests']['sha256'],'spec_sha256':manifest['spec']['sha256'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest().upper()},indent=2))
