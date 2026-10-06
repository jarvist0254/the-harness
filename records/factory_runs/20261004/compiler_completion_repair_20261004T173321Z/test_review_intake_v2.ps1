$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'review_artifact_v2.ps1')
$base=@{verdict='REJECT';findings=@(@{region='fixture';exact_source='fixture';reason='fixture only';minimal_fix='ROOT review required'});safety_checks=@('No tools, CLI, provider, native or GPU execution.')}
$tests=@()
function CheckReview([string]$Name,[string]$Raw,[bool]$Expected){
 $accepted=$true;$selected=$null;$errorType=$null
 try{$r=Read-StrictJson $Raw;$v=Get-StrictReviewFromCli $r;$selected=$v.source}catch{$accepted=$false;$errorType=$_.Exception.GetType().Name}
 $script:tests+=@{name=$Name;expected_accept=$Expected;actual_accept=$accepted;selected_source=$selected;passed=($accepted-eq$Expected);error_type=$errorType}
}
CheckReview 'valid_actual_structured_output_over_nonjson_response' (@{structured_output=$base;response='```json mixed invalid response'}|ConvertTo-Json -Depth 10) $true
CheckReview 'strict_json_response_fallback' (@{response=($base|ConvertTo-Json -Depth 10)}|ConvertTo-Json -Depth 10) $true
CheckReview 'duplicate_outer_keys_refused_before_selection' '{"structured_output":{},"response":"{}","usage":{},"usage":{}}' $false
CheckReview 'malformed_outer_json_refused' '{"structured_output":' $false
$v=$base.Clone();$v.authority='ROOT_STATIC_ADMISSION';CheckReview 'structured_extra_authority_refused_no_fallback' (@{structured_output=$v;response=($base|ConvertTo-Json -Depth 10)}|ConvertTo-Json -Depth 10) $false
CheckReview 'markdown_response_without_structured_output_refused' (@{response='```json {"verdict":"PASS"} ```'}|ConvertTo-Json -Depth 10) $false
$v=$base.Clone();$v.findings=@(@{region='x';exact_source='x';reason='x'});CheckReview 'incomplete_finding_refused' (@{structured_output=$v}|ConvertTo-Json -Depth 10) $false
$r=@{utc=[DateTime]::UtcNow.ToString('o');scope='PURE_REVIEW_INTAKE_ONLY';tests=$tests;passed=@($tests|Where-Object {$_.passed}).Count;failed=@($tests|Where-Object {!$_.passed}).Count;cli_provider_calls=0;credentials_read=$false;native_fixture_or_gpu_run=$false;native_children=0;verdict_is_runtime_approval=$false}
$r|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'PURE_REVIEW_INTAKE_V2_CONTROLS.json') -Encoding utf8
$r|ConvertTo-Json -Depth 12
if($r.failed-ne0){exit 1}
