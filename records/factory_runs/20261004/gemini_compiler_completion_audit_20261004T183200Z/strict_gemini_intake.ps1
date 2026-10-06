$ErrorActionPreference='Stop'
. 'E:\the_harness\records\factory_runs\20261004\compiler_completion_repair_20261004T173321Z\review_artifact_v2.ps1'
$artifact=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'gemini_review_attempt2.pending_root_qa.json') -Raw | ConvertFrom-Json
$selected=Get-StrictReviewFromCli ([pscustomobject]@{structured_output=$artifact})
$result=[ordered]@{intake='V2_STRICT_JSON_ACCEPTED';source=$selected.source;artifact=$selected.artifact;root_authority='NONE'}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'gemini_review_attempt2.strict_intake.json'),($result|ConvertTo-Json -Depth 40),[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Depth 2
