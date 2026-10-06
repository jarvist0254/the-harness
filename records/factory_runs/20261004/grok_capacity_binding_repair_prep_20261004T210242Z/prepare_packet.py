"""Source/data-only preparation. Does not import candidate or launch a provider."""
import ast, hashlib, json, pathlib
R = pathlib.Path(__file__).parent
OLD = pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_capacity_repair_prep_20261004T203621Z')
C = OLD/'grok_capacity_high'
QA = pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\capacity_grok_root_audit_20261004T205640Z')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(C/'source.grok_untrusted.py') == '4a27892638447b0913aa2faffa8b4c6c1615011ddc8fde54550fceb9f1190211'
assert sha(C/'tests_source.grok_untrusted.txt') == '1a885582f610a0144479a90be787d049f8afedadd86da8d7810c2b85c428b114'
assert sha(QA/'execution_receipt.json') == '4da149e4f51a0428cf1af239ad11009d79fa5781739dc157b940c9a01bb2a9af'
assert sha(QA/'stdout.raw.json') == '6b01aba1b1b29ca2eae440cfbf5644a583dfac7092c40cd706dd34f9bb3eb238'
assert sha(QA/'AUDIT.md') == 'acc960e13aed07471e156ff2179c0b0d4490ef233f730f55a82a0ef69ef95653'
pins = {}
for name in ['invoke_owned_capacity_editor.ps1', 'provider_common.ps1', 'research_artifact.ps1']:
    data = (OLD/name).read_bytes()
    with (R/name).open('xb') as output: output.write(data)
    assert sha(R/name) == sha(OLD/name)
    pins[str(R/name)] = sha(R/name)
instruction = '''PREPARATION ONLY. No provider launch until ROOT authorizes the actual hash-pinned packet. Source-only Grok4.7-build-fast HIGH corrective editor; output ONE strict JSON with exactly status,source,tests_source,analysis,prerequisites,evidence_limits,references. Status PROPOSED|REFUSED|ANALYSIS. Complete replacement module and actual-file pure tests each<=131072 characters. Nonempty concise explanation arrays. No tools, files, processes, network, native/GPU execution, subagents or source promotion. Actual hardware qualification remains NOT_CHECKED; synthetic acceptance cannot certify physical VRAM/P2P/capacity.

Continue the completed Muse→Gemini→Grok capacity chain using ROOT measured independent feedback only. Correct EXACTLY these three measured RED cases against actual source4a278926: CPU_payload_disagrees_with_registered_reference_bytes, single_attempt_foreign_physical_population, three_attempt_foreign_physical_population. Preserve the44 current independent passing controls and original4 RED fixes, exact4 policy (5 physical cards refuse), unique positive resident shards on every owner, cumulative peak coverage, matching OOM workload/artifact pins, strict finite numeric types, input immutability, fixed per-logit tolerance and original1e-12 metric rounding bound. Do not widen tolerance, add CPU fallback, fabricate allocator/native evidence or claim whole hardware goal complete. Native current host has NV5070Ti plus AMD shared iGPU, no Intel GPU and no four-card physical result.

ROOT-PENDING bounded CPU reference schema proposal, for ROOT review: the existing named trusted['cpu_reference_hash'] registry slot accepts actual immutable bytes/bytearray or a lowercase64 SHA digest. To validate actual CPU values, bytes must be available: when the slot is digest-only, require separately named trusted['cpu_reference_bytes']; bind its actual SHA to that digest and evidence CPU reference hash. Bytes are UTF-8 JSON containing ONLY a flat ordered nonempty array of finite numbers (no bool, object, null, string, NaN or Infinity), representing EVERY CPU value corresponding one-to-one to four.execution.logits in the same order. Proposed bounds16MiB bytes /1048576 values, not an accepted historical limit or hardware count; explicitly document these proposed bounds for ROOT. Reject missing payload, malformed/oversized reference, count mismatch, unrepresentable/range-invalid numbers or CPU value mismatches fail-closed. Use strict non-bool finite value conversion consistent with the current safely representable numeric contract; compare CPU values exactly after that conversion, never through numeric execution tolerance. Our actual positive reference bytes are b'[1.0]'; preserve that legal fixture and input bytearrays unchanged. Only metadata digest agreement is insufficient. Hash/check full raw reference bytes before parsing and verify all supplied CPU values, not a prefix. Don't infer native execution or reference truth from a registered synthetic payload. Other artifact hash/digest registry semantics remain unchanged.

Population fix: SINGLE and THREE OOM participants must resolve to respectively1 and3 distinct physical owners from the SAME FOUR qualified physical-owner population. Resolve explicit aliases/root-subdevice mappings unambiguously against four owners; repeated enumeration of the same physical canonical root remains legal. Require owner subsets; unrelated hardware OOM must refuse. No index/name/vendor-only fallback. An alias matching multiple physical owners or missing stable ownership is NOT_CHECKED/refused, never counted as another card. Retain exact4 distinct discrete policy and current shared/unknown backing refusal. Do not blindly count runtime subdevices as extra physical devices or reject the current legal same-canonical-root alias controls. The current source stores canonical sets but never compares cross-role participant populations.

Actual evaluator47 tests:44PASS/3RED/0exceptions; original4 fixed. Owned PID83872 exit1/reaped.188s, zero traps, pins unchanged. These are synthetic validator observations only. Preserve all raw old artifacts. Return useful actual-file tests importing CANDIDATE_PATH, never embed a duplicate implementation. Include the three actual mutations plus positive legal baseline and existing coverage regressions; no provider test execution. ROOT will independently retarget unchanged47 controls and additional schema-bound controls after actual-source review.
'''
prompt = instruction
for label, path in [('ACTUAL CANDIDATE', C/'source.grok_untrusted.py'), ('ACTUAL PROVIDER TESTS NOT EXECUTED', C/'tests_source.grok_untrusted.txt'), ('INDEPENDENT ACTUAL TEST SOURCE', QA/'test_independent_capacity.py'), ('INDEPENDENT RAW47 RESULTS', QA/'stdout.raw.json'), ('INDEPENDENT AUDIT', QA/'AUDIT.md')]:
    prompt += '\n===== '+label+' SHA256 '+sha(path)+' =====\n'+path.read_text(encoding='utf-8')+'\n'
