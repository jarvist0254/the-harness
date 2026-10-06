$ErrorActionPreference='Stop'
$base='E:\the_harness\records\factory_runs\20261004'
$out=Join-Path $base 'l0_compiler_two_prep_v2_20261004T214600Z'
if(Test-Path -LiteralPath $out){throw 'immutable preparation already exists'}
New-Item -ItemType Directory -Path $out|Out-Null
$utf=[Text.UTF8Encoding]::new($false)
function WriteNew($name,$text){[IO.File]::WriteAllText((Join-Path $out $name),$text,$utf)}
function Pin($p){@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $p).Length}}
$helpers=Join-Path $base 'l0_egl_sync_bridge_two_prep_20261004T212837Z'
foreach($n in @('invoke_owned_stream_research.v3.ps1','qwen_http_stream_research.v3.ps1','provider_common.ps1','research_artifact.v3.ps1','PURE_LIMIT_CONTROLS.json')){Copy-Item -LiteralPath (Join-Path $helpers $n) -Destination (Join-Path $out $n)}
$header='E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h'
$hl=[IO.File]::ReadAllLines($header)
$peer=Join-Path $base 'qwen_transfer_four_prep_20261004T202539Z\qwen_l0_peer_repair\source.SCHEMA_REFUSED_UNTRUSTED_REVIEW_ONLY.txt'
$query='E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\source.original_untrusted.cpp'
$sources=@{qwen_l0_peer_compile_repair=$peer;qwen_l0_query_measured_repair=$query}
$evidence=@{
 qwen_l0_peer_compile_repair=@('E:\the_harness\records\root_continuation_20261004\peer_copy_source_compile_20261004T210634Z\compile_qa_findings.md','E:\the_harness\records\root_continuation_20261004\peer_copy_source_compile_20261004T210634Z\compile.stderr.txt','E:\the_harness\records\root_continuation_20261004\peer_copy_source_compile_20261004T210634Z\compile_receipt.json');
 qwen_l0_query_measured_repair=@('E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\STUB_ADJUDICATION_EXECUTED.md','E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\actual_header_stub_DRAFT.cpp','E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\stub_build_20261004T213121Z\runtime_receipt.json')
}
$common=@'
User authorizes maximum 10 native child agents EACH Qwen/DeepSeek parent if actually supported; this direct HTTP job has NO tools or native child support, actual native children=0. Use qwen3.8-max maximum supported xhigh reasoning. Do not execute, compile, import, browse, install, authenticate or modify files. Supplied primary excerpts are the source of truth; distinguish source design from hardware proof. Return ONE complete JSON object only with exact keys status,source,tests_source,analysis,prerequisites,evidence_limits,references. status PROPOSED|ANALYSIS|REFUSED. source and tests_source must be strings, source<=32000 UTF16 characters, tests_source<=16000; all four explanatory fields arrays of 1..40 nonempty strings <=8192 each. Provide COMPLETE usable C++ and actual-file behavioral CPU test/stub source, not grep tests, not embedded copied implementation. Missing Intel hardware is NOT_CHECKED/exit2, observed attempted native API failure is FAIL/exit1, collector or payload success PASS/exit0 only for its declared narrow scope. Always direct_transport_qualified=false. Never claim physical P2P, residency, four-card capacity or actual execution from metadata. No source execution is authorized by this response.
'@
$directive=@{
 qwen_l0_peer_compile_repair=@'
Repair the EXACT source414474 compiler failure, not the older f0e4 source. All five measured compiler errors use nonexistent ZE_RESULT_ERROR_FAILURE. Use legitimate result codes preserving native errors and explicit own invariant categories rather than fabricate API results. Correct other measured static faults: strict CLI unknown/duplicate/extra refusals; capped driver/root/subdevice enumeration with errors preserved; full128bit UUID, root/subdevice physical alias refusal, selected directed peer API/property results separately recorded. Exact official API/PFN/struct signatures govern all calls. Select queue group with actual numQueues; allocations owned by intended roots and checked type/owner. Device-fill64KiB producer, optional ONE word at32768 byte fault through GPU command BEFORE copy, unchanged independent CPU reference; compare all16384 words, require control exactly expected injected word/value to classify specifically detected. Bound each GPU wait10s; timed-out work must NOT be destroyed/freed as if drained. Honest UNKNOWN_DRAIN/failure and owned process external supervision is acceptable; no guarantee native calls can be cancelled. Check every cleanup result before final one JSON receipt, separate unsupported prerequisites from actual errors. Preserve scope PAYLOAD_EXPERIMENT_ONLY even PASS. Provide behavioral tests of actual-file CLI/status/UUID/dedup/count/API failure/FD-free cleanup state and targeted native-header stubs; no native/GPU execution by you.
'@;
 qwen_l0_query_measured_repair=@'
Repair exact9f2635 query-only collector using actual measured four RED controls. JSON numeric vendor/device values cannot be bare0x; genuine official enum is not preprocessor macro, so remove defined(enum) and call supported official zeDeviceGetExternalMemoryProperties with preserved API codes/unknown capability. DEVICE_LOST zeInit is observed failure FAIL1 not NOT_CHECKED2. Exact duplicate root handle/fullUUID must not count as extra physical root; expose enumeration row count separately if useful, root/fullUUID lineage and directed peer matrix mapped to deduplicated roots. Enumerate subdevices only to report lineage/aliases, no counting them as cards. Strict machine schema status PASS|FAIL|NOT_CHECKED and exits0|1|2, all uint counts capped before vector allocation and VK-like incomplete mutation handled by L0 actual semantics not invented enums. Full128bit UUID, strict integer result/vendor/device numbers, unknown capability remains unknown not unsupported. NO contexts, allocations, queues, transfers/import/export or hardware claims. PASS qualifies collector only with direct_transport_qualified=false ALWAYS. Supply actual-header CPU behavioral stub/tests importing real official ze_api.h, no fake enum macros/no LZQ_TEST_NO_HEADER; assert strict JSON, actual query counters, injected device-lost classification and duplicate dedup/directed lineage. Tests target actual source path supplied by caller, not copied implementation. Existing stub/report is evidence, not a passing test of new candidate.
'@
}
$jobs=@()
foreach($job in @('qwen_l0_peer_compile_repair','qwen_l0_query_measured_repair')){
 $source=[IO.File]::ReadAllText($sources[$job]);WriteNew ($job+'.source.snapshot.txt') $source
 $apiNames=@([regex]::Matches($source,'\bze[A-Z][A-Za-z0-9_]+\s*\(')|ForEach-Object{$_.Value.TrimEnd('(',' ')})|Sort-Object -Unique
 $types=@([regex]::Matches($source,'\bze_[a-z0-9_]+_t\b')|ForEach-Object{$_.Value})|Sort-Object -Unique
 $parts=[Collections.Generic.List[string]]::new();$parts.Add('Verbatim selected declarations from official ze_api.h SHA c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de. Line numbers are explanatory, not source patches. All supplied definitions derive from this file.')
 foreach($name in @($apiNames)+@($types)){
  $indexes=@(for($i=0;$i-lt$hl.Length;$i++){if($hl[$i]-match ('^'+[regex]::Escape($name)+'\s*\(') -or $hl[$i]-match ('^typedef (struct|enum) _'+[regex]::Escape($name)+'\s*$')){$i}})
  foreach($i in $indexes){$end=$i;while($end-lt$hl.Length-1-and$hl[$end]-notmatch '^\s*\);\s*$'-and$hl[$end]-notmatch ('^}\s*'+[regex]::Escape($name)+'\s*;')){$end++};$start=[Math]::Max(0,$i-2);$parts.Add("HEADER lines $($start+1)-$($end+1)`n"+($hl[$start..$end]-join"`n"))}
 }
 $excerpts=$parts-join"`n`n";WriteNew ($job+'.api_excerpts.txt') $excerpts
 $spec=$common+"`n`nTASK`n"+$directive[$job];WriteNew ($job+'.spec.txt') $spec
 $prompt=$spec+"`n`nEXACT ORIGINAL SOURCE (untrusted, preserve)`n"+$source+"`n`nOFFICIAL HEADER DECLARATIONS`n"+$excerpts
 foreach($p in $evidence[$job]){$prompt+="`n`nACTUAL EVIDENCE $(Split-Path -Leaf $p) SHA $((Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant())`n"+[IO.File]::ReadAllText($p)}
 WriteNew ($job+'.prompt.txt') $prompt
 $jobs+=@{job=$job;model='qwen3.8-max';reasoning_effort='xhigh';enable_thinking=$true;thinking_budget_absent=$true;source_pin=(Pin $sources[$job]);snapshot_pin=(Pin (Join-Path $out ($job+'.source.snapshot.txt')));spec_pin=(Pin (Join-Path $out ($job+'.spec.txt')));prompt_pin=(Pin (Join-Path $out ($job+'.prompt.txt')));api_excerpt_pin=(Pin (Join-Path $out ($job+'.api_excerpts.txt')));evidence_pins=@($evidence[$job]|ForEach-Object{Pin $_});source_chars_max=32000;tests_chars_max=16000;http_seconds=2400;outer_seconds=2430;native_children_actual=0;launch_authorized=$false}
}
$packet=@{utc=[DateTime]::UtcNow.ToString('o');status='PREPARATION_ONLY_PENDING_ROOT_EXACT_ADMISSION';scope='SOURCE_ONLY_NO_CANDIDATE_IMPORT_COMPILE_EXECUTION_OR_PROMOTION';jobs=$jobs;header_pin=(Pin $header);helpers=@(Get-ChildItem -LiteralPath $out -File|Where-Object{$_.Name -match '\.ps1$|PURE_LIMIT'}|ForEach-Object{Pin $_.FullName});raw_stream_cap_bytes=16777216;normalized_reasoning_and_content_each=2097152;dedicated_token_plan_guard=$true;credits_from_tokens=$false}
WriteNew 'COMPILER_TWO_ROOT_REVIEW_PACKET.json' ($packet|ConvertTo-Json -Depth 30)
$jobs|ForEach-Object{[pscustomobject]@{job=$_.job;prompt_sha256=$_.prompt_pin.sha256;prompt_bytes=$_.prompt_pin.bytes}}
Pin (Join-Path $out 'COMPILER_TWO_ROOT_REVIEW_PACKET.json')|ConvertTo-Json
