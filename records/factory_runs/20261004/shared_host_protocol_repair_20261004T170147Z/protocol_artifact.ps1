# Narrow new intake only. Transport/credentials/owned deadlines remain frozen.
function Assert-ProtocolArtifact($Artifact){
 if($Artifact-isnot[pscustomobject]){throw 'protocol artifact not object'}
 if((@($Artifact.PSObject.Properties.Name|Sort-Object)-join',')-cne'changes,evidence_limits,prerequisites,protocol_argument,smoke_plan,status'){throw 'protocol artifact keys mismatch'}
 if($Artifact.status-isnot[string]-or$Artifact.status-cnotin@('PROPOSED','REFUSED')){throw 'protocol status invalid'}
 if($Artifact.protocol_argument-isnot[string]-or[string]::IsNullOrWhiteSpace($Artifact.protocol_argument)-or$Artifact.protocol_argument.Length-gt32768){throw 'protocol argument invalid'}
 if($Artifact.changes-isnot[array]-or$Artifact.changes.Count-gt8){throw 'changes array invalid'}
 if($Artifact.status-ceq'REFUSED'-and$Artifact.changes.Count-ne0){throw 'refusal must not fabricate changes'}
 if($Artifact.status-ceq'PROPOSED'-and$Artifact.changes.Count-lt1){throw 'proposal must contain a genuine minimal repair'}
 $source=Join-Path $PSScriptRoot 'source_snapshot.cpp'
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()-cne'21a0379e778bdb8c31e5da7774410b59236e2b6f72a87eaf1b68ff584a666815'){throw 'protocol source snapshot pin mismatch'}
 $text=[IO.File]::ReadAllText($source).Replace("`r`n","`n")
 $intervals=[Collections.Generic.List[object]]::new()
 foreach($c in $Artifact.changes){
  if($c-isnot[pscustomobject]-or(@($c.PSObject.Properties.Name|Sort-Object)-join',')-cne'rationale,replace,search'){throw 'protocol change keys mismatch'}
  foreach($n in @('search','replace','rationale')){if($c.$n-isnot[string]-or[string]::IsNullOrWhiteSpace($c.$n)-or$c.$n.Length-gt32768){throw 'protocol change string invalid'}}
  $search=$c.search.Replace("`r`n","`n")
  if($search-ceq$c.replace.Replace("`r`n","`n")){throw 'no-op change refused'}
  $matches=[regex]::Matches($text,[regex]::Escape($search))
  if($matches.Count-ne1){throw 'change search must match exactly once in source snapshot'}
  $lo=$matches[0].Index;$hi=$lo+$matches[0].Length
  foreach($span in $intervals){if($lo-lt$span.hi-and$hi-gt$span.lo){throw 'overlapping source changes refused'}}
  $intervals.Add(@{lo=$lo;hi=$hi})
 }
 foreach($n in @('prerequisites','evidence_limits','smoke_plan')){
  if($Artifact.$n-isnot[array]-or$Artifact.$n.Count-lt1-or$Artifact.$n.Count-gt32){throw 'protocol explanation array invalid'}
  foreach($v in $Artifact.$n){if($v-isnot[string]-or[string]::IsNullOrWhiteSpace($v)-or$v.Length-gt8192){throw 'protocol explanation item invalid'}}
 }
}
