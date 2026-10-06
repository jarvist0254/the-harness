param([Parameter(Mandatory)][string]$Job,[Parameter(Mandatory)][string]$AdmissionPath,[Parameter(Mandatory)][string]$SourcePath,[Parameter(Mandatory)][string]$SourceSha256,[Parameter(Mandatory)][string]$PromptPath)
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'research_artifact.v2.ps1')
$a=Assert-LaunchContract 'Qwen' $Job $AdmissionPath $SourcePath $SourceSha256 $PromptPath
$work=Join-Path $PSScriptRoot $Job;New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
$clock=[Diagnostics.Stopwatch]::StartNew();$script:lastBeat=0;$lastProgress=0
$state='PRE_REQUEST';$http=$null;$usage=$null;$finish=$null;$modelObserved=$null;$parseError=$null;$done=$false;$cap=$false;$timeout=$false;$normalizedCap=$false
$client=$null;$cts=$null;$req=$null;$resp=$null;$stream=$null;$settings=$null;$key=$null
$memory=[IO.MemoryStream]::new();$content=[Text.StringBuilder]::new();$pending=[Text.StringBuilder]::new();$reasoningBytes=0;$contentBytes=0;$frames=0
function Process-SseLine([string]$line){
 if(!$line.StartsWith('data:')){return}
 $data=$line.Substring(5).TrimStart()
 if($data-ceq'[DONE]'){$script:done=$true;return}
 if([string]::IsNullOrWhiteSpace($data)){return}
 $o=Read-StrictJson $data;$script:frames++
 if($o.model-is[string]-and! [string]::IsNullOrWhiteSpace($o.model)){$script:modelObserved=$o.model}
 if($null-ne$o.usage){$script:usage=$o.usage}
 foreach($choice in @($o.choices)){
  if($null-eq$choice){continue}
  if($null-ne$choice.finish_reason){$script:finish=$choice.finish_reason}
  $d=$choice.delta
  if($null-ne$d.reasoning_content){if($d.reasoning_content-isnot[string]){throw 'reasoning delta type'};$nb=[Text.Encoding]::UTF8.GetByteCount($d.reasoning_content);if($script:reasoningBytes+$nb-gt2097152){$script:normalizedCap=$true;throw 'normalized reasoning cap'};$script:reasoningBytes+=$nb}
  if($null-ne$d.content){if($d.content-isnot[string]){throw 'content delta type'};$nb=[Text.Encoding]::UTF8.GetByteCount($d.content);if($script:contentBytes+$nb-gt2097152){$script:normalizedCap=$true;throw 'normalized content cap'};[void]$script:content.Append($d.content);$script:contentBytes+=$nb}
 }
}
try{
 $settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
 $model='qwen3.8-max';$matches=@($settings.modelProviders.openai|Where-Object{$_.id-ceq$model});if($matches.Count-ne1){throw 'configured exact model unavailable'};$m=$matches[0]
 $endpoint='https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1';if($m.baseUrl.TrimEnd('/')-cne$endpoint){throw 'endpoint mismatch'}
 $key=$settings.env.($m.envKey);if($key-isnot[string]-or[string]::IsNullOrWhiteSpace($key)){throw 'credential unavailable'}
 if(!$key.StartsWith('sk-sp-',[StringComparison]::Ordinal)){throw 'dedicated token-plan credential kind unavailable'}; $dedicatedPlanKind=$true
 $prompt=[IO.File]::ReadAllText($PromptPath);if($prompt.Contains($key)){throw 'known credential in prompt'}
 $body=@{model=$model;messages=@(@{role='user';content=$prompt});max_tokens=16384;temperature=0.1;stream=$true;stream_options=@{include_usage=$true};enable_thinking=$true;reasoning_effort='xhigh'}|ConvertTo-Json -Depth 8
 Save-NewJson (Join-Path $work 'request_metadata.json') @{model=$model;endpoint=$endpoint;source_sha256=$SourceSha256;prompt_sha256=$a.prompt_sha256;stream=$true;include_usage=$true;enable_thinking=$true;reasoning_effort='xhigh';thinking_budget_set=$false;max_reply_tokens=16384;http_deadline_seconds=2400;response_cap_bytes=16777216;normalized_reasoning_cap_bytes=2097152;normalized_content_cap_bytes=2097152;credential_saved=$false;dedicated_token_plan_key_kind_confirmed=$dedicatedPlanKind;native_children_actual=0;pid=$PID}
 [IO.File]::WriteAllText((Join-Path $work 'request_body.json'),$body,[Text.UTF8Encoding]::new($false))
 $client=[Net.Http.HttpClient]::new();$client.Timeout=[Threading.Timeout]::InfiniteTimeSpan;$cts=[Threading.CancellationTokenSource]::new(2400000)
 $req=[Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post,$endpoint+'/chat/completions');$req.Headers.Authorization=[Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$key);$req.Content=[Net.Http.StringContent]::new($body,[Text.Encoding]::UTF8,'application/json')
 $resp=Wait-Task ($client.SendAsync($req,[Net.Http.HttpCompletionOption]::ResponseHeadersRead,$cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl');$http=[int]$resp.StatusCode
 Save-NewJson (Join-Path $work 'transport_headers.json') @{http=$http;seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);content_type=[string]$resp.Content.Headers.ContentType;auth_headers_saved=$false;requested_model=$model}
 $stream=Wait-Task ($resp.Content.ReadAsStreamAsync($cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl')
 $buf=[byte[]]::new(16384);$chars=[char[]]::new(16388);$decoder=[Text.UTF8Encoding]::new($false,$true).GetDecoder()
 while($true){
  $n=Wait-Task ($stream.ReadAsync($buf,0,$buf.Length,$cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl');if($n-eq0){break}
  if($memory.Length+$n-gt16777216){$cap=$true;break};$memory.Write($buf,0,$n)
  $count=$decoder.GetChars($buf,0,$n,$chars,0,$false);[void]$pending.Append($chars,0,$count)
  while($true){$text=$pending.ToString();$at=$text.IndexOf("`n");if($at-lt0){break};$line=$text.Substring(0,$at).TrimEnd("`r");[void]$pending.Remove(0,$at+1);if($resp.IsSuccessStatusCode){Process-SseLine $line}}
  if($clock.Elapsed.TotalSeconds-$lastProgress-ge15){$lastProgress=$clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($lastProgress,2);http=$http;observed_model=$modelObserved;frames=$frames;raw_bytes=$memory.Length;reasoning_bytes=$reasoningBytes;content_bytes=$contentBytes;finish_reason=$finish;usage_known=($null-ne$usage);done=$done}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $work 'stream_progress.jsonl')}
 }
 if($resp.IsSuccessStatusCode-and$pending.Length-gt0){Process-SseLine ($pending.ToString().TrimEnd("`r"))}
 if($cap){$state='RESPONSE_CAP_REFUSED'}elseif(!$resp.IsSuccessStatusCode){$state='HTTP_FAILURE'}elseif(!$done-or$finish-cne'stop'-or$null-eq$usage){$state='INCOMPLETE_STREAM_NOT_ACCEPTED'}else{
  $answer=$content.ToString();if($answer.Contains($key)){throw 'known credential in answer'}
  [IO.File]::WriteAllText((Join-Path $work 'answer.raw.txt'),$answer,[Text.UTF8Encoding]::new($false))
  try{$artifact=Read-StrictJson $answer;Assert-ResearchArtifact $artifact;Save-NewJson (Join-Path $work 'research.pending_root_qa.json') $artifact;$state='COMPLETE_RESEARCH_STAGED_UNAPPLIED'}catch{$state='ARTIFACT_PARSE_OR_SCHEMA_ERROR';$parseError=$_.Exception.GetType().Name}
 }
}catch{
 $e=$_.Exception;while($e.InnerException){$e=$e.InnerException}
 if($normalizedCap){$state='NORMALIZED_DELTA_CAP_REFUSED'}elseif($e-is[OperationCanceledException]-or($cts-and$cts.IsCancellationRequested)){$state='HTTP_TIMEOUT_USAGE_UNKNOWN';$timeout=$true}else{$state='TRANSPORT_OR_SSE_PARSE_ERROR';$parseError=$e.GetType().Name}
}finally{
 $bytes=$memory.ToArray();$raw=[Text.Encoding]::UTF8.GetString($bytes);$secretMatch=($key-is[string]-and! [string]::IsNullOrEmpty($key)-and$raw.Contains($key))
 if(!$secretMatch){[IO.File]::WriteAllBytes((Join-Path $work 'response.raw.sse'),$bytes)}else{$state='KNOWN_CREDENTIAL_OUTPUT_REFUSED'}
 foreach($v in @($stream,$resp,$req,$cts,$client,$memory)){if($null-ne$v){$v.Dispose()}}
 $key=$null;$settings=$null;$clock.Stop()
 Save-NewJson (Join-Path $work 'terminal.json') @{requested_model='qwen3.8-max';observed_model=$modelObserved;status=$state;http=$http;finish_reason=$finish;usage=$usage;usage_known=($null-ne$usage);elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);frames=$frames;raw_bytes=$bytes.Length;reasoning_bytes=$reasoningBytes;content_bytes=$contentBytes;done=$done;timeout=$timeout;response_cap_exceeded=$cap;normalized_cap_exceeded=$normalizedCap;parse_error_type=$parseError;known_secret_match_refused=$secretMatch;pid=$PID;native_children_actual=0;credential_saved=$false;provider_patch_applied=$false}
}
