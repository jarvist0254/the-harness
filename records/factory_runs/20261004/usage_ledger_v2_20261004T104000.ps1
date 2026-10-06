$ErrorActionPreference='Stop'
$base=$PSScriptRoot
$dirs=[Collections.Generic.List[IO.DirectoryInfo]]::new()
foreach($d in Get-ChildItem -LiteralPath $base -Directory){$dirs.Add($d);foreach($child in Get-ChildItem -LiteralPath $d.FullName -Directory){if($child.Name -ne 'qwen_home'){$dirs.Add($child)}}}
$rows=@()
foreach($d in $dirs){
 $termPath=Join-Path $d.FullName 'terminal.json';$metaPath=Join-Path $d.FullName 'request_metadata.json'
 if(!(Test-Path -LiteralPath $termPath) -and !(Test-Path -LiteralPath $metaPath)){continue}
 $t=$null;$m=$null;$usage=$null;$observed=$null
 if(Test-Path -LiteralPath $termPath){try{$t=Get-Content -Raw -LiteralPath $termPath|ConvertFrom-Json}catch{}}
 if(Test-Path -LiteralPath $metaPath){try{$m=Get-Content -Raw -LiteralPath $metaPath|ConvertFrom-Json}catch{}}
 $usage=$t.usage;$observed=$t.observed_model
 foreach($name in @('response.json','stdout.json')){if(!$usage){$p=Join-Path $d.FullName $name;if(Test-Path -LiteralPath $p){try{$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;$usage=$r.usage;if(!$observed){$observed=$r.model}}catch{}}}}
 if(!$usage){$p=Join-Path $d.FullName 'stdout.json';if(Test-Path -LiteralPath $p){try{$events=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;foreach($event in @($events)){if($event.stats.models){$modelStats=@($event.stats.models.PSObject.Properties|ForEach-Object {$_.Value});$usage=[pscustomobject]@{prompt_tokens=($modelStats|ForEach-Object {$_.tokens.prompt}|Measure-Object -Sum).Sum;completion_tokens=($modelStats|ForEach-Object {$_.tokens.candidates}|Measure-Object -Sum).Sum;total_tokens=($modelStats|ForEach-Object {$_.tokens.total}|Measure-Object -Sum).Sum}}}}catch{}}}
 $stream=Join-Path $d.FullName 'stdout.jsonl'
 if(!$usage -and (Test-Path -LiteralPath $stream)){foreach($line in Get-Content -LiteralPath $stream){try{$r=$line|ConvertFrom-Json;if($r.type -eq 'result'){$usage=$r.usage}}catch{}}}
 $requested=$t.requested_model;if(!$requested){$requested=$t.model};if(!$requested){$requested=$m.model}
 $input=$usage.prompt_tokens;if($null -eq $input){$input=$usage.input_tokens}
 $output=$usage.completion_tokens;if($null -eq $output){$output=$usage.output_tokens}
 $state=$t.status;if(!$state){$state='TERMINAL_REQUIRES_ADJUDICATION'}
 if($t.partial_output){$state='PARTIAL_NOT_ACCEPTED'}
 if($t.expected_response_present -eq $false){$state='IDENTITY_RESPONSE_FAILED'}
 if($t.exit_code -eq 55){$state='WALL_TIMEOUT_NOT_ACCEPTED'}
 if($t.exit_code -eq -1){$state='OWNED_PROCESS_STOPPED_NO_CHILD_CLAIM'}
 if($t.exit_code -eq 1){$state='CLI_STARTUP_FAILED'}
 $seconds=$t.elapsed_seconds;if(!$seconds){$seconds=$t.seconds}
 $rows+= [pscustomobject]@{path=$d.FullName;requested_model=$requested;observed_model=$observed;state=$state;http=$t.http;exit_code=$t.exit_code;seconds=$seconds;prompt_tokens=$input;completion_tokens=$output;total_tokens=$usage.total_tokens;usage_available=($null -ne $usage);product_accepted=$false;source_artifact_unverified=(Test-Path -LiteralPath (Join-Path $d.FullName 'answer.json'))}
}
$ledger=@{generated_utc=[DateTime]::UtcNow.ToString('o');scope='isolated harness provider experiments; liveFactory unchanged';quota_units='Dashboard units/percentage cannot be equated to API token counts';observed_token_total=($rows|Measure-Object -Property total_tokens -Sum).Sum;usage_missing_rows=@($rows|Where-Object {!$_.usage_available}).Count;rows=$rows}
$out=Join-Path $base ('provider_usage_ledger_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'.json')
$ledger|ConvertTo-Json -Depth 10|Set-Content -LiteralPath $out -Encoding utf8
[pscustomobject]@{ledger=$out;rows=$rows.Count;observed_token_total=$ledger.observed_token_total;usage_missing_rows=$ledger.usage_missing_rows}|ConvertTo-Json

