$ErrorActionPreference='Stop'
$base='E:\the_harness\records\factory_runs\20261004'
$out=Join-Path $base 'grok_combined_dma_repair_prep_20261004T214800Z'
if(Test-Path -LiteralPath $out){throw 'immutable folder exists'}
New-Item -ItemType Directory -Path $out|Out-Null
$utf=[Text.UTF8Encoding]::new($false)
function Pin($p){@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $p).Length}}
function WriteNew($n,$s){[IO.File]::WriteAllText((Join-Path $out $n),$s,$utf)}
$old=Join-Path $base 'grok_capacity_repair_prep_20261004T203621Z'
Copy-Item -LiteralPath (Join-Path $old 'provider_common.ps1') -Destination (Join-Path $out 'provider_common.ps1')
Copy-Item -LiteralPath (Join-Path $base 'l0_egl_sync_bridge_two_prep_20261004T212837Z\research_artifact.v3.ps1') -Destination (Join-Path $out 'research_artifact.ps1')
$wrapper=[IO.File]::ReadAllText((Join-Path $old 'invoke_owned_capacity_editor.ps1'))
$before='Tool-less four-physical-card measured-capacity validator corrective source editor.'
$after='Tool-less CUDA device DMA-BUF to Level Zero payload-experiment corrective C++ source editor.'
if(([regex]::Matches($wrapper,[regex]::Escape($before))).Count-ne1){throw 'wrapper attribution span not unique'}
WriteNew 'invoke_owned_combined_editor.ps1' ($wrapper.Replace($before,$after))
$source=Join-Path $base 'muse_combined_dma_prep_20261004T205950Z\source.snapshot.txt'
$tests=Join-Path $base 'cuda_l0_device_dmabuf_prep_20261004T195400Z\qwen_cuda_l0_device_dmabuf_v3\tests_source.qwen_untrusted.txt'
$muse=Join-Path $base 'muse_combined_dma_prep_20261004T205950Z\run_output\muse_review.extracted.json'
$gem=Join-Path $base 'gemini_combined_dma_prep_20261004T211555Z\gemini_combined_high_v3_with_companion\review.pending_root_qa.json'
$compile='E:\the_harness\records\root_continuation_20261004\cuda_l0_source_compile_20261004T202000Z_attempt2'
$bridge='E:\the_harness\records\root_continuation_20261004\l0_fd_sync_bridge_trace_20261004T2115Z'
$inputs=@($source,$tests,$muse,$gem,(Join-Path $compile 'compile_qa_findings.md'),(Join-Path $compile 'compile.stderr.txt'),(Join-Path $compile 'compile_receipt.json'),(Join-Path $bridge 'bridge_contract_findings.md'),(Join-Path $bridge 'source_excerpts.txt'),'E:\the_harness\records\root_continuation_20261004\ROOT_COMBINED_DMA_STATIC_REVIEW_20261004T205616Z.json','E:\the_harness\records\root_continuation_20261004\EGL_LEVEL_ZERO_PINNED_API_EXCERPTS_20261004T2101Z.txt')
$task=@'
Produce a complete corrected C++ source plus complete meaningful actual-file behavioral CPU/header-stub test source for the exact original combined CUDA-device-export to Intel-LevelZero-import payload experiment. Source only: NO tools, compilation, execution, imports, browsing, installation, auth or file edits. User authorizes max10 native agents EACH Qwen/DeepSeek if actually supported, but this Grok tool-less CLI has native children0 and no tool calls. Return strict ONE JSON object exact keys status,source,tests_source,analysis,prerequisites,evidence_limits,references. status PROPOSED|ANALYSIS|REFUSED; source<=32000 UTF16 chars, tests_source<=16000, explanatory fields arrays1..40 of nonempty strings<=8192. No truncated source, no grep-only tests, no copied implementation inside tests.

