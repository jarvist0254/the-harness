$ErrorActionPreference='Stop'
$base='E:\the_harness\records\factory_runs\20261004'
$out=Join-Path $base 'muse_l0_collector_prep_20261004T220000Z'
if(Test-Path -LiteralPath $out){throw 'immutable folder exists'}
New-Item -ItemType Directory -Path $out|Out-Null
$utf=[Text.UTF8Encoding]::new($false)
function Pin($p){@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $p).Length}}
function WriteNew($n,$s){[IO.File]::WriteAllText((Join-Path $out $n),$s,$utf)}
$qa='E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z'
$ip=Join-Path $qa 'MUSE_REVIEW_INPUT_PINS.json'
$manifest=Get-Content -LiteralPath $ip -Raw|ConvertFrom-Json
foreach($p in $manifest.inputs){if((Get-FileHash -LiteralPath $p.path).Hash.ToLowerInvariant()-cne$p.sha256){throw ('input pin mismatch '+$p.path)}}
$old=Join-Path $base 'muse_combined_dma_prep_20261004T205950Z'
Copy-Item -LiteralPath (Join-Path $old 'output_schema.json') -Destination (Join-Path $out 'output_schema.json')
$task=@'
Tough independent STATIC adversarial review of the actual in-house LevelZero query collector derivative5e8c32b98c1fec8fa708435fc7c039828b1ed1326fca269a0e1bb75fcd3edbd6. This is separately authored from originalQwen9f2635; another paidQwen repair of9f is running independently, NOT an input. Original immutable provider/source refusals remain. Review complete actual source, full real-header CPU stub, full independent tests and actual7-control RED/GREEN evidence. Seven controls moved original1PASS/6FAIL to derivative7PASS/0FAIL; this proves those CPU/header-stub cases ONLY. No Intel hardware/driver/P2P transport/context/allocations/physical capacity execution or product promotion is demonstrated. PASS status must qualify collector-only with direct_transport_qualified=false. Find genuine residual correctness gaps and test blind spots without inventing hardware failures or mistaking stub success for physical proof.

No tools, reading external user sessions, source imports, code execution, compiler/linker/native/GPU/API/network calls, filesystem edits, installs, authentication or delegation. No interactive userMuse session interference. Up to10 native child agents EACH Qwen/DeepSeek are authorized only if supported in their own lanes; this static Muse review launches no children/tools. Return only JSON verdict,findings,safety_checks under supplied schema: verdict SUPPORT_WITH_LIMITS|REQUEST_CHANGES|NEEDS_DISCUSSION; at most16 findings with exact region,exact_source,reason,minimal_fix nonempty strings each<=2048. Every finding must distinguish source-static fact, measured actual stub observation, and untested physical hypothesis. Do not force cosmetic edits or claim a global absence from bounded evidence. Review strict status PASS/FAIL/NOT_CHECKED exits0/1/2, preservation of actualAPI error codes versus documented missing prerequisites, validJSON/intfields, real enum guarded query behavior, full128bitUUID and physical-root/handle/subdevice lineage dedup, directedmatrix indices, bounded counts/mutating enumeration/error handling. Test malformed/error paths independent of implementation and whether seven passing tests miss genuine behavior. Original4 measuredRED and exact source/header/stub pins supplied below. No imports/native execution admission is given by verdict.
'@
WriteNew 'muse_collector.spec.txt' $task
$embed=@('source.local_derivative_revision2.cpp','actual_header_stub_local_revision2.cpp','test_measured_requirements.py','requirements_GREEN.stderr.log','requirements_RED.stderr.log','ADJUDICATION.md','ADJUDICATION.json')|ForEach-Object{Join-Path $qa $_}
$embed+=@('E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\STUB_ADJUDICATION_EXECUTED.md','E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\STUB_CONTRACT.pending.md', (Join-Path $base 'l0_compiler_two_prep_v2_20261004T214600Z\qwen_l0_query_measured_repair.api_excerpts.txt'))
$prompt=$task
foreach($p in $embed){$prompt+="`n`nVERBATIM INPUT $(Split-Path -Leaf $p) SHA $((Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant())`n"+[IO.File]::ReadAllText($p)}
$prompt+="`n`nADDITIONAL PINNED RECEIPTS: all18manifest inputs hash-checked; full official header and binary receipts NOT embedded, except verbatim selected actual header declarations above. Use source-stub-test observations only, do not claim you read full unstated files. Native execution absence/PE imports and controller statuses are summarized in actual adjudication, not proof of real drivers.`n"+[IO.File]::ReadAllText($ip)
if($utf.GetByteCount($prompt)-gt131072){throw 'Muse prompt exceeds frozen128KiB helper guard'}
WriteNew 'muse_collector.prompt.txt' $prompt
$wrapper=[IO.File]::ReadAllText((Join-Path $old 'run_muse_combined.v2.pending_admission.py'))
$newpins=@($manifest.inputs)+@((Pin $ip),(Pin (Join-Path $out 'muse_collector.spec.txt')),(Pin $embed[-1]))
$block="PINS = {`n"+(@($newpins|ForEach-Object{'    r"'+$_.path+'": "'+$_.sha256.ToUpperInvariant()+'",'})-join"`n")+"`n}"
$wrapper=[regex]::Replace($wrapper,'(?ms)^PINS = \{.*?^\}',$block)
$wrapper=$wrapper.Replace('E:\the_harness\records\factory_runs\20261004\muse_combined_dma_prep_20261004T205950Z',$out).Replace('muse_combined.v2.prompt.txt','muse_collector.prompt.txt').Replace('AE6A1A7FFB51189D871957C4349A7B475CA09CFA98407397FEFFBE0541748FFE',(Get-FileHash -LiteralPath (Join-Path $out 'muse_collector.prompt.txt')).Hash)
WriteNew 'run_muse_collector.pending_admission.py' $wrapper
$packet=@{utc=[DateTime]::UtcNow.ToString('o');status='PREPARATION_ONLY_NO_PROVIDER_LAUNCH';launch_authorized=$false;scope='STATIC_REVIEW_NO_SOURCE_IMPORT_NATIVE_OR_PHYSICAL_QUALIFICATION';model='muse-spark-1.3';provider='meta';deadline_seconds=300;capture_aggregate_bytes=2097152;source_sha256='5e8c32b98c1fec8fa708435fc7c039828b1ed1326fca269a0e1bb75fcd3edbd6';qa_manifest=(Pin $ip);inputs=@($newpins);full_embedded_inputs=@($embed|ForEach-Object{Pin $_});prompt=(Pin (Join-Path $out 'muse_collector.prompt.txt'));schema=(Pin (Join-Path $out 'output_schema.json'));wrapper=(Pin (Join-Path $out 'run_muse_collector.pending_admission.py'));wrapper_changes='Only ROOT/PROMPT/PINS/PROMPT_SHA256 task bindings replaced; transport, tool guards, kill-on-close Job, output limits and parser unchanged.';native_children_actual=0;actual_tests_not_executed_by_manager=$true}
WriteNew 'MUSE_COLLECTOR_ROOT_REVIEW_PACKET.json' ($packet|ConvertTo-Json -Depth 20)
Pin (Join-Path $out 'MUSE_COLLECTOR_ROOT_REVIEW_PACKET.json')|ConvertTo-Json
