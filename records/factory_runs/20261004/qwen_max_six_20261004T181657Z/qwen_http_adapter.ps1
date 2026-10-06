param([Parameter(Mandatory)][string]$Job,[Parameter(Mandatory)][string]$AdmissionPath,[Parameter(Mandatory)][string]$SourcePath,[Parameter(Mandatory)][string]$SourceSha256,[Parameter(Mandatory)][string]$PromptPath)
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'adapter_artifact.ps1')
$a=Assert-LaunchContract 'Qwen' $Job $AdmissionPath $SourcePath $SourceSha256 $PromptPath
$work=Join-Path $PSScriptRoot $Job;New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
$clock=[Diagnostics.Stopwatch]::StartNew();$script:lastBeat=0;$state='PRE_REQUEST';$stage='credential';$http=$null;$usage=$null;$finish=$null;$observed=$null;$timedOut=$false;$parseError=$null;$capExceeded=$false
$client=$null;$cts=$null;$req=$null;$resp=$null;$stream=$null;$raw=$null;$settings=$null;$key=$null
try{
 # This credential read occurs only in the owned, root-admitted launched child, never during preparation.
 $settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
 $model='qwen3.8-max';$m=@($settings.modelProviders.openai|Where-Object{$_.id-ceq$model})
 if($m.Count-ne1){throw 'requested exact model not uniquely configured'}
 $m=$m[0];$endpoint='https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1'
 if($m.baseUrl.TrimEnd('/')-cne$endpoint){throw 'configured endpoint mismatch'}
 $key=$settings.env.($m.envKey);if($key-isnot[string]-or[string]::IsNullOrWhiteSpace($key)){throw 'configured credential unavailable'}
 $prompt=[IO.File]::ReadAllText($PromptPath)
 if($prompt.Contains($key)){throw 'credential present in prompt; refused'}
 $body=@{model=$model;messages=@(@{role='user';content=$prompt});max_tokens=16384;temperature=0.1;stream=$false;enable_thinking=$true;reasoning_effort='xhigh'}|ConvertTo-Json -Depth 8
 Save-NewJson (Join-Path $work 'request_metadata.json') @{requested_model=$model;endpoint=$endpoint;source_path=$SourcePath;source_sha256=$SourceSha256;prompt_sha256=(Get-FileHash -LiteralPath $PromptPath).Hash;max_reply_tokens=16384;enable_thinking=$true;reasoning_effort='xhigh';http_deadline_seconds=330;response_cap_bytes=2097152;credential_saved=$false;native_children_actual=0;max_native_authorized_qwen=10;max_native_authorized_deepseek=10;pid=$PID}
 [IO.File]::WriteAllText((Join-Path $work 'request_body.json'),$body,[Text.UTF8Encoding]::new($false))
 $stage='transport';$client=[Net.Http.HttpClient]::new();$client.Timeout=[Threading.Timeout]::InfiniteTimeSpan;$cts=[Threading.CancellationTokenSource]::new(330000)
 $req=[Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post,$endpoint+'/chat/completions');$req.Headers.Authorization=[Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$key);$req.Content=[Net.Http.StringContent]::new($body,[Text.Encoding]::UTF8,'application/json')
 $resp=Wait-Task ($client.SendAsync($req,[Net.Http.HttpCompletionOption]::ResponseHeadersRead,$cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl');$http=[int]$resp.StatusCode
 $stream=Wait-Task ($resp.Content.ReadAsStreamAsync($cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl')
 $mem=[IO.MemoryStream]::new();$buf=[byte[]]::new(16384);$limit=2097152
 try{while($true){$n=Wait-Task ($stream.ReadAsync($buf,0,$buf.Length,$cts.Token)) $clock (Join-Path $work 'heartbeat.jsonl');if($n-eq0){break};$room=$limit-[int]$mem.Length;if($n-gt$room){if($room-gt0){$mem.Write($buf,0,$room)};$capExceeded=$true;break};$mem.Write($buf,0,$n)};$bytes=$mem.ToArray()}finally{$mem.Dispose()}
 $raw=[Text.UTF8Encoding]::new($false,$true).GetString($bytes)
 if($raw.Contains($key)){throw 'known credential appeared in response; not persisted'}
 [IO.File]::WriteAllBytes((Join-Path $work 'response.raw.json'),$bytes)
 if($capExceeded){$state='RESPONSE_CAP_REFUSED_USAGE_UNKNOWN';$stage='response_cap'}
 elseif(!$resp.IsSuccessStatusCode){$state='HTTP_FAILURE';$stage='http_status'}
 else{
  $stage='response_parse';$o=Read-StrictJson $raw;$usage=$o.usage;$finish=$o.choices[0].finish_reason;$observed=$o.model;$answer=$o.choices[0].message.content
  if($answer-isnot[string]){throw 'answer not string'}
  [IO.File]::WriteAllText((Join-Path $work 'answer.raw.txt'),$answer,[Text.UTF8Encoding]::new($false))
  if($finish-cne'stop'){$state='PARTIAL_NOT_ACCEPTED'}else{
   $stage='artifact_parse';try{$artifact=Read-StrictJson $answer;Assert-AdapterArtifact $artifact;Save-NewJson (Join-Path $work 'adapter.pending_root_qa.json') $artifact;$state='COMPLETE_ADAPTER_STAGED_UNAPPLIED'}catch{$state='ARTIFACT_PARSE_OR_SCHEMA_ERROR';$parseError=$_.Exception.GetType().Name}
  }
 }
}catch{
 $e=$_.Exception;while($e.InnerException){$e=$e.InnerException}
 if($e-is[OperationCanceledException]-or($cts-and$cts.IsCancellationRequested)){$state='HTTP_TIMEOUT_USAGE_UNKNOWN';$timedOut=$true}else{$state='TRANSPORT_OR_PARSE_ERROR';$parseError=$e.GetType().Name}
}finally{
 foreach($v in @($stream,$resp,$req,$cts,$client)){if($null-ne$v){$v.Dispose()}}
 $settings=$null;$key=$null;$clock.Stop()
 Save-NewJson (Join-Path $work 'terminal.json') @{requested_model='qwen3.8-max';observed_model=$observed;status=$state;failure_stage=$stage;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;usage_known=($null-ne$usage);timeout=$timedOut;response_cap_exceeded=$capExceeded;parse_error_type=$parseError;pid=$PID;native_children_actual=0;provider_patch_applied=$false;credential_saved=$false}
}
