param([string]$Model,[string]$Batch)
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot $Batch
New-Item -ItemType Directory -Path $root -ErrorAction Stop|Out-Null
$homePath=Join-Path $root 'qwen_home'
New-Item -ItemType Directory -Path $homePath|Out-Null
$original=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
$entry=$original.modelProviders.openai|Where-Object id -eq $Model|Select-Object -First 1
if(!$entry){throw 'Model not configured'}
$key=$original.env.($entry.envKey)
if(!$key){throw 'Credential not configured'}
$allowed=@('agent','team_create','team_delete','list_agents','send_message','request_shutdown','task_create','task_update','task_list','task_get','task_stop')
$denied=@('read_file','grep_search','glob','list_directory','run_shell_command','write_file','edit','notebook_edit','web_fetch','web_search','skill','tool_search','save_memory','schedule_task','computer_use','ask_user_question')
$config=@{security=@{auth=@{selectedType='openai'}};model=@{name=$Model;maxSubagentDepth=1;generationConfig=@{timeout=120000;maxRetries=0;extra_body=@{enable_thinking=$false}}};modelProviders=@{openai=@($entry)};memory=@{enableManagedAutoMemory=$false;enableManagedAutoDream=$false;enableAutoSkill=$false;enableTeamMemory=$false;enableTeamMemorySync=$false};agents=@{team=@{maxTeammates=10};builtin=@{exploreModel='inherit'}};experimental=@{agentTeam=$true};permissions=@{allow=$allowed;deny=$denied};tools=@{core=$allowed;exclude=$denied};mcpServers=@{};telemetry=@{enabled=$false};context=@{fileName='NO_CONTEXT_DISABLED.md';loadFromIncludeDirectories=$false}}
$config|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $homePath 'settings.json') -Encoding utf8
$prompt=@'
You are an isolated harness review coordinator. User authorizes UP TO TEN native child agents for this batch, NOT mandatory ten. ACTUALLY use native Agent/Team tools: create a team, launch THREE distinct read_only:true named teammates with exact SAME session model, then await actual independent results and shut them down. maxSubagentDepth=1. No nested workers. No shell, filesystem reads/writes, MCP, external messages, memories, auth or jobs. All source/context is supplied below. Do not merely simulate agents or claim unverified spawns. Task scopes available (select THREE most useful independent ones): (1)Vulkan transfer-buffer implementation/barriers/memory; (2)futureCUDA capabilities/P2P read-onlycollector spec; (3)D3D12 sharedheap/fence/state review; (4)negativecontrol and bytes evidence; (5)OpenCL hostbridge review; (6)RPCfourCPUworker pipeline evidence; (7)physicaldevice alias/schema; (8)integrated 4card packing 3upright+rolledtop no tackon; (9)future percardVRAM/KVadmission spec; (10)final strict test evidence audit. Each child scope/spec: return exact source-grounded issues and minimalfixes, distinguish observed from future, no code mutation. Outputs stdout-only. No arbitrary pooledVRAM/P2P/performance claims. Four8GB hypothetical cards are NOT one32GB allocation. Host5070Ti display fifth excluded. PyRe rejects mixedbackend singlejob; actual selection supports multipleSAMEbackend devices, controllerone selecteddevice/job. OpenCL actual AMDintegrated/sharedmemory +NVIDIA dedicated hoststaging apparatus; CPUggmlRPC apparatus, NOT GPUproof. Packing one integrated print overhangallowed3upright+rolledtop, no48mmrow assumption. Return JSON {model,actual_child_ids,completed_reviews,unsupported_or_unchecked}. If tool execution blocked, report precise blocker and do not claim delegation. Include individual child model and real IDs from tool outputs. SUPPLIED SOURCE:
'@
foreach($f in @('E:\the_harness\j_link\README.md','E:\the_harness\j_link\opencl_smoke.py','E:\the_harness\j_link\rpc_four_worker_smoke.cpp','E:\the_harness\records\factory_runs\20261004\qwen_independent_work_20261004T102000\vulkan_codegen\vulkan_two_device.cpp')){if(Test-Path -LiteralPath $f){$prompt+="`nFILE $f`n"+(Get-Content -Raw -LiteralPath $f)}}
$prompt|Set-Content -LiteralPath (Join-Path $root 'prompt.txt') -Encoding utf8
$env:QWEN_HOME=$homePath
$env:QWEN_CODE_SYSTEM_SETTINGS_PATH=Join-Path $homePath 'settings.json'
$env:QWEN_CODE_ENABLE_AGENT_TEAM='1'
$env:OPENAI_API_KEY=$key
[Environment]::SetEnvironmentVariable($entry.envKey,$key,'Process')
$env:OPENAI_BASE_URL=$entry.baseUrl
$env:QWEN_CODE_DISABLE_WORKFLOWS='1'
$key=$null;$original=$null
$start=[Diagnostics.ProcessStartInfo]::new('node')
$start.WorkingDirectory=$root;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true;$start.RedirectStandardInput=$true;$start.CreateNoWindow=$true
foreach($a in @('C:\Users\thoma\.qwen\updates\npm\8f26e68d15de80a6\versions\0.24.7\node_modules\@qwen-code\qwen-code\cli.js','--bare','--safe-mode','--auth-type','openai','--model',$Model,'--advisor','off','--approval-mode','plan','--chat-recording','false','--max-subagent-depth','1','--max-wall-time','240s','--max-session-turns','16','--max-tool-calls','40','--output-format','stream-json','--system-prompt','Coordinate real source-only read-only native teammates. No tools except agent/team coordination are permitted. Never claim simulated work as execution.','--prompt','Execute the supplied isolated review batch.')){$start.ArgumentList.Add($a)}
foreach($tool in $allowed){$start.ArgumentList.Add("--core-tools=$tool");$start.ArgumentList.Add("--allowed-tools=$tool")}; foreach($tool in $denied){$start.ArgumentList.Add("--exclude-tools=$tool")};
$p=[Diagnostics.Process]::new();$p.StartInfo=$start
$clock=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
$out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync();$inputTask=$p.StandardInput.WriteAsync($prompt)
@{pid=$p.Id;model=$Model;team_cap=10;planned_children=3;wall_seconds=240;outer_seconds=270;memory=$false;tools=$allowed;credential_persisted=$false}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'launch_metadata.json')
$forced=$false;$stdinClosed=$false
while(!$p.WaitForExit(15000)){if($inputTask.IsCompleted -and !$stdinClosed){try{$inputTask.GetAwaiter().GetResult();$p.StandardInput.Close()}catch{};$stdinClosed=$true};Write-Output "$Batch PID $($p.Id) waiting $([math]::Round($clock.Elapsed.TotalSeconds))s";if($clock.Elapsed.TotalSeconds -gt 270){$p.Kill($true);$forced=$true;break}}
$p.WaitForExit();$out.GetAwaiter().GetResult()|Set-Content -LiteralPath (Join-Path $root 'stdout.jsonl') -Encoding utf8;$err.GetAwaiter().GetResult()|Set-Content -LiteralPath (Join-Path $root 'stderr.txt') -Encoding utf8
@{pid=$p.Id;model=$Model;exit_code=$p.ExitCode;elapsed_seconds=[math]::Round($clock.Elapsed.TotalSeconds,2);outer_killed=$forced}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'terminal.json')
Get-Content -LiteralPath (Join-Path $root 'terminal.json')




