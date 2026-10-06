from pathlib import Path
import hashlib,json
base=Path(r'E:\the_harness')
out=base/r'records\factory_runs\20261004\muse_qwen_linux_dmabuf_audit_20261004T190700Z'
items={
 'source':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_linux_dmabuf_transport\source.qwen_untrusted.cpp',
 'tests':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_linux_dmabuf_transport\tests_source.qwen_untrusted.txt',
 'spec':base/r'records\factory_runs\20261004\qwen_jlink_stream_six_20261004T184200Z\qwen_linux_dmabuf_transport.spec.txt',
}
manifest={}
for k,p in items.items():
 b=p.read_bytes(); dest=out/f'{k}.snapshot{p.suffix}';dest.write_bytes(b)
 manifest[k]={'original':str(p),'snapshot':str(dest),'sha256':hashlib.sha256(b).hexdigest().upper(),'bytes':len(b)}
(out/'inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
source=items['source'].read_text(encoding='utf-8'); tests=items['tests'].read_text(encoding='utf-8'); spec=items['spec'].read_text(encoding='utf-8')
prompt=f'''Independent Muse adversarial source review. Review only the exact embedded C++ query/transport candidate, its supplied tests, and exact spec. Do not use tools, execute, compile, modify files, inspect other folders, launch native/API work, query devices, or claim a tested transfer.

Focus on whether the artifact accurately distinguishes (a) finding DRM/Vulkan devices or nodes, (b) extension and external-memory capability queries, (c) actual legal export/import compatibility for specific allocations/resource types, (d) a functioning shared-data transfer, and (e) direct cross-vendor VRAM/P2P. Check API version/header/ABI assumptions, result-code and property handling, FD ownership/closure, size/alignment/offset/modifier constraints, memory type and dedicated-allocation requirements, queue-family ownership and semaphore/fence synchronization, timeout/resource bounds, parser strictness/overflow, and whether tests reject misleading partial-capability claims. Specifically challenge any inference from `/dev/dri`, DMA-BUF support, generic external memory, PCI topology, UUIDs, or handle import success to a valid NVIDIA↔Intel↔AMD VRAM transport. Name exact source lines and concrete counterexamples. Return only confirmed actionable findings; mark unresolved driver/API facts NOT_CHECKED. No forced edits if source is already only a capability query and labels it accurately.

Source SHA256 {manifest['source']['sha256']}
Tests SHA256 {manifest['tests']['sha256']}
Spec SHA256 {manifest['spec']['sha256']}

EXACT SPEC:
{spec}

SOURCE:
{source}

TESTS:
{tests}

Output exactly JSON keys verdict, findings, safety_checks. Each finding has exactly region, exact_source, reason, minimal_fix, all strings with current line numbers. No markdown or surrounding prose. No API execution/runtime/P2P acceptance claims. Empty findings is permitted when justified.
'''
if len(prompt.encode('utf-8'))>128*1024: raise SystemExit('prompt too large')
(out/'prompt.txt').write_text(prompt,encoding='utf-8')
schema={'type':'object','additionalProperties':False,'properties':{'verdict':{'type':'string'},'findings':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'region':{'type':'string'},'exact_source':{'type':'string'},'reason':{'type':'string'},'minimal_fix':{'type':'string'}},'required':['region','exact_source','reason','minimal_fix']}},'safety_checks':{'type':'array','items':{'type':'string'}}},'required':['verdict','findings','safety_checks']}
(out/'output_schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
# Clone previously audited bounded Job launcher, changing only owned folder and input pins.
old=base/r'records\factory_runs\20261004\muse_adversarial_20261004T172000Z\compiler_completion_audit\run_muse_job.py'
s=old.read_text(encoding='utf-8-sig')
s=s.replace(r'E:\the_harness\records\factory_runs\20261004\muse_adversarial_20261004T172000Z\compiler_completion_audit',str(out))
start=s.index('PINS = {'); end=s.index('\nMUSE_SHA256',start)
pins='PINS = {\n'+''.join(f'    {str(p)!r}: {manifest[k]["sha256"]!r},\n' for k,p in items.items())+'}'
# Ensure valid raw Windows path literals in the copied module.
pins='PINS = {\n'+''.join(f'    r"{p}": "{manifest[k]["sha256"]}",\n' for k,p in items.items())+'}'
s=s[:start]+pins+s[end:]
prompt_sha=hashlib.sha256((out/'prompt.txt').read_bytes()).hexdigest().upper()
schema_sha=hashlib.sha256((out/'output_schema.json').read_bytes()).hexdigest().upper()
s=s.replace('PROMPT_SHA256 = "AB6A6220AA9B4413B6D96E4D259D2968CBB29850B954BBA0EAB4EC397AA7B4D4"',f'PROMPT_SHA256 = "{prompt_sha}"')
s=s.replace('SCHEMA_SHA256 = "6D9132A41CA02CE6AFA6F6AE8BF436A06F76EDF865B19EFAF0943C9ED8FFDF16"',f'SCHEMA_SHA256 = "{schema_sha}"')
(out/'run_muse_job.py').write_text(s,encoding='utf-8')
print(json.dumps({'folder':str(out),'prompt_bytes':len(prompt.encode()),'prompt_sha256':prompt_sha,'schema_sha256':schema_sha,'input_pins':manifest,'runner_sha256':hashlib.sha256((out/'run_muse_job.py').read_bytes()).hexdigest().upper()},indent=2))
