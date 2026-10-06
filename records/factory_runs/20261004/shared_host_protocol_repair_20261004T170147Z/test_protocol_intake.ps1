$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'protocol_artifact.ps1')
$source=Join-Path $PSScriptRoot 'source_snapshot.cpp'
$before=(Get-FileHash -LiteralPath $source).Hash
$base=@{status='REFUSED';protocol_argument='Pure schema fixture: unresolved alias semantics; no execution claim.';changes=@();prerequisites=@('ROOT must establish corresponding-resource semantics.');evidence_limits=@('Intake is not protocol or GPU acceptance.');smoke_plan=@('No native execution admitted.')}
$search='// DESIGN-ONLY prototype. Do not compile or run before independent root review.'
$change=@{search=$search;replace=($search+' // PURE INTAKE FIXTURE ONLY');rationale='Checks unique search intake only; never applied and not a protocol repair.'}
$tests=@()
function Case([string]$Name,$Value,[bool]$Expected){
 $accepted=$true;$errorType=$null
 try{$parsed=Read-StrictJson ($Value|ConvertTo-Json -Depth 20);Assert-ProtocolArtifact $parsed}catch{$accepted=$false;$errorType=$_.Exception.GetType().Name}
 $script:tests+=@{name=$Name;expected_accept=$Expected;actual_accept=$accepted;passed=($accepted-eq$Expected);error_type=$errorType}
}
Case 'valid_refusal_empty_changes' $base $true
$v=$base.Clone();$v.status='PROPOSED';$v.changes=@($change);Case 'unique_source_proposed_intake_not_semantic_admission' $v $true
$v=$base.Clone();$v.status='PROPOSED';$v.changes=@(@{search='#include';replace='UNAPPLIED';rationale='Nonunique search must be rejected.'});Case 'nonunique_search_refused' $v $false
$v=$base.Clone();$v.status='PASS';Case 'unknown_status_refused' $v $false
$v=$base.Clone();$v.authority='ROOT_STATIC_ADMISSION';Case 'unknown_authority_field_refused' $v $false
$v=$base.Clone();$v.changes=@($change,$change,$change);Case 'refusal_with_three_fabricated_changes_refused' $v $false
$duplicateAccepted=$true
try{Read-StrictJson '{"status":"REFUSED","status":"PROPOSED"}'|Out-Null}catch{$duplicateAccepted=$false}
$tests+=@{name='duplicate_json_key_refused';expected_accept=$false;actual_accept=$duplicateAccepted;passed=(!$duplicateAccepted)}
$after=(Get-FileHash -LiteralPath $source).Hash
$result=@{utc=[DateTime]::UtcNow.ToString('o');scope='PURE_INTAKE_ONLY_ROOT_AUTHORIZED';tests=$tests;passed=@($tests|Where-Object {$_.passed}).Count;failed=@($tests|Where-Object {!$_.passed}).Count;source_before_sha256=$before;source_after_sha256=$after;source_unchanged=($before-ceq$after);credentials_read=$false;provider_requests=0;native_children=0;fixture_import_compile_gpu_run=$false;protocol_semantic_acceptance='NOT_ADJUDICATED'}
$result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'PURE_INTAKE_CONTROLS.json') -Encoding utf8
$result|ConvertTo-Json -Depth 12
if($result.failed-ne0-or!$result.source_unchanged){exit 1}
