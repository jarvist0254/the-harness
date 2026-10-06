$ErrorActionPreference='Stop'
$base=$PSScriptRoot
$pipe=Join-Path $base 'gemini_grok_pipeline_20261004T110000'
$raw=Get-Content -Raw -LiteralPath (Join-Path $pipe 'grok_fast_stdout.json')|ConvertFrom-Json
$patch=Get-Content -Raw -LiteralPath (Join-Path $pipe 'grok_fast_patch_extracted.json')|ConvertFrom-Json
$source=Get-Content -Raw -LiteralPath (Join-Path $pipe 'opencl_executor.snapshot.py')
$matches=@($patch.replacements|ForEach-Object {$source.Contains($_.old)})
$receipt=[ordered]@{state='COMPLETE_PATCH_STATIC_MATCHED_PENDING_IMPLEMENTER_GATE';model='grok-4.7-build-fast';raw_terminal='grok_fast_terminal.json';raw_response='grok_fast_stdout.json';extraction_field='text';stop_reason=$raw.stopReason;exit_code=0;seconds=57.12;replacement_count=$matches.Count;exact_source_matches=$matches;usage=$raw.usage;model_usage=$raw.modelUsage;reported_cost_usd=$raw.total_cost_usd;actual_native_children=0;source_edited_by_this_agent=$false;root_approved_subject_to_independent_gate=$true}
$receipt|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $pipe 'grok_fast_acceptance_20261004T112000.json') -Encoding utf8
$future=Join-Path $base 'qwen_future_qualification_20261004T110800'
$four=Join-Path $future 'four_card_acceptance'
$answer=(Get-Content -Raw -LiteralPath (Join-Path $four 'answer.json')).Trim()
$answer=$answer -replace '^```json\s*','' -replace '\s*```$',''
$parsed=$answer|ConvertFrom-Json
$parsed|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $four 'review.extracted_20261004T112000.json') -Encoding utf8
@{state='COMPLETE_ADVISORY_WITH_INVALID_ASSERTIONS';format_recovery='Removed JSON markdown fence only; original answer and terminal preserved; no extra provider call';findings=@('T1 assertion no_kernel_launch_count > 0 contradicts zero native launches; use actual receipt schema and zero event count.','REJECTED/CAPACITY_REFUSED and assigned_layer_ids are proposed names, not verified current receipt fields.','T4 cannot request a B-to-C target using current injection CLI; actual control selects first vendor boundary.','No dedicated VRAM delta equality can be assumed for caching/driver allocations; measurement must distinguish shared AMD memory.','Reference to shared memory in initial verified mixed-vendor execution is misleading: transport is host-staged between separate contexts.','Four cards absent; all proposed four-card tests remain NOT_CHECKED.');actual_native_children=0}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $four 'ADJUDICATION_20261004T112000.json') -Encoding utf8
# Rebuild standard receipts using the existing bounded collector, preserving all prior snapshots.
$summary=& (Join-Path $base 'usage_ledger_v2_20261004T104000.ps1')|ConvertFrom-Json
$ledger=Get-Content -Raw -LiteralPath $summary.ledger|ConvertFrom-Json
$rows=@($ledger.rows)
foreach($name in @('gemini_terminal.json','grok_terminal.json','grok_fast_terminal.json')){
 $t=Get-Content -Raw -LiteralPath (Join-Path $pipe $name)|ConvertFrom-Json
 $state=$t.state
 if($name -eq 'grok_fast_terminal.json'){$state=$receipt.state}
 $rows+= [pscustomobject]@{path=(Join-Path $pipe $name);requested_model=$t.model;observed_model=$t.model;state=$state;exit_code=$t.exit_code;seconds=$t.seconds;prompt_tokens=$t.usage.input_tokens;completion_tokens=$t.usage.output_tokens;total_tokens=$t.usage.total_tokens;usage_available=($null -ne $t.usage);usage=$t.usage;product_accepted=$false;source_artifact_unverified=$true}
}
$rows=@($rows|Sort-Object path -Unique)
$ledger.rows=$rows
$ledger.observed_token_total=($rows|Measure-Object total_tokens -Sum).Sum
$ledger.usage_missing_rows=@($rows|Where-Object {!$_.usage_available}).Count
$ledger.generated_utc=[DateTime]::UtcNow.ToString('o')
$ledger|Add-Member -NotePropertyName counting_rule -NotePropertyValue 'One row per provider request directory or explicit pipeline call; copied answer/review/extraction artifacts are not calls. Missing usage is unknown. Provider-reported totals retained; cache/thinking breakdowns must not be added twice.'
$out=Join-Path $base 'provider_usage_ledger_FINAL_20261004T112000.json'
$ledger|ConvertTo-Json -Depth 15|Set-Content -LiteralPath $out -Encoding utf8
[pscustomobject]@{ledger=$out;rows=$rows.Count;observed_tokens=$ledger.observed_token_total;missing_usage=$ledger.usage_missing_rows;grok_exact_matches=$matches}|ConvertTo-Json -Depth 5
