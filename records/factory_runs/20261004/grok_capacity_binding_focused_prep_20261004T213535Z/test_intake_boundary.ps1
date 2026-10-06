$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskIntake=Join-Path $taskRoot 'research_artifact.ps1'
$taskBefore=(Get-FileHash -LiteralPath $taskIntake).Hash.ToLowerInvariant()
if($taskBefore-cne'458c5e8b30dc91cb490e324c6572ad4b7b642f7ce068ad2d9b43905d93b931b6'){throw 'intake pin mismatch'}
# Only the fully read pure validation function is dot-sourced. No transport helper.
. $taskIntake
function New-PureArtifact {
 return [pscustomobject]@{status='PROPOSED';source=('s'*32768);tests_source=('t'*16384);analysis=@('synthetic boundary only');prerequisites=@('none');evidence_limits=@('not candidate execution');references=@('synthetic')}
}
$taskCases=@(
 @{name='exact_source_and_test_character_limits';expected='PASS';mutate={param($v)}},
 @{name='source_limit_plus_one';expected='REFUSE';mutate={param($v)$v.source+='s'}},
 @{name='test_limit_plus_one';expected='REFUSE';mutate={param($v)$v.tests_source+='t'}},
 @{name='unknown_status_enum';expected='REFUSE';mutate={param($v)$v.status='PASS'}},
 @{name='explanation_string_instead_of_array';expected='REFUSE';mutate={param($v)$v.analysis='wrong_type'}}
)
$taskResults=@()
foreach($taskCase in $taskCases){
 $taskValue=New-PureArtifact
 & $taskCase.mutate $taskValue
 $taskObserved='PASS';$taskError=$null
 try{Assert-ResearchArtifact $taskValue}catch{$taskObserved='REFUSE';$taskError=$_.Exception.Message}
 $taskResults+=@{name=$taskCase.name;expected=$taskCase.expected;observed=$taskObserved;passed=($taskObserved-ceq$taskCase.expected);error=$taskError}
}
$taskAfter=(Get-FileHash -LiteralPath $taskIntake).Hash.ToLowerInvariant()
$taskPass=@($taskResults|Where-Object passed).Count
$taskReceipt=@{scope='PURE_INTAKE_FUNCTION_BOUNDARY_CONTROLS_ONLY';total=5;passed=$taskPass;failed=(5-$taskPass);cases=$taskResults;intake_sha256_before=$taskBefore;intake_sha256_after=$taskAfter;hash_unchanged=($taskBefore-ceq$taskAfter);provider_calls=0;candidate_source_imported_or_executed=$false;native_gpu_calls=0}
$taskOut=Join-Path $taskRoot 'INTAKE_BOUNDARY_RECEIPT.json'
if(Test-Path -LiteralPath $taskOut){throw 'immutable receipt exists'}
[IO.File]::WriteAllText($taskOut,($taskReceipt|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$taskReceipt|ConvertTo-Json -Depth 8
if($taskPass-ne5-or$taskBefore-cne$taskAfter){exit 1}
