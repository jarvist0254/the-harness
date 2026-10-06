$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$source='E:\the_harness\j_link\opencl_executor.py'
$expected='765B2BE5E976DFB6709F3D0E7754F71696E2B9287CC87120A767E8820F69DF94'
if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $expected){throw 'Source hash changed; stop without inference'}
$snapshot=Join-Path $root 'opencl_executor.snapshot.py'
Copy-Item -LiteralPath $source -Destination $snapshot -ErrorAction Stop
$specPath=Join-Path $root 'acceptance.snapshot.md'
$spec=Get-Content -Raw -LiteralPath 'E:\the_harness\docs\06_LOCAL_AGENT_HANDOFF.md'
$spec.Substring($spec.IndexOf('## Working-executor acceptance experiment'))|Set-Content -LiteralPath $specPath -Encoding utf8
$schema=@{type='object';properties=@{verdict=@{type='string';enum=@('accept','reject')};findings=@{type='array';items=@{type='object';properties=@{severity=@{type='string'};line=@{type='integer'};exact_source=@{type='string'};reason=@{type='string'};minimal_fix=@{type='string'}};required=@('severity','line','reason','minimal_fix')}};missing_qualification=@{type='array';items=@{type='string'}}};required=@('verdict','findings','missing_qualification')}|ConvertTo-Json -Depth 12 -Compress
$schemaPath=Join-Path $root 'gemini_schema.json';$schema|Set-Content -LiteralPath $schemaPath -Encoding utf8
$prompt="Perform substantive independent CODE REVIEW now. You are Gemini review lane in an isolated harness factory pipeline, not the global factory. Use only read-only file tools to read EXACTLY '$snapshot' and '$specPath'. Do not read any other paths, secrets, memories, old task queues; no shell, edits, jobs, network/tools, installs or external messages. Source SHA256 $expected. The implementer reports26pure contract tests passed; no hardware acceptance is implied. Review actual code against spec; prioritize kernel row-major math+independentCPU reference+first vendor-boundary corruption propagating through remainingGPU layers; device identification/aliasing/defaultNVIDIA+AMD/order/reverse; resident unique weights alluploadedonce; actualactivationhoststage versusCPUrefill; ceilMiBlayerbudgets, allocationbeforeadmission; parentdeadline/nativecrash/atomicJSON<=128KiB/exitcodes; resourcecleanup andfalsePASS risks. In-orderOpenCLqueues legally order enqueuecopies/kernels; do not falsely report race just because no per-copy hostwait. Planner returns blocks names legitimately; differentiate source's adapter contract. Findings mustcite exact source lines and concrete testable minimalfix. Return ONLY JSON conforming schema. If no confirmed bug, identify a concrete missing discriminator or boundscheck worth a SMALL tested Grok patch, not cosmetic changes. No arbitrary pooledVRAM/P2P/4card/LLM/performanceclaim. Await both reads before review; no hypothetical findings. Do not merely outline a plan. Actual complete substantive verdict required."
$prompt|Set-Content -LiteralPath (Join-Path $root 'gemini_request.txt') -Encoding utf8
$start=[Diagnostics.ProcessStartInfo]::new('C:\Users\thoma\AppData\Local\agy\bin\agy.exe')
$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
foreach($a in @('--model','gemini-3.8-flash-high','--mode','plan','--sandbox','--new-project','--disable-slash-commands','--output-format','json','--print-timeout','210s','--json-schema',$schemaPath,'--log-file',(Join-Path $root 'gemini_provider.log'),'--print',$prompt)){$start.ArgumentList.Add($a)}
$p=[Diagnostics.Process]::new();$p.StartInfo=$start;$clock=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
@{model='gemini-3.8-flash-high';executable=$start.FileName;pid=$p.Id;source_sha256=$expected;provider_deadline_seconds=210;outer_deadline_seconds=240;mode='plan';sandbox=$true;credential_persisted=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'gemini_launch.json')
$out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync();$killed=$false
while(!$p.WaitForExit(15000)){Write-Output "Gemini review PID $($p.Id) waiting $([math]::Round($clock.Elapsed.TotalSeconds))s";if($clock.Elapsed.TotalSeconds -ge 240){$p.Kill($true);$killed=$true;break}}
$p.WaitForExit();$stdout=$out.GetAwaiter().GetResult();$stderr=$err.GetAwaiter().GetResult()
$stdout|Set-Content -LiteralPath (Join-Path $root 'gemini_stdout.json') -Encoding utf8;$stderr|Set-Content -LiteralPath (Join-Path $root 'gemini_stderr.txt') -Encoding utf8
$state='NOT_ACCEPTED';$usage=$null
try{$r=$stdout|ConvertFrom-Json;$usage=$r.usage;if(!$killed -and $p.ExitCode -eq 0 -and $stderr -notmatch 'partial|timed out|timeout'){ $answer=$r.response;if($answer -isnot [string]){$answer=$answer|ConvertTo-Json -Depth 15};$answer|Set-Content -LiteralPath (Join-Path $root 'gemini_answer.json');$parsed=$answer|ConvertFrom-Json;if($parsed.verdict -in @('accept','reject') -and $null -ne $parsed.findings){$parsed|ConvertTo-Json -Depth 15|Set-Content -LiteralPath (Join-Path $root 'gemini_review.json');$state='COMPLETE_REVIEW_UNADJUDICATED'}}}catch{}
@{model='gemini-3.8-flash-high';pid=$p.Id;exit_code=$p.ExitCode;seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);outer_killed=$killed;state=$state;usage=$usage}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'gemini_terminal.json')
Get-Content -LiteralPath (Join-Path $root 'gemini_terminal.json')
