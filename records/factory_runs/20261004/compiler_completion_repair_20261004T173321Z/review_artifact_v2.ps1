function Assert-StrictReviewArtifact($Artifact){
 if($Artifact-isnot[pscustomobject]-or(@($Artifact.PSObject.Properties.Name|Sort-Object)-join',')-cne'findings,safety_checks,verdict'){throw 'review keys mismatch'}
 if($Artifact.verdict-isnot[string]-or[string]::IsNullOrWhiteSpace($Artifact.verdict)-or$Artifact.verdict.Length-gt128){throw 'review verdict invalid'}
 if($Artifact.findings-isnot[array]-or$Artifact.findings.Count-gt32){throw 'review findings invalid'}
 foreach($f in $Artifact.findings){
  if($f-isnot[pscustomobject]-or(@($f.PSObject.Properties.Name|Sort-Object)-join',')-cne'exact_source,minimal_fix,reason,region'){throw 'review finding keys mismatch'}
  foreach($n in @('region','exact_source','reason','minimal_fix')){if($f.$n-isnot[string]-or[string]::IsNullOrWhiteSpace($f.$n)-or$f.$n.Length-gt16384){throw 'review finding string invalid'}}
 }
 if($Artifact.safety_checks-isnot[array]-or$Artifact.safety_checks.Count-lt1-or$Artifact.safety_checks.Count-gt32){throw 'review safety checks invalid'}
 foreach($v in $Artifact.safety_checks){if($v-isnot[string]-or[string]::IsNullOrWhiteSpace($v)-or$v.Length-gt8192){throw 'review safety string invalid'}}
}
function Get-StrictReviewFromCli($Outer){
 if($Outer-isnot[pscustomobject]){throw 'CLI outer response not object'}
 if($null-ne$Outer.structured_output){
  $artifact=$Outer.structured_output;$source='structured_output'
 }else{
  if($Outer.response-isnot[string]){throw 'strict JSON response string required'}
  $artifact=Read-StrictJson $Outer.response;$source='response_strict_json'
 }
 Assert-StrictReviewArtifact $artifact
 return @{artifact=$artifact;source=$source}
}
