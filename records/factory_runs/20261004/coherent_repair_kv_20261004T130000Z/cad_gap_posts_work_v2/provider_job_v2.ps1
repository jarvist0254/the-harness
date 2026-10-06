param([string]$Job,[string]$Model,[string]$Artifact)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Job;New-Item -ItemType Directory -Path $root -ErrorAction Stop|Out-Null
$prompt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot ($Job+'.prompt.txt'))
$s=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
$m=$s.modelProviders.openai|Where-Object { $_.id -eq $Model }|Select-Object -First 1;if(!$m){throw 'model unavailable'};$key=$s.env.($m.envKey);if(!$key){throw 'credential unavailable'}
$body=@{model=$Model;messages=@(@{role='user';content=$prompt});max_tokens=12000;temperature=0.1;stream=$false;enable_thinking=$false}|ConvertTo-Json -Depth 8
$body|Set-Content -LiteralPath (Join-Path $root 'request_body.json') -Encoding utf8
@{model=$Model;credential_saved=$false;http_deadline_seconds=240;native_children=0;max_native_authorized_qwen=10;max_native_authorized_deepseek=10;pid=$PID}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'request_metadata.json')
$client=[Net.Http.HttpClient]::new();$client.Timeout=[TimeSpan]::FromSeconds(240);$client.DefaultRequestHeaders.Authorization=[Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$key)
$clock=[Diagnostics.Stopwatch]::StartNew();$state='ERROR';$beat=0
try{$task=$client.PostAsync($m.baseUrl.TrimEnd('/')+'/chat/completions',[Net.Http.StringContent]::new($body,[Text.Encoding]::UTF8,'application/json'))
 while(!$task.IsCompleted){Start-Sleep -Milliseconds 1000;if($clock.Elapsed.TotalSeconds-$beat-ge15){$beat=$clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($beat,1);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $root 'heartbeat.jsonl')}}
 $r=$task.GetAwaiter().GetResult();$http=[int]$r.StatusCode;$raw=$r.Content.ReadAsStringAsync().GetAwaiter().GetResult();if($raw.Length-gt2097152){throw 'response budget exceeded'};$raw|Set-Content -LiteralPath (Join-Path $root 'response.json') -Encoding utf8
 if($r.IsSuccessStatusCode){$o=$raw|ConvertFrom-Json;$usage=$o.usage;$finish=$o.choices[0].finish_reason;$observed=$o.model;$answer=$o.choices[0].message.content;$answer|Set-Content -LiteralPath (Join-Path $root 'answer.txt') -Encoding utf8
 if($finish-eq'stop'){$clean=$answer.Trim()-replace'^```json\s*',''-replace'\s*```$','';$p=$clean|ConvertFrom-Json;if(!$p.source-or!$p.tests){throw 'source/tests missing'};$p|ConvertTo-Json -Depth 25|Set-Content -LiteralPath (Join-Path $root 'artifact.json');$p.source|Set-Content -LiteralPath (Join-Path $root $Artifact) -Encoding utf8;$p.tests|Set-Content -LiteralPath (Join-Path $root 'tests.candidate.py') -Encoding utf8;$state='COMPLETE_UNTRUSTED_PENDING_ROOT_ADMISSION'}else{$state='PARTIAL_NOT_ACCEPTED'}}else{$state='HTTP_FAILURE'}
}catch{$state='ERROR_'+$_.Exception.GetType().Name}finally{$clock.Stop();$client.Dispose();$s=$null;$key=$null}
@{requested_model=$Model;observed_model=$observed;status=$state;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;pid=$PID;native_children=0}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $root 'terminal.json')

