$ErrorActionPreference='Stop';$base='E:\the_harness\records\factory_runs\20261004';$out=Join-Path $base 'gemini_l0_collector_review_prep_20261004T222800Z';if(Test-Path -LiteralPath $out){throw 'immutable folder exists'};New-Item -ItemType Directory -Path $out|Out-Null
$utf=[Text.UTF8Encoding]::new($false)
function Pin($p){@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $p).Length}}
function WriteNew($n,$s){[IO.File]::WriteAllText((Join-Path $out $n),$s,$utf)}
$old=Join-Path $base 'gemini_combined_dma_prep_20261004T211555Z'
foreach($n in @('provider_common.high.v2.ps1','research_artifact.ps1','REVIEW_SCHEMA.json')){Copy-Item -LiteralPath (Join-Path $old $n) -Destination (Join-Path $out $n)}
Copy-Item -LiteralPath (Join-Path $base 'measure_gemini_native_argv_20261004T222600Z.ps1') -Destination (Join-Path $out 'measure_actual_native_commandline.ps1')
$source='E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\source.local_derivative_revision2.cpp'
$review=Join-Path $base 'muse_l0_collector_prep_20261004T220000Z\parser_revision2\run_output\parsed_review.json'
$qa='E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\ADJUDICATION.md'
$gaps=Join-Path $base 'muse_l0_collector_prep_20261004T220000Z\ROOT_ADDITIONAL_COLLECTOR_SCOPE_GAPS_20261004T220600Z.json'
$r=Get-Content -LiteralPath $review -Raw|ConvertFrom-Json;$compact=$r|ConvertTo-Json -Depth 40 -Compress
WriteNew 'muse_review.semantic_compact.json' $compact
$task=@'
Independent Gemini HIGH STATIC review of FULL exact collector source and all11 Muse findings below. No tools, file reads/writes, execution/native/GPU/compiler calls, browsing or delegation. Return only verdict,findings,safety_checks under supplied schema; advisory, never runtime approval. Original9f2635 Qwen source measured4RED; separate in-house derivative5e8c32 below moved7 actual real-header CPU-stub controls from1PASS/6FAIL to7PASS/0FAIL. That scoped success and originalRED remain; NO realIntelGPU/driver/P2P/residency evidence. Full stub/test/receipt files NOT embedded here. Review each Muse claim faithfully, separate measured/static facts from untested physical hypotheses. ROOT: UNINITIALIZED does not prove missing-driver cause. Prioritize fail-open JSON truncation, physicalGPU/root coverage, genuineerrors and tested boundedcounts. Unsupported directedP2P sentinel differs from diagonal by pair/index metadata; don't force matrix redesign automatically. INT_MIN helper risk is static potential, bounded-caller reachability unproved. Noargs and --json producing sameJSON is not a correctness bug. Exact source and all Muse semantic fields preserved, no omissions. Do not force speculative/cosmetic changes or claim capabilities/VRAM. Collector-only status never qualifies directtransport.
'@
$prompt=$task+"`nFULL EXACT SOURCE SHA5e8c32b98c1fec8fa708435fc7c039828b1ed1326fca269a0e1bb75fcd3edbd6`n"+[IO.File]::ReadAllText($source)+"`nFULL MUSE SEMANTIC JSON originalSHAf88cdad706e88a7af8fa4aad0c6d214d16ead6706a2e9ee1468e5a6092bbf5a1`n"+$compact
if($prompt.Length-gt28000){throw 'complete raw prompt exceedsnew28000guard'}
WriteNew 'gemini_l0_collector_high.prompt.txt' $prompt
$wrapper=[IO.File]::ReadAllText((Join-Path $old 'invoke_owned_combined_review.high.pending_admission.ps1'))
$dot=". (Join-Path `$PSScriptRoot 'research_artifact.ps1')"
$wrapper=$wrapper.Replace($dot,$dot+"`n. (Join-Path `$PSScriptRoot 'measure_actual_native_commandline.ps1')")
$raw='$prompt=[IO.File]::ReadAllText($PromptPath)'
$wrapper=$wrapper.Replace($raw,$raw+"`n  if(`$prompt.Length-gt28000){throw 'ROOT rawGemini prompt cap28000 exceeded'}")
$start='$p=[Diagnostics.Process]::new();'
$measure=@'
if($Lane-eq'Gemini'){
 $nativeCommandMeasurement=Measure-ActualNativeCommandLine $si
 if($nativeCommandMeasurement.including_terminating_nul_utf16_code_units-gt32000){throw 'ROOT fullyquoted nativecommand cap32000 includingNUL exceeded'}
 Save-NewJson (Join-Path $PSScriptRoot ($Job+'.actual_commandline_measurement.json')) $nativeCommandMeasurement
}
'@
if(([regex]::Matches($wrapper,[regex]::Escape($start))).Count-ne1){throw 'wrapper startspan notunique'}
$wrapper=$wrapper.Replace($start,$measure+"`n"+$start)
WriteNew 'invoke_owned_collector_review.high.raw28k.cmd32k.ps1' $wrapper
. (Join-Path $out 'measure_actual_native_commandline.ps1')
$job='gemini_l0_collector_high';$work=Join-Path $out $job;$si=[Diagnostics.ProcessStartInfo]::new();$si.FileName='C:\Users\thoma\AppData\Local\agy\bin\agy.exe';$si.WorkingDirectory=$work;$si.UseShellExecute=$false;$si.CreateNoWindow=$true
foreach($arg in @('--model','gemini-3.8-flash-high','--mode','plan','--sandbox','--new-project','--disable-slash-commands','--output-format','json','--print-timeout','210s','--json-schema',(Join-Path $out 'REVIEW_SCHEMA.json'),'--log-file',(Join-Path $work 'provider.log'),'--print',$prompt)){$si.ArgumentList.Add($arg)}
$actual=Measure-ActualNativeCommandLine $si
if($actual.including_terminating_nul_utf16_code_units-gt32000){throw 'actual fullquoted commandline exceeds32000NOlaunch'}
WriteNew 'ACTUAL_DOTNET_COMMANDLINE_MEASUREMENT.json' ($actual|ConvertTo-Json -Depth 8)
$packet=@{utc=[DateTime]::UtcNow.ToString('o');status='PREPARATION_ONLY_PENDING_ROOT_READ_ADMISSION';launch_authorized=$false;job=$job;model='gemini-3.8-flash-high';source_pin=(Pin $source);muse_original=(Pin $review);muse_complete_semantic_compact=(Pin (Join-Path $out 'muse_review.semantic_compact.json'));scoped_qa_reference=(Pin $qa);scope_gaps=(Pin $gaps);source_full_embedded=$true;muse_all11_findings_fields_embedded=$true;full_stub_and_test_files_embedded=$false;prompt=(Pin (Join-Path $out 'gemini_l0_collector_high.prompt.txt'));raw_prompt_utf16_chars=$prompt.Length;raw_prompt_cap=28000;native_command_cap_including_nul=32000;actual_measurement=$actual;measurement=(Pin (Join-Path $out 'ACTUAL_DOTNET_COMMANDLINE_MEASUREMENT.json'));helpers=@(Get-ChildItem -LiteralPath $out -File|Where-Object{$_.Extension-ceq'.ps1'-or$_.Name-ceq'REVIEW_SCHEMA.json'}|ForEach-Object{Pin $_.FullName});diffs=@('New exact model/source/prompt/outputbindings, copy frozencommon/schema/companion unchanged.','Wrapper adds dot-source of puremanaged commandline measurer.','Explicit raw28000guard afterprompt read; actualquoted32000includingNULguard beforeProcess.Start plusmeasurementreceipt.','Provider210/outer240sec,2MiBeach streams, CLI flags, auth, parse, ownedcleanup unchanged.');native_children_actual=0;source_execution=$false}
WriteNew 'GEMINI_COLLECTOR_RAW28K_CMD32K_ROOT_REVIEW_PACKET.json' ($packet|ConvertTo-Json -Depth 25)
Pin (Join-Path $out 'GEMINI_COLLECTOR_RAW28K_CMD32K_ROOT_REVIEW_PACKET.json')|ConvertTo-Json
