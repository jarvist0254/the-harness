param([string]$Job,[string]$Model)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Job
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
$source=Get-Content -Raw -LiteralPath 'E:\the_harness\records\factory_runs\20261004\d3d12_pro_nonthinking_20261004T101008434Z\d3d12_crossadapter_buffer.cpp'
$prompt='Repair this experimental Windows C++17 D3D12 source with MINIMAL scoped changes. NO TOOLS. Return ONLY valid JSON {"source":"...","notes":["..."]}. Actual NVIDIA10de + AMD1002 smoke failed CreateCommittedResource E_INVALIDARG0x80070057. Microsoft documented committed crossadapter sharing supports ROW_MAJOR Texture2D; this is BUFFER and needs explicit shared HEAP + PLACED resource. Change ONLY shared BUFFER construction: GetResourceAllocationInfo for buffer sizing/alignment; create explicit CreateHeap with SHARED|SHARED_CROSS_ADAPTER flags using compatible default properties; CreatePlacedResource at offset0 on A; CreateSharedHandle of HEAP, OpenSharedHandle to ID3D12Heap on B then CreatePlacedResource at sameoffset/sameDESC/state on B. Check allocationinfo invalidSize, heapalignment; preserve resourceflags ALLOW_CROSS_ADAPTER, bufferROW_MAJOR. Keep sharedcrossadapter GPUfence, queueBWait, producerCOMMON release, checkedHRESULTs and bounded10secCPUwait. Fix negativecontrol: compare ORIGINAL noncorrupted pattern (remove expectedXOR), mismatch returns1 and bytes_checked actual inspected count (continue whole256KiB parity if possible). Label transport SPEC_REQUIRED_L0_NOT_MEASURED (MS crossadapter heaps systemmemory requirement, no measured heap proof), not directP2P/VRAM pooling. Include<memory> explicitly. Remove wasted placeholderCreateEvent hSharedBuffer by declaringemptyUniqueHandle. Keep realNVIDIA+AMD adapterfilter exact vendorIDs, skip if either absent exit77; do not replaceFAIL invalidcalls with unsupporteddriver claims. Do not alter queues, add services or features. Source follows:'+"`n"+$source
$settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json' | ConvertFrom-Json
$m=$settings.modelProviders.openai | Where-Object id -eq $Model | Select-Object -First 1
if(!$m){throw 'configured model missing'}
$key=$settings.env.($m.envKey)
if(!$key){throw 'configured credential absent'}
$body=@{model=$Model;messages=@(@{role='user';content=$prompt});max_tokens=8192;temperature=0.1;stream=$false;enable_thinking=$false}|ConvertTo-Json -Depth 8
$body | Set-Content -LiteralPath (Join-Path $root 'request_body.json') -Encoding utf8
@{model=$Model;timeout_seconds=180;credential_persisted=$false;tools=$false;memory=$false;pid=$PID}|ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'request_metadata.json')
$client=[System.Net.Http.HttpClient]::new();$client.Timeout=[TimeSpan]::FromSeconds(180)
$client.DefaultRequestHeaders.Authorization=[System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$key)
$clock=[Diagnostics.Stopwatch]::StartNew();$status='ERROR'
try{
$task=$client.PostAsync($m.baseUrl.TrimEnd('/')+'/chat/completions',[System.Net.Http.StringContent]::new($body,[Text.Encoding]::UTF8,'application/json'))
$beat=0
while(!$task.IsCompleted){Start-Sleep -Milliseconds 1000;if($clock.Elapsed.TotalSeconds-$beat -ge 15){$beat=$clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($beat,1);status='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $root 'heartbeats.jsonl');Write-Output "$Job waiting $([math]::Round($beat)) seconds"}}
$r=$task.GetAwaiter().GetResult();$http=[int]$r.StatusCode;$raw=$r.Content.ReadAsStringAsync().GetAwaiter().GetResult();$raw|Set-Content -LiteralPath (Join-Path $root 'response.json') -Encoding utf8
if($r.IsSuccessStatusCode){$obj=$raw|ConvertFrom-Json;$finish=$obj.choices[0].finish_reason;$observed=$obj.model;$usage=$obj.usage;$answer=$obj.choices[0].message.content;$answer|Set-Content -LiteralPath (Join-Path $root 'answer.json') -Encoding utf8;if($finish -eq 'stop'){$parsed=$answer|ConvertFrom-Json;if($Job -eq 'd3d12_review'){$parsed|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $root 'review.json')}elseif($parsed.source){$parsed.source|Set-Content -LiteralPath (Join-Path $root 'd3d12_placed_heap_correction.cpp') -Encoding utf8};$status='COMPLETE_UNVERIFIED'}else{$status='PARTIAL_NOT_ACCEPTED'}}else{$status='HTTP_FAILURE'}
}catch{$status='ERROR_'+$_.Exception.GetType().Name}finally{$clock.Stop();$client.Dispose();$key=$null;$settings=$null}
@{job=$Job;requested_model=$Model;observed_model=$observed;status=$status;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;pid=$PID}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'terminal.json')
Get-Content -LiteralPath (Join-Path $root 'terminal.json')

