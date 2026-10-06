$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$jobs=@('supervisor_v2','validator_v2','gemini_candidate_review','grok_context_padding','grok_single_device','grok_supervisor_repair','grok_validator_repair','gemini_repaired_admission_review','grok_model_whitelist','qwen_scoped_repairs_20261004T125000Z\spawn_transaction','qwen_scoped_repairs_20261004T125000Z\cleanup_transaction','qwen_scoped_repairs_20261004T125000Z\capacity_participation','qwen_scoped_repairs_20261004T125000Z\proof_bindings')
$rows=@()
foreach($job in $jobs){
 $p=Join-Path $root ($job+'\terminal.json');$t=$null
 if(Test-Path -LiteralPath $p){$t=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json}
 $u=$t.usage;$input=$u.prompt_tokens;if($null-eq$input){$input=$u.input_tokens};$output=$u.completion_tokens;if($null-eq$output){$output=$u.output_tokens}
 $state=$t.status;if(!$t){$state='IN_FLIGHT_OR_MISSING_TERMINAL'}
 $rows+=@{call_id=$job;receipt=$p;requested_model=$t.requested_model;observed_model=$t.observed_model;status=$state;http=$t.http;exit_code=$t.exit_code;seconds=$t.elapsed_seconds;prompt_tokens=$input;completion_tokens=$output;total_tokens=$u.total_tokens;usage=$u;usage_available=($null-ne$u);vendor_reported_cost_usd=$t.vendor_reported_cost_usd;actual_native_children=0;product_accepted=$false}
}
$ledger=@{generated_utc=[DateTime]::UtcNow.ToString('o');scope=$root;calls=$rows;call_count=$rows.Count;observed_token_total=($rows|Measure-Object total_tokens -Sum).Sum;unknown_usage_calls=@($rows|Where-Object {!$_.usage_available}).Count;counting_rule='One row per actual provider request; copied/extracted source/review and gate artifacts are not extra inference calls. Token totals are provider-reported; do not add cache/thinking twice or equate them with monthly dashboard units. Vendor cost is reported evidence, not billing settlement.';native_agents_actual=0;native_agents_maximum_authorized_per_terminal=10;live_global_factory_modified=$false;previous_ledger_preserved='E:\the_harness\records\factory_runs\20261004\provider_usage_ledger_FINAL_20261004T112000.json'}
$out=Join-Path $root ('usage_snapshot_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'.json')
$ledger|ConvertTo-Json -Depth 16|Set-Content -LiteralPath $out -Encoding utf8
@{path=$out;calls=$rows.Count;observed_tokens=$ledger.observed_token_total;unknown_usage=$ledger.unknown_usage_calls}|ConvertTo-Json
