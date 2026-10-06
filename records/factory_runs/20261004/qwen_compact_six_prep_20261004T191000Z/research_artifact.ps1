function Assert-ResearchArtifact($a){
 if($a-isnot[pscustomobject]-or(@($a.PSObject.Properties.Name|Sort-Object)-join',')-cne'analysis,evidence_limits,prerequisites,references,source,status,tests_source'){throw 'research keys mismatch'}
 if($a.status-cnotin@('PROPOSED','ANALYSIS','REFUSED')){throw 'status invalid'}
 foreach($n in @('source','tests_source')){$limit=if($n-ceq'source'){8000}else{6000};if($a.$n-isnot[string]-or$a.$n.Length-gt$limit){throw 'compact source bound'}}
 foreach($n in @('analysis','evidence_limits','prerequisites','references')){if($a.$n-isnot[array]-or$a.$n.Count-lt1-or$a.$n.Count-gt40){throw 'research array bound'};foreach($v in $a.$n){if($v-isnot[string]-or[string]::IsNullOrWhiteSpace($v)-or$v.Length-gt8192){throw 'research string'}}}
}