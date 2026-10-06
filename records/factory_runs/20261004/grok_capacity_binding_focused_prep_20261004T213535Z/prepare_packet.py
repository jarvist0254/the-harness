"""Compact source-only provider packet preparation; no imports of candidates/calls."""
import hashlib,json,pathlib
R=pathlib.Path(__file__).parent
OLD=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_capacity_binding_repair_prep_20261004T210242Z')
C=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_capacity_repair_prep_20261004T203621Z\grok_capacity_high\source.grok_untrusted.py')
QA=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\capacity_grok_root_audit_20261004T205640Z')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(C)=='4a27892638447b0913aa2faffa8b4c6c1615011ddc8fde54550fceb9f1190211'
assert sha(OLD/'FINAL_TIMEOUT_RECEIPT.json')=='2b8a04ae0ae6ffadb6a9ecf3d8f24c13a628555a2de39dc4a5ab6d2e325da2e3'
assert sha(QA/'stdout.raw.json')=='6b01aba1b1b29ca2eae440cfbf5644a583dfac7092c40cd706dd34f9bb3eb238'
for name in ['invoke_owned_capacity_editor.ps1','provider_common.ps1']:
    with (R/name).open('xb') as output:output.write((OLD/name).read_bytes())
    assert sha(R/name)==sha(OLD/name)
