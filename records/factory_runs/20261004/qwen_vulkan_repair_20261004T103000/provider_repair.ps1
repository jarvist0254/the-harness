param([string]$Job,[string]$Model)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Job
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
$source=Get-Content -Raw -LiteralPath 'E:\the_harness\records\factory_runs\20261004\qwen_independent_work_20261004T102000\vulkan_codegen\vulkan_two_device.cpp'
$prompt='Repair this UNEXECUTED experimental C++17 Vulkan source after real staticgate. Return ONLY completeJSON {"source":"...","notes":["..."]}; NO TOOLS. Under500lines, fullcomplete noellipsis. Verified Khronos Vulkan-Headersv1.4.321 include E:\the_harness\records\vendor_headers\vulkan_1.4.321\include; WindowsSystem32vulkan-1.dll actual loader. Localimportlibderiveauthorized so linkvulkan-1.lib normalimports valid. EXACT fixes: vkGetPhysicalDeviceGroupProperties does NOT exist; use VkPhysicalDeviceGroupProperties STRUCT plus vkEnumeratePhysicalDeviceGroups(VkInstance,uint32_t*,VkPhysicalDeviceGroupProperties*) and initialize sType for each struct. Missing<functional>; lambdaneeds devscapture, avoid lambda entirely ifeasier. Select actualvendor10deNVIDIA and1002AMD physicaldevices, skip77 ifmissing; reportdeviceIDs/names andheaps; AMD mayintegrated/shared hostmemory mustneverinferdedicated8GB. Bupload mustmemcpy REAL A mappedreadback bytes, NOT refill CPUreferencePATTERN. A vkCmdFillBuffer->Acopy requires explicitTRANSFER_WRITEtoTRANSFER_READ bufferbarrier srcstage/dststageTRANSFER; ALLVkBufferMemoryBarrier src/dstQueueFamilyIndex VK_QUEUE_FAMILY_IGNORED forsinglequeueperdevice. Addcorrect B transfercopy/readback barriers. TwoSEPARATElogicaldevices, explicitHOST_STAGED_NOT_P2P. Buffer256KiB, fullparity against original0x4a17c0de acrossall65536words, negative --inject-corruption mutates BfinalreadbackthencompareORIGINALexpected andexit1; actualbyteschecked/mismatchcount. Fences bounded10sec vkWaitForFences; return3onTIMEOUT,2onAPIerror,0PASS. Noncoherent flush/invalidate safealignedwholealloc VK_WHOLE_SIZE; mappings offset0fullallocatedsize whenusingWHOLE. RAIIcleanup evenexception. CheckVkResult. No hardwareexecutionclaim/noP2P/noVRAMpooling. Preserve unsupported/partial factual boundaries. Source follows:'+"`n"+$source
$settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json' | ConvertFrom-Json
$m=$settings.modelProviders.openai | Where-Object id -eq $Model | Select-Object -First 1
if(!$m){throw 'configured model missing'}
$key=$settings.env.($m.envKey)
if(!$key){throw 'configured credential absent'}
$body=@{model=$Model;messages=@(@{role='user';content=$prompt});max_tokens=12000;temperature=0.1;stream=$false;enable_thinking=$false}|ConvertTo-Json -Depth 8
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
if($r.IsSuccessStatusCode){$obj=$raw|ConvertFrom-Json;$finish=$obj.choices[0].finish_reason;$observed=$obj.model;$usage=$obj.usage;$answer=$obj.choices[0].message.content;$answer|Set-Content -LiteralPath (Join-Path $root 'answer.json') -Encoding utf8;if($finish -eq 'stop'){$parsed=$answer|ConvertFrom-Json;if($Job -eq 'd3d12_review'){$parsed|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $root 'review.json')}elseif($parsed.source){$parsed.source|Set-Content -LiteralPath (Join-Path $root 'vulkan_two_device_correction.cpp') -Encoding utf8};$status='COMPLETE_UNVERIFIED'}else{$status='PARTIAL_NOT_ACCEPTED'}}else{$status='HTTP_FAILURE'}
}catch{$status='ERROR_'+$_.Exception.GetType().Name}finally{$clock.Stop();$client.Dispose();$key=$null;$settings=$null}
@{job=$Job;requested_model=$Model;observed_model=$observed;status=$status;http=$http;finish_reason=$finish;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);usage=$usage;pid=$PID}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'terminal.json')
Get-Content -LiteralPath (Join-Path $root 'terminal.json')