prompt_path = R/'grok_capacity_binding_high.prompt.txt'
with prompt_path.open('x', encoding='utf-8', newline='\n') as output: output.write(prompt)
assert prompt_path.stat().st_size <= 262144
pins[str(prompt_path)] = sha(prompt_path)
job = 'grok_capacity_binding_high'
admission = {'provider_launch_authorized': False, 'batch_path': str(R), 'job_id': job, 'lane': 'Grok', 'model': 'grok-4.7-build-fast', 'source_path': str(C/'source.grok_untrusted.py'), 'source_sha256': sha(C/'source.grok_untrusted.py'), 'prompt_sha256': sha(prompt_path), 'authorization': 'PENDING_ROOT_REVIEW_NO_LAUNCH'}
with (R/'ROOT_LAUNCH_BINDING.pending.json').open('x', encoding='utf-8') as output: json.dump(admission, output, indent=2)
packet = {'status': 'PREPARED_PENDING_ROOT_AUTHORIZATION', 'provider_launched': False, 'job': job, 'model': 'grok-4.7-build-fast', 'reasoning_effort': 'high', 'deadline_seconds': 600, 'per_stream_cap_bytes': 2097152, 'copied_helpers_byte_identical': True, 'helper_and_prompt_pins': pins, 'candidate_source_pin': sha(C/'source.grok_untrusted.py'), 'source_file': str(C/'source.grok_untrusted.py'), 'actual_qa': {'path': str(QA/'execution_receipt.json'), 'sha256': sha(QA/'execution_receipt.json'), 'counts': {'total': 47, 'pass': 44, 'red': 3}}, 'proposed_new_reference_bounds': {'bytes': 16777216, 'values': 1048576, 'authorization': 'PENDING_ROOT_SCHEMA_REVIEW'}, 'native_gpu_provider_execution': False, 'pending_admission_path': str(R/'ROOT_LAUNCH_BINDING.pending.json')}
with (R/'PREPARATION_PACKET.json').open('x', encoding='utf-8') as output: json.dump(packet, output, indent=2)
print(json.dumps({'packet_sha256': sha(R/'PREPARATION_PACKET.json'), 'prompt_sha256': sha(prompt_path), 'prompt_bytes': prompt_path.stat().st_size, 'helper_sha256': sha(R/'invoke_owned_capacity_editor.ps1')}, indent=2))
