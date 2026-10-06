param([Parameter(Mandatory)][ValidateSet('Qwen','Gemini','Grok')][string]$Lane,[Parameter(Mandatory)][string]$Job,[Parameter(Mandatory)][string]$AdmissionPath,[Parameter(Mandatory)][string]$SourcePath,[Parameter(Mandatory)][string]$SourceSha256,[Parameter(Mandatory)][string]$PromptPath)
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'adapter_artifact.ps1')
$a=Assert-LaunchContract $Lane $Job $AdmissionPath $SourcePath $SourceSha256 $PromptPath
$models=@{Qwen='qwen3.8-max';Gemini='gemini-3.8-flash-medium';Grok='grok-4.7-build-fast'}
if($a.model-cne$models[$Lane]-or$a.prompt_sha256-cne(Get-FileHash -LiteralPath $PromptPath).Hash.ToLowerInvariant()){throw 'root-admitted model/prompt pin mismatch'}
$work=Join-Path $PSScriptRoot $Job
if(Test-Path -LiteralPath $work){throw 'immutable job folder already exists'}
$si=[Diagnostics.ProcessStartInfo]::new();$si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
if($Lane-eq'Qwen'){
 $si.FileName=(Get-Command pwsh).Source;$si.WorkingDirectory=$PSScriptRoot;$deadline=360
 foreach($arg in @('-NoProfile','-File',(Join-Path $PSScriptRoot 'qwen_http_adapter.ps1'),'-Job',$Job,'-AdmissionPath',$AdmissionPath,'-SourcePath',$SourcePath,'-SourceSha256',$SourceSha256,'-PromptPath',$PromptPath)){$si.ArgumentList.Add($arg)}
}else{
 New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null;$si.WorkingDirectory=$work
 if($Lane-eq'Gemini'){
  $si.FileName='C:\Users\thoma\AppData\Local\agy\bin\agy.exe';$deadline=240
  $prompt=[IO.File]::ReadAllText($PromptPath)
  foreach($arg in @('--model',$models[$Lane],'--mode','plan','--sandbox','--new-project','--disable-slash-commands','--output-format','json','--print-timeout','210s','--json-schema',(Join-Path $PSScriptRoot 'REVIEW_SCHEMA.json'),'--log-file',(Join-Path $work 'provider.log'),'--print',$prompt)){$si.ArgumentList.Add($arg)}
 }else{
  $si.FileName='C:\Users\thoma\.grok\bin\grok.exe';$deadline=300
  $cfg=Join-Path $work '.grok';New-Item -ItemType Directory -Path $cfg|Out-Null
  [IO.File]::WriteAllText((Join-Path $cfg 'config.toml'),"[mcp_servers.google_search_console]`nenabled=false`n[mcp_servers.windows-mcp]`nenabled=false`n[mcp_servers.pycharm]`nenabled=false")
  foreach($n in @('GROK_MEMORY','GROK_SUBAGENTS','GROK_WEB_FETCH','GROK_AGENT_DASHBOARD')){$si.Environment[$n]='0'}
  foreach($arg in @('--model',$models[$Lane],'--cwd',$work,'--session-id',[Guid]::NewGuid().ToString(),'--no-subagents','--disable-web-search','--permission-mode','plan','--tools','read_file','--disallowed-tools','read_file,Agent,run_terminal_cmd,search_replace,web_search,web_fetch,task,todo_write','--verbatim','--system-prompt-override','Tool-less compiler-only adapter source editor. Output only adapter_source,pure_tests_source,rationale,safety_checks,native_fixture_plan JSON. No tools, execution or file edits. Preserve original supervisor; adapter requests owned cleanup without claiming natural whole-tree completion.','--reasoning-effort','low','--max-turns','3','--output-format','json','--prompt-file',$PromptPath)){$si.ArgumentList.Add($arg)}
 }
}
$p=[Diagnostics.Process]::new();$p.StartInfo=$si;$clock=[Diagnostics.Stopwatch]::StartNew();$cts=[Threading.CancellationTokenSource]::new();$killed=$false;$overflow=$false;$drainUnknown=$false;$pipeError=$false;$exit=$null;$started=$false
$mem=@([IO.MemoryStream]::new(),[IO.MemoryStream]::new());$buf=@([byte[]]::new(16384),[byte[]]::new(16384));$tasks=@($null,$null);$done=@($false,$false);$streams=@($null,$null);$lastBeat=0;$exitSeen=$null
try{
 $p.Start()|Out-Null;$started=$true
 Save-NewJson (Join-Path $PSScriptRoot ($Job+'.owned_launch.json')) @{lane=$Lane;requested_model=$models[$Lane];pid=$p.Id;observed_process_start_utc=$p.StartTime.ToUniversalTime().ToString('o');source_sha256=$SourceSha256;prompt_sha256=$a.prompt_sha256;deadline_seconds=$deadline;identity='retained Process object; no PID reattach';clock='Stopwatch';native_children_actual=0;credential_read_by_outer_wrapper=$false}
 $streams=@($p.StandardOutput.BaseStream,$p.StandardError.BaseStream)
 for($i=0;$i-lt2;$i++){$tasks[$i]=$streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token)}
 while($true){
  if(!$p.HasExited-and($clock.Elapsed.TotalSeconds-ge$deadline-or$overflow)){$p.Kill($true);$killed=$true}
  for($i=0;$i-lt2;$i++){
   if($done[$i]-or!$tasks[$i].IsCompleted){continue}
   try{$n=$tasks[$i].GetAwaiter().GetResult()}catch{$pipeError=$true;$done[$i]=$true;continue}
   if($n-eq0){$done[$i]=$true;continue}
   $room=2097152-[int]$mem[$i].Length
   if($n-gt$room){if($room-gt0){$mem[$i].Write($buf[$i],0,$room)};$overflow=$true;$done[$i]=$true}else{$mem[$i].Write($buf[$i],0,$n);$tasks[$i]=$streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token)}
  }
  if($p.HasExited){if($null-eq$exitSeen){$exitSeen=$clock.Elapsed.TotalSeconds};if($done[0]-and$done[1]){break};if($clock.Elapsed.TotalSeconds-$exitSeen-ge5){$drainUnknown=$true;break}}
  if($clock.Elapsed.TotalSeconds-$lastBeat-ge15){$lastBeat=$clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($lastBeat);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $PSScriptRoot ($Job+'.owned_heartbeat.jsonl'))}
  Start-Sleep -Milliseconds 250
 }
 if($p.HasExited){$exit=$p.ExitCode}else{$drainUnknown=$true}
}catch{$drainUnknown=$true;$pipeError=$true}
finally{
 if($started-and!$p.HasExited){try{$p.Kill($true);$killed=$true;if(!$p.WaitForExit(5000)){$drainUnknown=$true}}catch{$drainUnknown=$true}}
 $cts.Cancel();foreach($s in $streams){if($s){$s.Dispose()}};$cts.Dispose()
 $stdout=[Text.Encoding]::UTF8.GetString($mem[0].ToArray());$stderr=[Text.Encoding]::UTF8.GetString($mem[1].ToArray());foreach($m in $mem){$m.Dispose()}
 # Avoid saving login URLs with userinfo or query values; such output is refused, not an accepted patch.
 $privateUrl=($stdout-match'https?://[^\s"<>]*[?@]' -or $stderr-match'https?://[^\s"<>]*[?@]')
 if($privateUrl){$stdout='REFUSED_PRIVATE_URL_OUTPUT';$stderr='REFUSED_PRIVATE_URL_OUTPUT'}
 [IO.File]::WriteAllText((Join-Path $PSScriptRoot ($Job+'.stdout.json')),$stdout,[Text.UTF8Encoding]::new($false));[IO.File]::WriteAllText((Join-Path $PSScriptRoot ($Job+'.stderr.txt')),$stderr,[Text.UTF8Encoding]::new($false))
 $state='NOT_ACCEPTED';$usage=$null;$modelUsage=$null;$finish=$null;$parseError=$null
 if($Lane-ne'Qwen'-and!$killed-and!$overflow-and!$drainUnknown-and!$pipeError-and!$privateUrl-and$exit-eq0){
  try{$r=Read-StrictJson $stdout;$usage=$r.usage;$modelUsage=$r.modelUsage
   if($Lane-eq'Gemini'){$answer=$r.response;if($answer-isnot[string]){$answer=$answer|ConvertTo-Json -Depth 40};$parsed=Read-StrictJson $answer;if($parsed.verdict-isnot[string]-or$parsed.findings-isnot[array]-or$parsed.safety_checks-isnot[array]){throw 'invalid review schema'};Save-NewJson (Join-Path $work 'review.pending_root_qa.json') $parsed;$state='COMPLETE_REVIEW_STAGED';$finish='NOT_REPORTED'}
   else{$finish=$r.stopReason;$parsed=Read-StrictJson $r.text;Assert-AdapterArtifact $parsed;Save-NewJson (Join-Path $work 'adapter.pending_root_qa.json') $parsed;$state='COMPLETE_ADAPTER_STAGED_UNAPPLIED'}
  }catch{$state='PARSE_OR_SCHEMA_ERROR';$parseError=$_.Exception.GetType().Name}
 }
 if($Lane-eq'Qwen'){$state='OWNED_CHILD_TERMINAL_CHECK_WORKER_RECEIPT'}
 if($killed){$state='OWNED_DEADLINE_OR_LOG_CAP_TERMINATION'}
 try{Save-NewJson (Join-Path $PSScriptRoot ($Job+'.owned_terminal.json')) @{lane=$Lane;requested_model=$models[$Lane];pid=if($started){$p.Id}else{$null};exit_code=$exit;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);status=$state;outer_killed=$killed;log_cap_exceeded=$overflow;pipe_error=$pipeError;drain_unknown=$drainUnknown;private_url_output_refused=$privateUrl;usage=$usage;model_usage=$modelUsage;finish_reason=$finish;parse_error_type=$parseError;native_children_actual=0;provider_patch_applied=$false;credential_saved=$false}
 }finally{$clock.Stop();$p.Dispose()}
}
