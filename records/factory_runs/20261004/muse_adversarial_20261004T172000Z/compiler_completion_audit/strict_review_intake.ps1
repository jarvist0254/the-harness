$ErrorActionPreference = 'Stop'
. 'E:\the_harness\records\factory_runs\20261004\compiler_completion_repair_20261004T173321Z\review_artifact_v2.ps1'
$artifactPath = Join-Path $PSScriptRoot 'run_output\parsed_review.json'
$artifact = Get-Content -LiteralPath $artifactPath -Raw | ConvertFrom-Json
$selected = Get-StrictReviewFromCli ([pscustomobject]@{ structured_output = $artifact })
$result = [ordered]@{ intake = 'V2_STRICT_JSON_ACCEPTED'; source = $selected.source; artifact = $selected.artifact; root_authority = 'NONE' }
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run_output\strict_intake_result.json') -Encoding utf8
$result | ConvertTo-Json -Depth 12
