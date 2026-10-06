# Strict source-string intake only; never parse/evaluate/import provider Python.
function Assert-AdapterArtifact($Artifact){
 if($Artifact-isnot[pscustomobject]){throw 'adapter artifact not object'}
 if((@($Artifact.PSObject.Properties.Name|Sort-Object)-join',')-cne'adapter_source,native_fixture_plan,pure_tests_source,rationale,safety_checks'){throw 'adapter artifact keys mismatch'}
 foreach($n in @('adapter_source','pure_tests_source')){
  if($Artifact.$n-isnot[string]-or[string]::IsNullOrWhiteSpace($Artifact.$n)-or$Artifact.$n.Length-gt131072){throw 'bounded nonempty source string required'}
 }
 foreach($n in @('rationale','safety_checks','native_fixture_plan')){
  if($Artifact.$n-isnot[array]-or$Artifact.$n.Count-lt1-or$Artifact.$n.Count-gt32){throw 'bounded explanation array required'}
  foreach($v in $Artifact.$n){if($v-isnot[string]-or[string]::IsNullOrWhiteSpace($v)-or$v.Length-gt8192){throw 'bounded nonempty explanation string required'}}
 }
}
