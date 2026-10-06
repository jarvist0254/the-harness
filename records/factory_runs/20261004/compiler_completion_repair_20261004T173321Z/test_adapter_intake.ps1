$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'adapter_artifact.ps1')
$base=@{adapter_source="def fixture_hook():`n    return 'COMPILER_ROOT_EXITED_CLEANUP_REQUIRED', 'fixture only'`n";pure_tests_source="import unittest`nclass Fixture(unittest.TestCase):`n    pass`n";rationale=@('Pure intake fixture only, not semantic acceptance.');safety_checks=@('No Python evaluated or imported.');native_fixture_plan=@('Plan only, no launch.')}
$tests=@()
function CheckCase([string]$name,$v,[bool]$expected){
 $accepted=$true;$errorType=$null
 try{Assert-AdapterArtifact (Read-StrictJson ($v|ConvertTo-Json -Depth 20))}catch{$accepted=$false;$errorType=$_.Exception.GetType().Name}
 $script:tests+=@{name=$name;expected_accept=$expected;actual_accept=$accepted;passed=($accepted-eq$expected);error_type=$errorType}
}
CheckCase 'valid_bounded_complete_source_strings_intake_only' $base $true
$v=$base.Clone();$v.status='PASS';CheckCase 'unknown_status_field_refused' $v $false
$v=$base.Clone();$v.native_api_execution='NOW';CheckCase 'unknown_execution_field_refused' $v $false
$v=$base.Clone();$v.adapter_source='';CheckCase 'empty_adapter_source_refused' $v $false
$v=$base.Clone();$v.pure_tests_source=@{code='exec forbidden object'};CheckCase 'source_object_refused_without_execution' $v $false
$v=$base.Clone();$v.adapter_source=('x'*131073);CheckCase 'oversized_source_refused' $v $false
$v=$base.Clone();$v.native_fixture_plan='launch now';CheckCase 'wrong_explanation_type_refused' $v $false
$result=@{utc=[DateTime]::UtcNow.ToString('o');scope='PURE_ADAPTER_INTAKE_ONLY';tests=$tests;passed=@($tests|Where-Object {$_.passed}).Count;failed=@($tests|Where-Object {!$_.passed}).Count;provider_calls=0;credentials_read=$false;python_parse_eval_import=$false;native_process_fixture_or_gpu_run=$false;native_children_actual=0;semantic_adapter_admission=$false}
$result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'PURE_ADAPTER_INTAKE_CONTROLS.json') -Encoding utf8
$result|ConvertTo-Json -Depth 12
if($result.failed-ne0){exit 1}
