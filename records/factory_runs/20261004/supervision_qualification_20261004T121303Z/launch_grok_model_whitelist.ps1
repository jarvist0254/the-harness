$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$work=Join-Path $root 'grok_model_whitelist';New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
$src=Join-Path $root 'grok_single_device\llama_logits_single_diagnostic.cpp'
$sha=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
if($sha -ne '3E5423CE5085576389083B46F32519E5005F930004E3BC3E85AEC98B7150C6EA'){throw 'source hash mismatch'}
$prompt=Get-Content -Raw -LiteralPath (Join-Path $root 'grok_model_whitelist.prompt.txt')
$prompt+=[Environment]::NewLine+'EXACT CURRENT SOURCE'+[Environment]::NewLine+(Get-Content -Raw -LiteralPath $src)
foreach($f in @('E:\the_harness\records\vulkan_llm_qualification_20261004\f32_derived_model_provenance.md','E:\the_harness\records\vulkan_llm_qualification_20261004\contextfix_default.stdout.json','E:\the_harness\records\vulkan_llm_qualification_20261004\contextfix_reverse.stdout.json','E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\include\llama.h','E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\ggml\include\ggml-backend.h')){$prompt+=[Environment]::NewLine+'SOURCE '+$f+[Environment]::NewLine+(Get-Content -Raw -LiteralPath $f)}
$pp=Join-Path $work 'request.txt';$prompt|Set-Content -LiteralPath $pp -Encoding utf8

$cfg=Join-Path $work '.grok';New-Item -ItemType Directory -Path $cfg|Out-Null
"[mcp_servers.google_search_console]`nenabled=false`n[mcp_servers.windows-mcp]`nenabled=false`n[mcp_servers.pycharm]`nenabled=false"|Set-Content -LiteralPath (Join-Path $cfg 'config.toml')
$env:GROK_MEMORY='0';$env:GROK_SUBAGENTS='0';$env:GROK_WEB_FETCH='0';$env:GROK_AGENT_DASHBOARD='0'
$si=[Diagnostics.ProcessStartInfo]::new('C:\Users\thoma\.grok\bin\grok.exe');$si.WorkingDirectory=$work;$si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
foreach($a in @('--model','grok-4.7-build-fast','--cwd',$work,'--session-id',[Guid]::NewGuid().ToString(),'--no-subagents','--disable-web-search','--permission-mode','plan','--tools','read_file','--disallowed-tools','read_file,Agent,run_terminal_cmd,search_replace,web_search,web_fetch,task,todo_write','--verbatim','--system-prompt-override','Tool-less exact-source patch author; output complete patch JSON and actual-import tests only.','--reasoning-effort','low','--max-turns','2','--output-format','json','--prompt-file',$pp)){$si.ArgumentList.Add($a)}
$p=[Diagnostics.Process]::new();$p.StartInfo=$si;$clock=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
@{pid=$p.Id;model='grok-4.7-build-fast';source_sha256=$sha;deadline_seconds=300;credential_saved=$false;native_children_actual=0}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $work 'launch.json')
$ot=$p.StandardOutput.ReadToEndAsync();$et=$p.StandardError.ReadToEndAsync();$killed=$false
while(!$p.WaitForExit(15000)){@{seconds=[math]::Round($clock.Elapsed.TotalSeconds);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $work 'heartbeat.jsonl');if($clock.Elapsed.TotalSeconds-ge300){$p.Kill($true);$killed=$true;break}}
$p.WaitForExit();$stdout=$ot.GetAwaiter().GetResult();$stderr=$et.GetAwaiter().GetResult();$stdout|Set-Content -LiteralPath (Join-Path $work 'stdout.json');$stderr|Set-Content -LiteralPath (Join-Path $work 'stderr.txt');$state='NOT_ACCEPTED'
try{$r=$stdout|ConvertFrom-Json;$usage=$r.usage;$parsed=$r.text|ConvertFrom-Json;if(!$killed -and $p.ExitCode-eq0 -and ($null-ne$parsed.replacements -or $parsed.source) -and $parsed.test_source){$parsed|ConvertTo-Json -Depth 25|Set-Content -LiteralPath (Join-Path $work 'patch.json');$parsed.test_source|Set-Content -LiteralPath (Join-Path $work 'model_whitelist_selftest.candidate.cpp');$state='COMPLETE_PATCH_UNTRUSTED'}}catch{}
@{requested_model='grok-4.7-build-fast';status=$state;pid=$p.Id;exit_code=$p.ExitCode;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);outer_killed=$killed;usage=$usage;model_usage=$r.modelUsage;stop_reason=$r.stopReason;vendor_reported_cost_usd=$r.total_cost_usd}|ConvertTo-Json -Depth 15|Set-Content -LiteralPath (Join-Path $work 'terminal.json')


