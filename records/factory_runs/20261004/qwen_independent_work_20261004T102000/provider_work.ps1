param([string]$Job,[string]$Model)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Job
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
if($Job -eq 'd3d12_review'){
$source=Get-Content -Raw -LiteralPath 'E:\the_harness\records\factory_runs\20261004\d3d12_pro_nonthinking_20261004T101008434Z\d3d12_crossadapter_buffer.cpp'
$prompt='Independently review the following experimental Windows C++17 D3D12 two-adapter host/system-memory shared-crossadapter 256KiB deterministic copy smoke. NO TOOLS. Return ONLY JSON {"verdict":"accept|reject","findings":[{"severity":"critical|high|medium|low","line":1,"reason":"...","minimal_fix":"..."}],"missing_hardware_qualification":["..."]}. Focus compile failures, shared-crossadapter resource/fence compatibility, queue synchronization, bounded CPU waits, command list lifecycle, full parity, corruption exit1, correct transport/VRAM wording and receipts. Do not invent execution evidence. Known bytes_checked early-break accounting issue will be corrected; find independent issues. Include concrete API semantics, not speculation. Source follows:'+"`n"+$source
}else{
$prompt=@'
Generate a COMPACT standalone Windows C++17 Vulkan TWO-SEPARATE-DEVICE transfer smoke source. NO TOOLS. Return ONLY valid JSON {"source":"...","notes":["..."]}. Source MUST fit under 220 lines and 22000 chars: use <vulkan/vulkan.h> and Vulkan loader imports; SDK/header not found locally yet so compile is NOT_CHECKED. No shaders. Enumerate physical devices, require2 or print SKIP exit77. Report names/vendor/device IDs and local heap sizes, query/list physical-device groups for diagnostic ONLY. Create one logical device per selected physical device, each with transfer queue. A device-local256KiB buffer filled deterministic pattern via vkCmdFillBuffer(A), copy to A host-visible readback; bounded fence10s, invalidate noncoherent mapping when needed; memcpy HOST staging into B host-visible upload, flush noncoherent when needed, transfer to B device-local then B host-visible readback with bounded fence10s. Proper usage flags, barriers/stages queue ownership singlequeueperdevice, memorytype selection, checked VkResult, initial commandbuffer lifecycle. Full parity all65536 words, --inject-corruption mutates final mappedbyte then exit1; report actual bytes_checked/mismatches, transport HOST_STAGING_NOT_P2P, no pooled VRAM claims. Error exit2; timeout exit3; PASS0. RAII or explicit resource cleanup. Compact helper functions avoid huge inline boilerplate. Never call vkCreateDeviceGroup; never imply directP2P. Pattern constant0x4a17c0de sufficient deterministic. Windows console build comment cl /std:c++17 /EHsc source.cpp /I SDKinclude /link vulkan-1.lib; build prerequisites explicitly unverified.
'@
}
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
if($r.IsSuccessStatusCode){$obj=$raw|ConvertFrom-Json;$finish=$obj.choices[0].finish_reason;$observed=$obj.model;$usage=$obj.usage;$answer=$obj.choices[0].message.content;$answer|Set-Content -LiteralPath (Join-Path $root 'answer.json') -Encoding utf8;if($finish -eq 'stop'){$parsed=$answer|ConvertFrom-Json;if($Job -eq 'd3d12_review'){$parsed|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $root 'review.json')}elseif($parsed.source){$parsed.source|Set-Content -LiteralPath (Join-Path $root 'vulkan_two_device.cpp') -Encoding utf8};$status='COMPLETE_UNVERIFIED'}else{$status='PARTIAL_NOT_ACCEPTED'}}else{$status='HTTP_FAILURE'}
}catch{$status='ERROR_'+$_.Exception.GetType().Name}finally{$clock.Stop();$client.Dispose();$key=$null;$settings=$null}
@{job=$Job;requested_model=$Model;observed_model=$observed;status=$status;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;pid=$PID}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'terminal.json')
Get-Content -LiteralPath (Join-Path $root 'terminal.json')
