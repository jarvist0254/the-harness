param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=$PSScriptRoot
$exe='C:\Users\thoma\.grok\bin\grok.exe'
$promptPath=Join-Path $root 'grok_prompt.txt'
$manifestPath=Join-Path $root 'inputs.json'
$promptHash='20C46ABB2ECD817BDF5195F960079D670864F0D0778092FD030830955E84747D'
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if((Get-FileHash -LiteralPath $promptPath -Algorithm SHA256).Hash.ToUpperInvariant() -ne $promptHash){throw 'prompt pin mismatch'}
if((Get-Item -LiteralPath $promptPath).Length -gt 262144){throw 'prompt exceeds 256 KiB'}
if(!(Test-Path -LiteralPath $exe -PathType Leaf)){throw 'pinned Grok executable missing'}
$exeHash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToUpperInvariant()
$before=[ordered]@{}
foreach($item in $manifest.PSObject.Properties){
 $path=[string]$item.Value.original
 $expected=[string]$item.Value.sha256
 if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "input missing: $($item.Name)"}
 $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant()
 if($actual -ne $expected){throw "input changed: $($item.Name)"}
 $before[$path]=$actual
}
$admission=[ordered]@{authority='ROOT-delegated isolated source-only Grok corrective review; do not apply edits';lane='Grok';model='grok-4.7-build-fast';reasoning_effort='high';candidate_sha256=($manifest.candidate.sha256);prompt_sha256=$promptHash;grok_binary_sha256=$exeHash;source_execution=$false;provider_edit=$false;limits=@{deadline_seconds=300;per_stream_cap_bytes=2097152;prompt_cap_bytes=262144};inputs=$before;tools='read_file explicitly disallowed; no subagents/web/terminal/write tools requested'}
[IO.File]::WriteAllText((Join-Path $root 'ROOT_GROK_REVIEW_ADMISSION.json'),($admission|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
$psi=[Diagnostics.ProcessStartInfo]::new();$psi.FileName=$exe;$psi.WorkingDirectory=$root;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
$session=[Guid]::NewGuid().ToString()
$args=@('--model','grok-4.7-build-fast','--cwd',$root,'--session-id',$session,'--no-subagents','--disable-web-search','--permission-mode','plan','--tools','read_file','--disallowed-tools','read_file,Agent,run_terminal_cmd,search_replace,web_search,web_fetch,task,todo_write','--verbatim','--system-prompt-override','Read-only corrective audit. Do not use tools, shell, file access, execution, network, edits, subagents, or external messages. All source is embedded. Return the requested exact JSON only. Propose zero edits if no concrete end-to-end defect exists.','--reasoning-effort','high','--max-turns','4','--output-format','json','--prompt-file',$promptPath)
foreach($a in $args){[void]$psi.ArgumentList.Add($a)}
$p=[Diagnostics.Process]::new();$p.StartInfo=$psi;$sw=[Diagnostics.Stopwatch]::StartNew();$cts=[Threading.CancellationTokenSource]::new();$mem=@([IO.MemoryStream]::new(),[IO.MemoryStream]::new());$buf=@([byte[]]::new(16384),[byte[]]::new(16384));$tasks=@($null,$null);$streams=@();$done=@($false,$false);$started=$false;$killed=$false;$overflow=$false;$drainUnknown=$false;$pipeError=$false;$exit=$null;$lastBeat=0.0;$state='NOT_ACCEPTED';$parseError=$null;$usage='UNKNOWN';$modelUsage='UNKNOWN';$finish='UNKNOWN'
try{
 [void]$p.Start();$started=$true
 [IO.File]::WriteAllText((Join-Path $root 'grok_launch.json'),(@{model='grok-4.7-build-fast';reasoning_effort='high';pid=$p.Id;session_id=$session;start_utc=$p.StartTime.ToUniversalTime().ToString('o');candidate_sha256=$manifest.candidate.sha256;prompt_sha256=$promptHash;grok_binary_sha256=$exeHash;deadline_seconds=300;per_stream_cap_bytes=2097152;source_execution=$false;provider_edit=$false}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
 $streams=@($p.StandardOutput.BaseStream,$p.StandardError.BaseStream)
 for($i=0;$i-lt2;$i++){$tasks[$i]=$streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token)}
 while($true){
  if(!$p.HasExited-and($sw.Elapsed.TotalSeconds-ge300-or$overflow)){$p.Kill($true);$killed=$true}
  for($i=0;$i-lt2;$i++){
   if($done[$i]-or!$tasks[$i].IsCompleted){continue}
   try{$n=$tasks[$i].GetAwaiter().GetResult()}catch{$pipeError=$true;$done[$i]=$true;continue}
   if($n-eq0){$done[$i]=$true;continue}
   $room=2097152-[int]$mem[$i].Length
   if($n-gt$room){if($room-gt0){$mem[$i].Write($buf[$i],0,$room)};$overflow=$true;$done[$i]=$true}else{$mem[$i].Write($buf[$i],0,$n);$tasks[$i]=$streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token)}
  }
  if($p.HasExited){if($done[0]-and$done[1]){break};if($sw.Elapsed.TotalSeconds-ge305){$drainUnknown=$true;break}}
  if($sw.Elapsed.TotalSeconds-$lastBeat-ge15){$lastBeat=$sw.Elapsed.TotalSeconds;@{utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=[math]::Round($lastBeat,1);pid=$p.Id;status='RUNNING';stdout_bytes=$mem[0].Length;stderr_bytes=$mem[1].Length}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $root 'grok_progress.jsonl')}
  Start-Sleep -Milliseconds 100
 }
 if($p.HasExited){$exit=$p.ExitCode}else{$drainUnknown=$true}
}catch{$pipeError=$true;$parseError=$_.Exception.GetType().Name}
finally{
 if($started-and!$p.HasExited){try{$p.Kill($true);$killed=$true;if(!$p.WaitForExit(5000)){$drainUnknown=$true}}catch{$drainUnknown=$true}}
 $cts.Cancel();foreach($s in $streams){if($s){$s.Dispose()}};$cts.Dispose()
 $stdout=[Text.Encoding]::UTF8.GetString($mem[0].ToArray());$stderr=[Text.Encoding]::UTF8.GetString($mem[1].ToArray());foreach($m in $mem){$m.Dispose()}
}
$privateUrl=($stdout-match'https?://[^\s"<>]*[?@]' -or$stderr-match'https?://[^\s"<>]*[?@]')
$stdoutBytes=[Text.Encoding]::UTF8.GetByteCount($stdout);$stderrBytes=[Text.Encoding]::UTF8.GetByteCount($stderr)
$sha=[Security.Cryptography.SHA256]::Create();$stdoutHash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($stdout))).Replace('-','');$stderrHash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($stderr))).Replace('-','');$sha.Dispose()
if($privateUrl){$stdout='REFUSED_PRIVATE_URL_OUTPUT';$stderr='REFUSED_PRIVATE_URL_OUTPUT'}
[IO.File]::WriteAllText((Join-Path $root 'grok_stdout.json'),$stdout,[Text.UTF8Encoding]::new($false));[IO.File]::WriteAllText((Join-Path $root 'grok_stderr.txt'),$stderr,[Text.UTF8Encoding]::new($false))
if(!$killed-and!$overflow-and!$drainUnknown-and!$pipeError-and!$privateUrl-and$exit-eq0){
 try{
  $outer=$stdout|ConvertFrom-Json
  $usage=if($null-ne$outer.usage){$outer.usage}else{'UNKNOWN'};$modelUsage=if($null-ne$outer.modelUsage){$outer.modelUsage}else{'UNKNOWN'};$finish=if($null-ne$outer.stopReason){$outer.stopReason}else{'UNKNOWN'}
  $payload=$outer.text;if($payload-isnot[string]){throw 'missing string result'}
  $doc=[Text.Json.JsonDocument]::Parse($payload)
  function Check-Unique($element){if($element.ValueKind-eq[Text.Json.JsonValueKind]::Object){$names=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);foreach($prop in $element.EnumerateObject()){if(!$names.Add($prop.Name)){throw 'duplicate JSON key'};Check-Unique $prop.Value}}elseif($element.ValueKind-eq[Text.Json.JsonValueKind]::Array){foreach($v in $element.EnumerateArray()){Check-Unique $v}}}
  try{Check-Unique $doc.RootElement}finally{$doc.Dispose()}
  $r=$payload|ConvertFrom-Json;$keys=@($r.PSObject.Properties.Name|Sort-Object)-join','
  if($keys-ne'adapter_changes,adapter_findings,helper_changes,helper_findings,rationale,safety_checks,tests,verdict'){throw 'result keys mismatch'}
  if($r.verdict-notin@('NO_SOURCE_CHANGES','PROPOSED_PATCHES')-or$r.adapter_changes-isnot[array]-or$r.adapter_changes.Count-gt4-or$r.helper_changes-isnot[array]-or$r.helper_changes.Count-gt3){throw 'result shape invalid'}
  foreach($patch in @($r.adapter_changes)+@($r.helper_changes)){if($patch-isnot[pscustomobject]-or(@($patch.PSObject.Properties.Name|Sort-Object)-join',')-ne'replace,search'-or[string]::IsNullOrWhiteSpace($patch.search)-or[string]::IsNullOrWhiteSpace($patch.replace)){throw 'patch shape invalid'}}
  foreach($field in @('adapter_findings','helper_findings')){if($r.$field-isnot[array]){throw "invalid $field"};foreach($f in $r.$field){if((@($f.PSObject.Properties.Name|Sort-Object)-join',')-ne'exact_source,minimal_fix,reason,region'){throw 'finding shape invalid'}}}
  foreach($field in @('tests','rationale','safety_checks')){if($r.$field-isnot[array]){throw "invalid $field"}}
  [IO.File]::WriteAllText((Join-Path $root 'grok_patch.pending_root_qa.json'),($r|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false));$state='COMPLETE_PATCH_STAGED_UNAPPLIED'
 }catch{$state='PARSE_OR_SCHEMA_ERROR';$parseError=$_.Exception.GetType().Name}
}elseif($killed){$state='OWNED_DEADLINE_OR_LOG_CAP_TERMINATION'}
$after=[ordered]@{};$unchanged=$true
foreach($item in $manifest.PSObject.Properties){$path=[string]$item.Value.original;$actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant();$after[$path]=$actual;if($actual-ne[string]$item.Value.sha256){$unchanged=$false}}
if(!$unchanged){$state='INPUT_PIN_CHANGED'}
$terminal=[ordered]@{model='grok-4.7-build-fast';reasoning_effort='high';pid=if($started){$p.Id}else{$null};exit_code=$exit;elapsed_seconds=[math]::Round($sw.Elapsed.TotalSeconds,2);status=$state;outer_killed=$killed;log_cap_exceeded=$overflow;pipe_error=$pipeError;drain_unknown=$drainUnknown;private_url_output_refused=$privateUrl;stdout_bytes=$stdoutBytes;stderr_bytes=$stderrBytes;stdout_sha256=$stdoutHash;stderr_sha256=$stderrHash;finish_reason=$finish;usage=$usage;model_usage=$modelUsage;tool_calls='UNKNOWN';subagents='UNKNOWN';inputs_unchanged=$unchanged;inputs_after=$after;provider_edit=$false;source_execution=$false;parse_error_type=$parseError}
[IO.File]::WriteAllText((Join-Path $root 'grok_terminal.json'),($terminal|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$p.Dispose();Get-Content -LiteralPath (Join-Path $root 'grok_terminal.json')
if($state-notin@('COMPLETE_PATCH_STAGED_UNAPPLIED','COMPLETE_NO_CHANGE_STAGED')){exit 2}
