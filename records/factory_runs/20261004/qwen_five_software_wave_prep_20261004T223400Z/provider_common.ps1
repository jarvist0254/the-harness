$ErrorActionPreference='Stop'
function Save-NewJson([string]$Path,$Value){
 if(Test-Path -LiteralPath $Path){throw 'immutable output exists'}
 $text=$Value|ConvertTo-Json -Depth 40
 [IO.File]::WriteAllText($Path,$text,[Text.UTF8Encoding]::new($false))
}
function Assert-UniqueJson($Element){
 if($Element.ValueKind -eq [Text.Json.JsonValueKind]::Object){
  $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($p in $Element.EnumerateObject()){if(!$names.Add($p.Name)){throw 'duplicate JSON key'};Assert-UniqueJson $p.Value}
 }elseif($Element.ValueKind -eq [Text.Json.JsonValueKind]::Array){foreach($v in $Element.EnumerateArray()){Assert-UniqueJson $v}}
}
function Read-StrictJson([string]$Text){
 $doc=[Text.Json.JsonDocument]::Parse($Text)
 try{Assert-UniqueJson $doc.RootElement;return ($Text|ConvertFrom-Json -Depth 40)}finally{$doc.Dispose()}
}
function Assert-PatchArtifact($Artifact){
 if($Artifact -isnot [pscustomobject]){throw 'artifact not object'}
 $keys=@($Artifact.PSObject.Properties.Name|Sort-Object)
 if(($keys-join',')-ne'changes,rationale,safety_checks'){throw 'artifact keys mismatch'}
 if($Artifact.changes -isnot [array] -or $Artifact.changes.Count-ne3){throw 'exact three changed regions required'}
 foreach($c in $Artifact.changes){
  if($c-isnot[pscustomobject]-or(@($c.PSObject.Properties.Name|Sort-Object)-join',')-ne'replace,search'){throw 'change keys mismatch'}
  foreach($n in @('search','replace')){if($c.$n-isnot[string]-or[string]::IsNullOrWhiteSpace($c.$n)-or$c.$n.Length-gt32768){throw 'invalid change string'}}
 }
 foreach($n in @('rationale','safety_checks')){
  if($Artifact.$n-isnot[array]-or$Artifact.$n.Count-lt1-or$Artifact.$n.Count-gt32){throw 'invalid explanation array'}
  foreach($v in $Artifact.$n){if($v-isnot[string]-or[string]::IsNullOrWhiteSpace($v)-or$v.Length-gt8192){throw 'invalid explanation string'}}
 }
}
function Assert-LaunchContract([string]$Lane,[string]$Job,[string]$AdmissionPath,[string]$SourcePath,[string]$SourceSha256,[string]$PromptPath){
 if($Job-notmatch'^[a-z][a-z0-9_]{0,63}$'){throw 'invalid job id'}
 if($SourceSha256-notmatch'^[a-f0-9]{64}$'){throw 'invalid source pin'}
 $root=[IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')+'\'
 $prompt=[IO.Path]::GetFullPath($PromptPath)
 if(!$prompt.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw 'prompt outside isolated batch'}
 $source=[IO.Path]::GetFullPath($SourcePath)
 if(!$source.StartsWith('E:\the_harness\',[StringComparison]::OrdinalIgnoreCase)){throw 'source outside authorized harness'}
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()-ne$SourceSha256){throw 'source pin mismatch'}
 $admission=[IO.Path]::GetFullPath($AdmissionPath)
 if(!$admission.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw 'delegated launch binding outside new batch'}
 if((Get-Item -LiteralPath $admission).Length-gt131072){throw 'admission receipt oversized'}
 $a=Read-StrictJson ([IO.File]::ReadAllText($admission))
 if($a.provider_launch_authorized-isnot[bool]-or!$a.provider_launch_authorized-or$a.batch_path-ne$PSScriptRoot-or$a.job_id-ne$Job-or$a.lane-ne$Lane-or$a.source_sha256-ne$SourceSha256){throw 'root launch receipt mismatch'}
 $models=@{Qwen='qwen3.8-max';Gemini='gemini-3.8-flash-medium';Grok='grok-4.7-build-fast'}
 if($a.model-cne$models[$Lane]-or$a.prompt_sha256-cne(Get-FileHash -LiteralPath $prompt).Hash.ToLowerInvariant()-or[IO.Path]::GetFullPath($a.source_path)-cne$source){throw 'root model/source/prompt binding mismatch'}
 if((Get-Item -LiteralPath $prompt).Length-gt262144){throw 'prompt oversized'}
 return $a
}
function Wait-Task($Task,$Clock,[string]$Heartbeat){
 while(!$Task.IsCompleted){Start-Sleep -Milliseconds 250;if($Clock.Elapsed.TotalSeconds-$script:lastBeat-ge15){$script:lastBeat=$Clock.Elapsed.TotalSeconds;@{seconds=[math]::Round($script:lastBeat,2);state='waiting'}|ConvertTo-Json -Compress|Add-Content -LiteralPath $Heartbeat}}
 return $Task.GetAwaiter().GetResult()
}
