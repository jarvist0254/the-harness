param([string]$Job,[string]$Model,[string]$Artifact)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Job
New-Item -ItemType Directory -Path $root -ErrorAction Stop|Out-Null
$prompt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot ($Job+'.prompt.txt'))
foreach($name in @('03_EXPERIMENT_RUNBOOK.snapshot.md','04_PYRE_INTEGRATION.snapshot.md','repositories.snapshot.json')){$prompt+="`nSOURCE $name`n"+(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot $name))}
if($Job -eq 'llama_spec'){$prompt+="`nPinned test-backend-ops.cpp actual usage source`n"+(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'backend_ops_usage.snapshot.txt'));$prompt+="`nPinned upstream docs/multi-gpu.md`n"+(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'multi_gpu.snapshot.md'))}
if($Job -eq 'freecad'){foreach($name in @('01_HARNESS_MASTER.snapshot.md','measurements_template.snapshot.json','layout_3plus1_concept.snapshot.svg')){$prompt+="`nSOURCE $name`n"+(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot $name))}}
if($Job -eq 'llama_logits'){foreach($name in @('llama_api.snapshot.h','ggml_backend_api.snapshot.h')){$prompt+="`nEXACT API HEADER $name`n"+(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot $name))}}
$settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
$m=$settings.modelProviders.openai|Where-Object id -eq $Model|Select-Object -First 1
if(!$m){throw 'exact model not configured'}
$key=$settings.env.($m.envKey);if(!$key){throw 'credential unavailable'}
$outputCap=12000;if($Job -eq 'llama_logits'){$outputCap=16000}
$body=@{model=$Model;messages=@(@{role='user';content=$prompt});max_tokens=$outputCap;temperature=0.1;stream=$false;enable_thinking=$false}|ConvertTo-Json -Depth 8
$body|Set-Content -LiteralPath (Join-Path $root 'request_body.json') -Encoding utf8
@{model=$Model;credential_present=$true;credential_saved=$false;native_children_actual=0;native_max_authorized=10;http_deadline_seconds=240;pid=$PID}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'request_metadata.json')
$client=[Net.Http.HttpClient]::new();$client.Timeout=[TimeSpan]::FromSeconds(240)
$client.DefaultRequestHeaders.Authorization=[Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$key)
$clock=[Diagnostics.Stopwatch]::StartNew();$state='ERROR';$beat=0
try{
 $task=$client.PostAsync($m.baseUrl.TrimEnd('/')+'/chat/completions',[Net.Http.StringContent]::new($body,[Text.Encoding]::UTF8,'application/json'))
 while(!$task.IsCompleted){Start-Sleep -Milliseconds 1000;if($clock.Elapsed.TotalSeconds-$beat -ge 15){$beat=$clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($beat,1);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $root 'heartbeat.jsonl')}}
 $r=$task.GetAwaiter().GetResult();$http=[int]$r.StatusCode;$raw=$r.Content.ReadAsStringAsync().GetAwaiter().GetResult()
 $raw|Set-Content -LiteralPath (Join-Path $root 'response.json') -Encoding utf8
 if($r.IsSuccessStatusCode){$o=$raw|ConvertFrom-Json;$usage=$o.usage;$finish=$o.choices[0].finish_reason;$observed=$o.model;$answer=$o.choices[0].message.content;$answer|Set-Content -LiteralPath (Join-Path $root 'answer.txt') -Encoding utf8
  if($finish -eq 'stop'){$clean=$answer.Trim() -replace '^```json\s*','' -replace '\s*```$','';$parsed=$clean|ConvertFrom-Json;if(!$parsed.source -or !$parsed.tests){throw 'complete source/tests missing'};$parsed|ConvertTo-Json -Depth 25|Set-Content -LiteralPath (Join-Path $root 'artifact.json');$parsed.source|Set-Content -LiteralPath (Join-Path $root $Artifact) -Encoding utf8;$parsed.tests|Set-Content -LiteralPath (Join-Path $root 'tests.candidate.txt') -Encoding utf8;$state='COMPLETE_UNTRUSTED_PENDING_GATES'}else{$state='PARTIAL_NOT_ACCEPTED'}
 }else{$state='HTTP_FAILURE'}
}catch{$state='ERROR_'+$_.Exception.GetType().Name}finally{$clock.Stop();$client.Dispose();$key=$null;$settings=$null}
@{job=$Job;requested_model=$Model;observed_model=$observed;status=$state;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;pid=$PID;native_children_actual=0}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'terminal.json')