ROOT ADJUDICATION supersedes erroneous reviewer advice, but preserve raw reviews as advisory inputs. Fix eight measured API callsites using exact supplied official headers. Emit one strict machine JSON terminal receipt: status PASS|FAIL|NOT_CHECKED EXACT, exits0|1|2. PAYLOAD_EXPERIMENT_ONLY is scope, never status. Bare queries/payload parity NEVER direct P2P or physical residency proof; direct_transport_qualified=false mandatory. API-success value0/absent missing prerequisite may NOT_CHECKED2; attempted CUDA_ERROR_INVALID_VALUE, DEVICE_LOST, allocation/copy/query failures are FAIL1 with original exact codes, not generic unsupported. CUDA device allocation occurs AFTER CUDA DMA_BUF gate but BEFORE Intel eligibility in original; check actual Intel GPU/fullUUID/root/capability BEFORE contexts/allocations where legal. Bound all counts/retries/vectors; preserve unknowns and all actual query errors. Selected imported device owner/type must be checked.

Pinned Intel compute-runtime d4fc0756006fa28738766cb66034dc9acadea91e DEVICE alloc import consumes its input FD on SUCCESS, FAILURE retains it; original import_fd=-1 on successful import may be correct. DO NOT introduce blanket borrowed FD rule, double-close or leak to 'fix' ownership; branch-specific implementation is not universal installed-driver guarantee. Explicit prerequisites/runtime version receipts and ownership transitions, duplicate for import where appropriate with clear original/duplicate lifetime. Do not claim undocumented reverse desktop CUDA DMA-BUF import. Current WSL CUDA false DMA_BUF_SUPPORTED is missing prerequisite NOT_CHECKED2 before allocations; no Intel enumerated, cannot prove transfer here.

Producer cuMemsetD32 deterministic64KiB and one-word GPU corruption BEFORE release/import/copy; unchanged independent CPU full16384-word comparison and complete baseline/control results. No fakeCPU refill asGPUforwarding. Synchronization must follow actual CUDA completion and documented imported consumer queue ordering; unknown cache/physical transport stays explicit limit, not fabricated success. Bounded10s waits, but no destruction/free of possibly busy submitted work on timeout. Honest UNKNOWN_DRAIN and owned supervisor process termination boundary is acceptable; native blocking call cancellation cannot be guaranteed by a source timeout. Attempt/check independent cleanup operations after known quiescence; any cleanup failure/uncertainty forces FAIL and unknown drain, no unconditional cleanup_unknown=false. Emit AFTER cleanup disposition. Full strict CLI unknown/duplicate/UUID/direction validation. Tests actually target supplied candidate and real pinned API header stubs, strictJSON/status/native-error mappings/count caps/FD success-vs-failure ownership/timeoutcleanup/GPU producer-control contract; do not execute them yourself. ROOT alone will admit compiler/native tests later.
'@
WriteNew 'grok_combined_high.spec.txt' $task
$prompt=$task
foreach($p in $inputs){$prompt+="`n`nINPUT $(Split-Path -Leaf $p) SHA256 $((Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant())`n"+[IO.File]::ReadAllText($p)}
WriteNew 'grok_combined_high.prompt.txt' $prompt
$packet=@{utc=[DateTime]::UtcNow.ToString('o');status='PREPARATION_ONLY_PENDING_ROOT_ADMISSION';job='grok_combined_high';model='grok-4.7-build-fast';reasoning_effort='high';deadline_seconds=600;stdout_cap_bytes=2097152;stderr_cap_bytes=2097152;source_limit_chars=32000;tests_limit_chars=16000;native_children_actual=0;generated_source_execution=$false;inputs=@($inputs|ForEach-Object{Pin $_});prompt=(Pin (Join-Path $out 'grok_combined_high.prompt.txt'));spec=(Pin (Join-Path $out 'grok_combined_high.spec.txt'));wrapper=(Pin (Join-Path $out 'invoke_owned_combined_editor.ps1'));common=(Pin (Join-Path $out 'provider_common.ps1'));intake=(Pin (Join-Path $out 'research_artifact.ps1'));wrapper_diff=@{only_replacement_search=$before;replace=$after;count=1;deadline_transport_secret_controls_unchanged=$true};launch_authorized=$false}
WriteNew 'GROK_COMBINED_ROOT_REVIEW_PACKET.json' ($packet|ConvertTo-Json -Depth 30)
Pin (Join-Path $out 'GROK_COMBINED_ROOT_REVIEW_PACKET.json')|ConvertTo-Json
