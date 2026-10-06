$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$work=Join-Path $root 'grok_coherent_narrow';New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
$prompt=(Get-Content -Raw -LiteralPath (Join-Path $root 'grok_coherent_narrow.prompt.txt'))+"`nEXACTFUNCTIONINPUT`n"+(Get-Content -Raw -LiteralPath (Join-Path $root 'grok_targeted_function_input.json'))+"`nGEMINIACTUALREVIEW`n"+(Get-Content -Raw -LiteralPath (Join-Path $root 'gemini_coherent_review\review.json'))
$pp=Join-Path $work 'request.txt';$prompt|Set-Content -LiteralPath $pp -Encoding utf8
$cfg=Join-Path $work '.grok';New-Item -ItemType Directory -Path $cfg|Out-Null
"[mcp_servers.google_search_console]`nenabled=false`n[mcp_servers.windows-mcp]`nenabled=false`n[mcp_servers.pycharm]`nenabled=false"|Set-Content -LiteralPath (Join-Path $cfg 'config.toml')
$env:GROK_MEMORY='0';$env:GROK_SUBAGENTS='0';$env:GROK_WEB_FETCH='0';$env:GROK_AGENT_DASHBOARD='0'
$si=[Diagnostics.ProcessStartInfo]::new('C:\Users\thoma\.grok\bin\grok.exe');$si.WorkingDirectory=$work;$si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
foreach($a in @('--model','grok-4.7-build-fast','--cwd',$work,'--session-id',[Guid]::NewGuid().ToString(),'--no-subagents','--disable-web-search','--permission-mode','plan','--tools','read_file','--disallowed-tools','read_file,Agent,run_terminal_cmd,search_replace,web_search,web_fetch,task,todo_write','--verbatim','--system-prompt-override','Tool-less exact-source patch author; output complete patch JSON and actual-import tests only.','--reasoning-effort','low','--max-turns','2','--output-format','json','--prompt-file',$pp)){$si.ArgumentList.Add($a)}
$p=[Diagnostics.Process]::new();$p.StartInfo=$si;$clock=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
@{pid=$p.Id;model='grok-4.7-build-fast';source_sha256='A9E6CF0EA1390F1A2254F7BB2FA61FED22CE6817D9D48612C040669AAB1BB21E+DB4A4702EBCF7F5B2E712736D7D12E6F71752004373494B3445CB911B4B27BDA';deadline_seconds=300;credential_saved=$false;native_children_actual=0}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $work 'launch.json')
$ot=$p.StandardOutput.ReadToEndAsync();$et=$p.StandardError.ReadToEndAsync();$killed=$false
while(!$p.WaitForExit(15000)){@{seconds=[math]::Round($clock.Elapsed.TotalSeconds);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $work 'heartbeat.jsonl');if($clock.Elapsed.TotalSeconds-ge300){$p.Kill($true);$killed=$true;break}}
$p.WaitForExit();$stdout=$ot.GetAwaiter().GetResult();$stderr=$et.GetAwaiter().GetResult();$stdout|Set-Content -LiteralPath (Join-Path $work 'stdout.json');$stderr|Set-Content -LiteralPath (Join-Path $work 'stderr.txt');$state='NOT_ACCEPTED'
try{$r=$stdout|ConvertFrom-Json;$usage=$r.usage;$parsed=$r.text|ConvertFrom-Json;if(!$killed -and $p.ExitCode-eq0 -and $parsed.supervisor_replacements -and $parsed.validator_replacements -and $parsed.test_source_supervisor -and $parsed.test_source_validator){$parsed|ConvertTo-Json -Depth 35|Set-Content -LiteralPath (Join-Path $work 'patch.json');$parsed.test_source_supervisor|Set-Content -LiteralPath (Join-Path $work 'supervisor.tests.candidate.py');$parsed.test_source_validator|Set-Content -LiteralPath (Join-Path $work 'validator.tests.candidate.py');$state='COMPLETE_PATCH_UNTRUSTED'}}catch{}
@{requested_model='grok-4.7-build-fast';status=$state;pid=$p.Id;exit_code=$p.ExitCode;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);outer_killed=$killed;usage=$usage;model_usage=$r.modelUsage;stop_reason=$r.stopReason;vendor_reported_cost_usd=$r.total_cost_usd}|ConvertTo-Json -Depth 15|Set-Content -LiteralPath (Join-Path $work 'terminal.json')


