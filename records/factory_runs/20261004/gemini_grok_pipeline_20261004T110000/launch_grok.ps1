$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if(!(Test-Path -LiteralPath (Join-Path $root 'gemini_review.json'))){throw 'Gemini review incomplete; stop'}
$snapshot=Join-Path $root 'opencl_executor.snapshot.py'
$sha=(Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash
if($sha -ne '765B2BE5E976DFB6709F3D0E7754F71696E2B9287CC87120A767E8820F69DF94'){throw 'Snapshot changed'}
$configDir=Join-Path $root '.grok';New-Item -ItemType Directory -Path $configDir -Force|Out-Null
@'
[mcp_servers.google_search_console]
enabled = false
[mcp_servers.windows-mcp]
enabled = false
[mcp_servers.pycharm]
enabled = false
'@|Set-Content -LiteralPath (Join-Path $configDir 'config.toml') -Encoding utf8
$prompt=@'
You are Grok EDIT lane after completed substantive Gemini review in an isolated harness factory pipeline. Author a REAL SMALL TESTABLE code patch; do NOT execute tools or edit files yourself. Return ONLY JSON {"replacements":[{"old":"EXACT source substring","new":"replacement"}],"test_source":"complete GPU-free unittest Python tests","notes":["..."]}. No broad rewrite, no placeholders, no cosmetic edits. User explicitly authorizes this provider coding job. No subagents, memories, auth changes, shell, MCP, secrets, network tools, queues, PyRe/product edits. Original source SHA765B2BE5E976DFB6709F3D0E7754F71696E2B9287CC87120A767E8820F69DF94. Gemini actual verdict/findings and exact immutable source appended below. Source owner will apply patch after review and run tests/hardware controls; do NOT claim execution.

PATCH ONLY TWO concrete defects:
1. Source enumeration failure to query device.max_mem_alloc_size stores0; both _check_device_memory and _execute_gpu currently skip guard when maximum0. Unknown/nonpositive/noninteger/bool maximum must raise RuntimeUnavailable (NOT_CHECKED exit2 via existing exception handling) BEFORE Context/Buffer allocation, never silently allocate. Keep real runtime allocation errors FAIL, not blanketUNSUPPORTED. Known positive maximum below largest W/b/activation buffer must refuse; positive sufficient maximum succeeds. Centralize tiny pure helper if useful, then minimal replacements both existing guarded paths. Do not confuse policycap with reportedphysicalfree memory. No default invented max.
2. Gemini source-confirmed corruption picks first device boundary instead of first VENDOR boundary, wrong for NV,NV,AMD. Resolve vendor from config devices metadata/vendor_key; choose first i where layer_owner[i] vendor differs layer_owner[i+1] vendor. If --inject-corruption and no vendor boundary, RuntimeRefused exit2. Introduce a tiny pure helper to permit GPU-free tests if necessary. Preserve actual activation injection after sourceGPUreadback BEFORE destinationupload, all remaining actual kernels, independentoriginalCPUreference, bounded60second child supervision.

Do NOT apply Gemini's suggested missingNVIDIA domain fallback0: inventing domain0 can merge distinctdevices and violate identityguard. PCI identity remains conservative until independently qualified. No single-device label or unrelated redesign in this patch.

Tests complete standalone GPU-free unittest module importing from j_link.opencl_executor (parentwilladapt test path), using prepare_plan for synthetic dictdevice fixtures or mocks. Test unknown max=0/None/bool/negative (RuntimeUnavailable before native allocator), known toosmall maximum rejects, validmax returns allocationrecords and proper largestbound. Test first-vendor-boundary NV,NV,AMD selects boundary aftersecondNV, reverse AMD,NV,NV selectsfirstAMD-toNV, homogeneousvendor givesNone/refusal wheninject. NoNumPy/PyOpenCL imports; noGPU jobs. Exact oldstrings mustmatchsource below. In-orderOpenCLqueues order commands correctly; do not add spurious waits/races. Planner block-name mapping is correct. All output source intended compile-test gate only.
'@
$prompt+="`nCOMPLETED GEMINI REVIEW:`n"+(Get-Content -Raw -LiteralPath (Join-Path $root 'gemini_review.json'))+"`nEXACT SOURCE:`n"+(Get-Content -Raw -LiteralPath $snapshot)
$promptPath=Join-Path $root 'grok_request.txt';$prompt|Set-Content -LiteralPath $promptPath -Encoding utf8
$schema=@{type='object';properties=@{replacements=@{type='array';items=@{type='object';properties=@{old=@{type='string'};new=@{type='string'}};required=@('old','new')}};test_source=@{type='string'};notes=@{type='array';items=@{type='string'}}};required=@('replacements','test_source','notes')}|ConvertTo-Json -Depth 10 -Compress
$env:GROK_MEMORY='0';$env:GROK_SUBAGENTS='0';$env:GROK_WEB_FETCH='0';$env:GROK_AGENT_DASHBOARD='0'
$start=[Diagnostics.ProcessStartInfo]::new('C:\Users\thoma\.grok\bin\grok.exe')
$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
foreach($a in @('--model','grok-4.7','--cwd',$root,'--session-id',[Guid]::NewGuid().ToString(),'--no-subagents','--disable-web-search','--permission-mode','plan','--tools','read_file','--disallowed-tools','read_file,Agent,run_terminal_cmd,search_replace,web_search,web_fetch,task,todo_write','--verbatim','--system-prompt-override','You are a tool-less code patch author. Use supplied source and completed Gemini findings. Output only complete exact patch JSON; never claim tests or agent execution.','--reasoning-effort','medium','--max-turns','2','--output-format','json','--json-schema',$schema,'--prompt-file',$promptPath)){$start.ArgumentList.Add($a)}
$p=[Diagnostics.Process]::new();$p.StartInfo=$start;$clock=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
@{model='grok-4.7';executable=$start.FileName;pid=$p.Id;source_sha256=$sha;outer_deadline_seconds=240;mode='plan';tools_effectively_empty=$true;memory=$false;subagents=$false;credential_persisted=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'grok_launch.json')
$out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync();$killed=$false
while(!$p.WaitForExit(15000)){Write-Output "Grok edit PID $($p.Id) waiting $([math]::Round($clock.Elapsed.TotalSeconds))s";if($clock.Elapsed.TotalSeconds -ge 240){$p.Kill($true);$killed=$true;break}}
$p.WaitForExit();$stdout=$out.GetAwaiter().GetResult();$stderr=$err.GetAwaiter().GetResult();$stdout|Set-Content -LiteralPath (Join-Path $root 'grok_stdout.json') -Encoding utf8;$stderr|Set-Content -LiteralPath (Join-Path $root 'grok_stderr.txt') -Encoding utf8
$state='NOT_ACCEPTED';$usage=$null
try{$r=$stdout|ConvertFrom-Json;$usage=$r.usage;$answer=$r.response;if(!$answer){$answer=$r.result};if(!$answer -and $r.replacements){$answer=$r|ConvertTo-Json -Depth 20};if(!$killed -and $p.ExitCode -eq 0){if($answer -isnot [string]){$answer=$answer|ConvertTo-Json -Depth 20};$answer|Set-Content -LiteralPath (Join-Path $root 'grok_answer.json');$parsed=$answer|ConvertFrom-Json;if($null -ne $parsed.replacements -and $parsed.test_source){$parsed|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $root 'grok_patch.json');$parsed.test_source|Set-Content -LiteralPath (Join-Path $root 'grok_patch_tests.py');$state='COMPLETE_PATCH_UNADJUDICATED'}}}catch{}
@{model='grok-4.7';pid=$p.Id;exit_code=$p.ExitCode;seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);outer_killed=$killed;state=$state;usage=$usage}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'grok_terminal.json')
Get-Content -LiteralPath (Join-Path $root 'grok_terminal.json')
