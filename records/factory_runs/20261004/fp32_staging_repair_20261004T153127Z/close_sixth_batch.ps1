$ErrorActionPreference='Stop'
$b=$PSScriptRoot
function ReadEvidenceJson($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json}
function GetEvidenceHash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function SaveEvidenceJson($n,$v){$v|ConvertTo-Json -Depth 30|Set-Content -LiteralPath (Join-Path $b $n) -Encoding utf8}
$src='E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\ggml\src\ggml-vulkan\ggml-vulkan.cpp'
$f=[IO.File]::ReadAllText((Join-Path $b 'ggml_vk_mul_mat_q_f16.excerpt.cpp.txt'))
$qp=Join-Path $b 'qwen_fp32_patch\patch.pending_root_qa.json'
$gp=Join-Path $b 'grok_fp32_patch\patch.pending_root_qa.json'
$q=ReadEvidenceJson $qp;$g=ReadEvidenceJson $gp
$regions=@(for($i=0;$i -lt 3;$i++){@{region=$i+1;search_matches=([regex]::Matches($f,[regex]::Escape($g.changes[$i].search))).Count;search_equals_qwen=($g.changes[$i].search -ceq $q.changes[$i].search);replace_equals_qwen=($g.changes[$i].replace -ceq $q.changes[$i].replace)}})
$expected='    const uint64_t y_sz = quantize_y ? (ggml_vk_align_size(y_ne, 128) * ggml_type_size(GGML_TYPE_Q8_1) / ggml_blck_size(GGML_TYPE_Q8_1)) : ggml_type_size(y_f32_kernel ? GGML_TYPE_F32 : f16_type) * y_ne;'
$gate=@{utc=[DateTime]::UtcNow.ToString('o');mode='DATA_ONLY_NO_APPLY';source_sha256=GetEvidenceHash $src;source_expected_sha256='86c7d9251ecddff54f6a53956cfd22c94ef9090064789b7a362d56cb1b3cadef';qwen_patch_sha256=GetEvidenceHash $qp;grok_patch_sha256=GetEvidenceHash $gp;regions=$regions;region3_exact_root_formula=($g.changes[2].replace -ceq $expected);acceptance='PENDING_ROOT_QA';patch_applied=$false;tests_compile_gpu_run=$false}
SaveEvidenceJson 'GROK_TEXT_MATCH_GATE.json' $gate
$alive=@(foreach($id in @(31016,51436)){if(Get-Process -Id $id -ErrorAction SilentlyContinue){$id}})
SaveEvidenceJson 'grok_fp32_patch.REAPED_RECEIPT.json' @{utc=[DateTime]::UtcNow.ToString('o');wrapper_pid=31016;cli_pid=51436;wrapper_session=23164;wrapper_session_exit=0;cli_exit=0;owned_pids_still_alive=$alive;identity='Retained owned process/session exits primary; point PID absence informational'}
$qt=ReadEvidenceJson (Join-Path $b 'qwen_fp32_patch\terminal.json');$mt=ReadEvidenceJson (Join-Path $b 'gemini_fp32_review_v2.owned_terminal.json');$gt=ReadEvidenceJson (Join-Path $b 'grok_fp32_patch.owned_terminal.json')
$calls=@(
 @{job='qwen_fp32_patch';role='Qwen_Workhorse';model='qwen3.8-max';transport='DIRECT_HTTP';terminal='qwen_fp32_patch\terminal.json';reported_tokens=11992;usage=$qt.usage;internal_model_calls=$null;elapsed_seconds=20.76;artifact_sha256=GetEvidenceHash $qp;wrapper_pid=55480;worker_pid=87556},
 @{job='gemini_fp32_review_v2';role='Gemini_Reviewer';model='gemini-3.8-flash-medium';transport='AGY_CLI';terminal='gemini_fp32_review_v2.owned_terminal.json';reported_tokens=54292;usage=$mt.usage;internal_model_calls=$null;elapsed_seconds=$mt.elapsed_seconds;artifact_sha256=GetEvidenceHash (Join-Path $b 'gemini_fp32_review_v2\review.pending_root_qa.json');raw_review_verdict='PASS';execution_approval=$false;wrapper_pid=29272;cli_pid=82588},
 @{job='grok_fp32_patch';role='Grok_Editor';model='grok-4.7-build-fast';transport='GROK_CLI';terminal='grok_fp32_patch.owned_terminal.json';reported_tokens=22902;usage=$gt.usage;model_usage=$gt.model_usage;internal_model_calls=1;elapsed_seconds=$gt.elapsed_seconds;artifact_sha256=GetEvidenceHash $gp;wrapper_pid=31016;cli_pid=51436}
)
$base='E:\the_harness\records\factory_runs\20261004\layer_diagnostic_20261004T144323Z\USAGE_FINAL_SIX_20261004T150416Z.json'
$ledger=@{utc=[DateTime]::UtcNow.ToString('o');definition='SIXTH isolated CLOSED batch; prior five immutable';calls=$calls;paid_jobs=3;direct_http_requests=1;cli_jobs=2;native_children_actual=0;max_authorized_native_children_each_qwen_deepseek_parent=10;observed_total_tokens=89186;unknown_usage_jobs=0;per_provider=@{Qwen=@{jobs=1;tokens=11992};Gemini=@{jobs=1;tokens=54292};Grok=@{jobs=1;tokens=22902}};excluded_local_startup=@{job='gemini_fp32_review';status='LOCAL_PRE_PROVIDER_START_FAILURE';reason='Windows argument length, no child/provider launch';paid_job=$false};prior_five=@{path=$base;sha256=GetEvidenceHash $base;jobs=47;observed_tokens=2515200;unknown_usage_jobs=2};all_six=@{jobs=50;observed_tokens=2604386;unknown_usage_jobs=2;per_provider=@{Qwen=@{jobs=21;tokens=394235;unknown_usage_jobs=1};Gemini=@{jobs=12;tokens=1377614;unknown_usage_jobs=0};Grok=@{jobs=17;tokens=832537;unknown_usage_jobs=1}}};credits='Provider tokens are not ModelStudio Credits; per-job Credits/billing NOT_CHECKED';acceptance='All patches unapplied; ROOT QA pending';source_sha256=GetEvidenceHash $src;secret_process_audit='SECRET_PROCESS_AUDIT_SIXTH.json';later_root_adjudication='Separate receipt only; preserve this immutable ledger'}
SaveEvidenceJson 'USAGE_FINAL_SIXTH.json' $ledger
SaveEvidenceJson 'CLOSED_RECEIPT.json' @{utc=[DateTime]::UtcNow.ToString('o');status='PROVIDER_BATCH_CLOSED_PENDING_ROOT_QA';paid_jobs=3;observed_tokens=89186;ledger='USAGE_FINAL_SIXTH.json';source_gate='GROK_TEXT_MATCH_GATE.json';secret_process_audit='SECRET_PROCESS_AUDIT_SIXTH.json';source_applied=$false;native_compile_gpu_run=$false;full_goal_complete=$false}
$gate|ConvertTo-Json -Depth 8