intake=(OLD/'research_artifact.ps1').read_text()
intake=intake.replace("foreach($n in @('source','tests_source')){if($a.$n-isnot[string]-or$a.$n.Length-gt131072){throw 'source bound'}}", "foreach($n in @('source','tests_source')){$cap=if($n-ceq'source'){32768}else{16384};if($a.$n-isnot[string]-or$a.$n.Length-gt$cap){throw 'source bound'};if($a.status-ceq'PROPOSED'-and[string]::IsNullOrWhiteSpace($a.$n)){throw 'PROPOSED source/tests missing'}}")
assert intake!=(OLD/'research_artifact.ps1').read_text()
(R/'research_artifact.ps1').write_text(intake,encoding='utf-8')
instruction='''PREPARATION ONLY: no launch until ROOT reviews/adopts this exact packet. Source-only Grok4.7-build-fast HIGH correction. Return ONE strict JSON with exactly status,source,tests_source,analysis,prerequisites,evidence_limits,references; statusPROPOSED|REFUSED|ANALYSIS. Complete replacement Python module <=32768 characters; actual-file tests <=16384 characters. Nonempty explanation arrays. No tools, source execution, files, provider/native/GPU calls, subagents or product promotion. Tests load supplied CANDIDATE_PATH, never embed an implementation. No hardware/P2P/capacity proof from synthetic data.

Make only these THREE measured binding corrections to exact source4a278926 below. Its existing47 independent controls measured44PASS/3RED and the original4 contradictions are fixed. Preserve those44passing assertions, exact4 distinct discrete policy, legal repeated-root/same-canonical-subdevice aliases, multiple resident shards/card, unique nonreplicated shards on all owners, cumulative peak coverage, matching OOM artifact/workload pins, input immutability, finite strict numerical values, fixed per-logit tolerance and original1e-12 rounding consistency. No tolerance widening, extra framework or unrelated redesign. Actual current machine has no4-card capacity evidence.

1 ACTUAL_CPU_PAYLOAD_BINDING. Existing trusted named cpu_reference_hash slot may be actualbytes/bytearray or lowercase64SHA digest. ROOT APPROVED NEW experimental schema: full ordered UTF8 JSON nonempty flat finite-number array, max16777216 bytes and1048576 values. Hash complete rawbytes before parsing; reject malformed JSON, objects/null/bool/strings/NaN/Infinity/unsafe huge numbers; bound byte/value counts. When slot is digest-only, require trusted['cpu_reference_bytes'] and bind actualbytes to that digest and evidence hash. Missing payload is NOT_CHECKED, not authority-by-hash. Compare full reference count and every supplied logits[*].cpu value EXACTLY after safe numerical conversion (no execution tolerance); ordered data must match. CPU registry bytes b'[1.0]' is the existing legal fixture. Bytearray inputs remain unchanged. Metadata labels/digests are not evidence of native execution. New serialization contract is explicit, not claimed historical artifact format.

2 SINGLE_PHYSICAL_OWNER_SUBSET and3 THREE_PHYSICAL_OWNER_SUBSET. OOM attempts must resolve respectively1 and3 distinct physical participants from the SAME qualified four-card physical population. Use explicit unambiguous canonical root/aliases; do not use vendor/index/name-only fallback. Resolve overlap across roles into four owners and require subsets. Unknown or multiple owner mappings refuse. Repeated enumeration of the same canonical physical root remains legal; subdevice rows do not count as extra physical cards. Retain exact4 (5 refuses), discrete/shared/backing checks and current residency/peak/statistics protections.

MEASURED MUTATIONS, all other bindings unchanged:
- CPU registered bytes b'[1.0]' and full digest remain fixed. Supplied pair CPU1/GPU1.05 -> CPU2/GPU2.05 with corresponding recomputed errors: actualoldPASS, mustREFUSE.
- Four physical IDs0,1,2,3 remain fixed. SINGLE OOM devices [7]: actualoldPASS, mustREFUSE.
- Same four remain fixed. THREE OOM devices [5,6,7]: actualoldPASS, mustREFUSE.
The raw measured findings are copied in compact JSON below; no whole47outcome text, previous provider tests or audit essays are included. Prior600.43-second timeout/empty streams/noartifact remains preserved, not a successful repair. This request cannot grant its own runtime admission. Provide concise real fixes and useful positive/negative tests, no essay. ROOT will read actual source and retarget the independent47 controls plus schema cases afterward.
'''
raw=json.loads((QA/'stdout.raw.json').read_text())
reds=[case for case in raw['cases'] if not case['passed']]
prompt=instruction+'\n===== EXACT ACTUAL SOURCE SHA256 '+sha(C)+' =====\n'+C.read_text()+'\n===== ACTUAL THREE RED OBSERVATIONS =====\n'+json.dumps(reds,indent=2)
prompt_path=R/'grok_capacity_binding_focused_high.prompt.txt'
prompt_path.write_text(prompt,encoding='utf-8')
job='grok_capacity_binding_focused_high'
binding={'provider_launch_authorized':False,'batch_path':str(R),'job_id':job,'lane':'Grok','model':'grok-4.7-build-fast','source_path':str(C),'source_sha256':sha(C),'prompt_sha256':sha(prompt_path),'authorization':'PENDING_ROOT_REVIEW_NO_PROVIDER_LAUNCH'}
(R/'ROOT_LAUNCH_BINDING.pending.json').write_text(json.dumps(binding,indent=2))
packet={'status':'PREPARED_PENDING_ROOT_AUTHORIZATION','provider_launched':False,'model':'grok-4.7-build-fast','reasoning_effort':'high','owned_deadline_seconds':600,'stream_cap_bytes':2097152,'source_contract_max_chars':32768,'tests_contract_max_chars':16384,'prompt_bytes':prompt_path.stat().st_size,'candidate_source_path':str(C),'candidate_source_sha256':sha(C),'pins':{name:sha(R/name) for name in ['invoke_owned_capacity_editor.ps1','provider_common.ps1','research_artifact.ps1',prompt_path.name,'ROOT_LAUNCH_BINDING.pending.json']},'prior_timeout_receipt_path':str(OLD/'FINAL_TIMEOUT_RECEIPT.json'),'prior_timeout_receipt_sha256':sha(OLD/'FINAL_TIMEOUT_RECEIPT.json'),'independent47_result_path':str(QA/'stdout.raw.json'),'independent47_result_sha256':sha(QA/'stdout.raw.json'),'only_three_measured_binding_repairs':True,'native_gpu_provider_execution':False}
(R/'PREPARATION_PACKET.json').write_text(json.dumps(packet,indent=2))
print(json.dumps({'packet_sha256':sha(R/'PREPARATION_PACKET.json'),'prompt_sha256':sha(prompt_path),'prompt_bytes':prompt_path.stat().st_size,'intake_sha256':sha(R/'research_artifact.ps1')},indent=2))
