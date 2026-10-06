# Harness and JLink five hour handoff

**Work stopped at the user's request on October 4, 2026, at 19:08 EDT / 23:08 UTC. The goal is PAUSED and the overall project is INCOMPLETE.** This report covers approximately 14:08–19:08 EDT / 18:08–23:08 UTC, followed by closure receipts and documentation. Earlier results are identified as carry-in work. It records completed engineering work, failed experiments, proposals that never ran, provider activity, and the state left on disk.

The strongest new result is passing numerical computation on the installed NVIDIA/AMD pair using the repaired, exact ggml build and a fixed F32 model fixture. **No Intel–NVIDIA direct P2P, Intel–Intel physical peer transfer, NVLink-style bridge, pooled VRAM, or four-card 8 GB capacity result was demonstrated.** Intel card selection remains undecided; the evidence does not support buying Intel cards on the assumption that JLink already works.

The previous roughly **45%** completion figure remains a low-confidence engineering planning estimate. It is not a measured fraction of the requirements, an ETA, or a hardware qualification score. Passing more software controls does not close the central transport and physical hardware requirements.

The concise companion report is [Desktop status](C:/Users/thoma/Desktop/status/harness-jlink-status.md). The [previous Desktop snapshot](C:/Users/thoma/Desktop/status/harness-jlink-status-20261004-1841.md) is preserved. [Documentation verification](records/HANDOFF_LAST_5_HOURS_VERIFICATION.json) records file existence, document hashes, and the saved evidence hashes checked during this handoff.

## Results at the stop point

| Workstream | Completed result | Qualification limit |
|---|---|---|
| Compiler completion policy | Local adapter passed 12 mock controls; four cleanup demotion controls and five native CPU fixtures passed their expected gates. Attempt 5 produced the binaries used below. | Cleanup after compiler-root exit is recorded explicitly; no whole-tree natural completion certificate. |
| NVIDIA and AMD operators | Each device passed 12,288 comparisons across six layouts, zero mismatches. | Installed RTX 5070 Ti and AMD shared-memory iGPU only. |
| Mixed-device model | Both device orders passed 151,936 finite final-token logit comparisons per order at the fixed tolerance. | CPU-dequantized F32 Qwen3-0.6B fixture; original Q8 remains unqualified. |
| Corruption detection | Four host readback/logit controls each detected the intended mismatch and exited 1. | These are host mutations, not GPU-producer or P2P-boundary fault injection. |
| Four-card capacity validator | Grok correction passed 73 independent synthetic controls. | No physical capacity, residency, allocator-OOM or four-card experiment. |
| Directed receipt validator | 24 scored synthetic controls passed; three malformed shapes raised ValueError separately. | Evidence consistency only; transport_accepted remains false. |
| Intel query collector | Local derivative passed seven CPU-fake checks. Separate Qwen candidate passed an object-only compile. Muse and Gemini both requested changes. | No Intel enumeration or native peer capability measurement; candidates remain distinct. |
| Intel peer-copy logic | Local repair passed eleven CPU-fake cases and eleven unique independent test methods. | Ordinary host malloc apparatus; no Intel device copy or P2P. |
| Completion and FD adapter | Independent v3 QA executed and remained RED: ten methods, nine failure events and one error. | Adapter is unaccepted; candidate completion/FD/cleanup defects remain. |
| Muse review parser | Revised terminal parser passed 18 independent cases. Actual Muse and Gemini collector reviews completed. | Review ingestion and source review, not GPU qualification. |
| Native EGL consumer proposal | Qwen request completed with finish_reason=length; partial output and extracted source string preserved for review. | No accepted schema, compile, native consumer or payload experiment. |
| Intel primary research | Official guide and pinned upstream source snapshots downloaded; FD/synchronization findings preserved. | Final multi-Arc research report and experiment matrix were unfinished. |

## Compiler repair and numerical GPU acceptance

The compiler completion work separated a compiler root's exit from proof that every descendant naturally completed. The ROOT-authored local adapter uses the existing contained supervisor and records cleanup explicitly. It passed the unchanged **12** independent mock controls. Four additional controls injected failures in job closure, owned-handle closure, reader completion and shutdown; each retained UNKNOWN_DRAIN and the caller refused acceptance. No native process calls occurred in those four mock evaluations.

The bounded native CPU suite covered success, a successful root with a resident descendant, resident failure, timeout and cancellation. All **five** reached their expected acceptance/refusal gates, with CLEANUP, zero active job processes, matching restart receipts and checked controller absence. The successful compiler cases still say whole_tree_certificate=false. These fixtures do not certify arbitrary controller loss or GPU workers.

Evidence: [adapter and 12-control receipt](records/root_continuation_20261004/compiler_adapter_local_fallback_20261004T182833Z/root12_receipt.json), [four refusal controls](records/root_continuation_20261004/compiler_cleanup_refusal_proof_20261004T183508Z/proof_results.json), [five native CPU fixtures](records/root_continuation_20261004/compiler_completion_driver_prepare_20261004T181731Z/native_runs/suite_1791138717588329600/suite_receipt.json), [ROOT attempt-5 admission](records/root_continuation_20261004/ROOT_FP32_BUILD_ATTEMPT5_ADMISSION_20261004T1837Z.json), [actual build controller result](records/build_vulkan_fp32_staging_20261004T155932Z/evidence/attempt5_compiler_root_cleanup/controller_result.json).

The fresh attempt-5 build then passed the fixed operator and model comparisons on the installed NVIDIA GeForce RTX 5070 Ti and AMD Radeon integrated graphics:

| Actual run | Comparisons | Mismatches | Exit | Recorded result |
|---|---:|---:|---:|---|
| NVIDIA operator, six layouts | 12,288 | 0 | 0 | Operator parity pass |
| AMD operator, six layouts | 12,288 | 0 | 0 | Operator parity pass |
| NVIDIA operator, host corruption | 12,288 | 1 | 1 | Expected mismatch detected |
| AMD operator, host corruption | 12,288 | 1 | 1 | Expected mismatch detected |
| F32 model, NVIDIA then AMD | 151,936 | 0 | 0 | Fixed fixture parity pass |
| F32 model, AMD then NVIDIA | 151,936 | 0 | 0 | Fixed fixture parity pass |
| F32 model, default-order host corruption | 151,936 | 1 | 1 | Expected mismatch detected |
| F32 model, reverse-order host corruption | 151,936 | 1 | 1 | Expected mismatch detected |

The operator tolerance remained `2e-5 + 2e-6 × abs(CPU reference)`. The model tolerance remained `0.01 + 0.01 × abs(CPU reference)`. Neither was widened. The clean model runs had maximum absolute errors 0.000058650970458984375 and 0.00007343292236328125, with RMSE approximately 0.0000110492 and 0.0000154611. The comparison covers 16 final-token positions, 0–15, for these fixed inputs.

The model is a distinct **2,390,150,816-byte F32 fixture**, produced by CPU dequantization of the **639,446,688-byte Q8_0** model. This change in representation matters: the original Q8 model was not rerun against the final attempt-5 binaries and is still unqualified. Earlier Q8 failures and earlier F32 diagnostic failures remain preserved. No Q8 pass can be inferred from the F32 result.

The [ROOT numerical acceptance](records/root_continuation_20261004/FP32_FRESH_NUMERICAL_ACCEPTANCE_20261004T1910Z.json) binds eight run receipts, eight stdout captures, five DLLs and the build receipt. Its SHA256 is `b1da0dd4719ee343b39f63e8ca0597d80c0c94c7083fe80d283d5b2f81204cde`. An uncertain earlier operator capture and a corruption invocation that failed argument parsing before model execution are explicitly excluded. There is no whole-tree completion certificate.

These passes establish the measured software computation and comparator behavior. They establish neither direct transport nor physical residency, combined usable VRAM, four installed cards, arbitrary-model accuracy or performance. No GPU workloads were rerun to create this handoff.

## Capacity and directed receipt validators

The independent capacity audit originally exposed three false acceptances in 47 controls: mismatched CPU-reference bytes, and single-/three-card OOM owners unrelated to the declared physical population. The actual Grok correction now refuses those cases. ROOT retained the original 47 substantive assertions and added 26 controls for full JSON references and population subsets. **73/73 passed**, with zero scored failures, exceptions, input mutations or denied audit events. The bounded evaluator exited 0 and was reaped; source, tests, controller and Python pins stayed unchanged.

The source hash is `446d78eaebd631eac79bca9f32c71671a485642371e1e9899306c7199543c5a5`. It remains a synthetic validator; caller-supplied artifact registries do not authenticate native device events or actual allocation ownership. It was not promoted into PyRe or accepted as proof of four-card capacity. [Capacity adjudication](records/root_continuation_20261004/capacity_binding_grok_root_audit_20261004T215300Z/FINAL_ADJUDICATION.md) and [raw outcomes](records/root_continuation_20261004/capacity_binding_grok_root_audit_20261004T215300Z/stdout.raw.json) preserve the complete result.

The repaired directed-transfer candidate passed **24 scored consistency controls**. Three extra malformed-input observations raised ValueError and were retained separately. Original contradictions involving an unrelated baseline, identical physical identities under different vendor labels, and an unregistered residency digest now refuse. Even a consistent synthetic DEVICE_P2P declaration returns `scope=evidence_consistency_only` and `transport_accepted=false`. HOST staging is classified as HOST_BACKED.

The exact source remains in its original schema-refused, untrusted review file, SHA256 `fc73cb96c60a4df88815d670f3d6682ff71c3a1cbcaf9dc06942bc780768dc29`. Provider-authored tests were not executed. The bounded independent evaluator exited 0 in 0.078 seconds, readers joined, pins remained unchanged and no GPU/native calls occurred. [Directed audit](records/root_continuation_20261004/directed_receipt_repair_audit_20261004T2135Z/AUDIT_EXECUTED.md) explains the controls and the remaining authority boundary.

## Intel collector candidates and independent reviews

There are **two different collector candidates**. Their results must not be combined into one acceptance.

The ROOT local derivative repaired JSON integer encoding, genuine external-property queries, status mapping, root-handle/full-UUID deduplication, and preservation of original API error codes. The original baseline was **1 PASS / 6 FAIL**; the final local derivative reached **7 PASS / 0 FAIL** against a CPU fake compiled with the official header. Three actual CPU-only stub processes covered normal, duplicate-root and initialization-error paths. Directed peer values remained asymmetric `[-1, 1, 0, -1]`; DEVICE_LOST returned FAIL/exit 1 with result 1879048193. All results retain direct_transport_qualified=false.

The local source is [source.local_derivative_revision2.cpp](records/root_continuation_20261004/l0_query_local_repair_20261004T214344Z/source.local_derivative_revision2.cpp), SHA256 `5e8c32b98c1fec8fa708435fc7c039828b1ed1326fca269a0e1bb75fcd3edbd6`. [Local adjudication](records/root_continuation_20261004/l0_query_local_repair_20261004T214344Z/ADJUDICATION.md) preserves the original failures, intermediate source snapshots, imports, captures and cleanup receipts.

Muse then reviewed this exact local derivative and returned **11 findings / REQUEST_CHANGES**. Gemini reviewed the full derivative and all eleven Muse findings and also returned **11 findings / REQUEST_CHANGES**. Material remaining concerns include output truncation that can leave incomplete JSON, physical-root coverage, enumeration count changes, identity aliases, device-type handling and error branches. ROOT also recorded additional scope gaps. Review suggestions were checked against actual indexing and caller bounds; speculative claims were not automatically converted into defects.

The actual Muse collector review completed in about 55 seconds with `meta/muse-spark-1.3`; its owned job closed cleanly, and usage remains UNKNOWN. The actual Gemini request asked for `gemini-3.8-flash-high`, completed in 104.42 seconds, exited 0 and reported **59,125 tokens**. Its requested model is recorded; the terminal's model_usage field is null. Source review does not establish hardware behavior.

Evidence: [Muse closure](records/factory_runs/20261004/muse_l0_collector_prep_20261004T220000Z/parser_revision2/CLOSED_MUSE_COLLECTOR_RECEIPT.json), [Muse findings](records/factory_runs/20261004/muse_l0_collector_prep_20261004T220000Z/parser_revision2/run_output/parsed_review.json), [ROOT additional gaps](records/factory_runs/20261004/muse_l0_collector_prep_20261004T220000Z/ROOT_ADDITIONAL_COLLECTOR_SCOPE_GAPS_20261004T220600Z.json), [Gemini terminal](records/factory_runs/20261004/gemini_l0_collector_review_prep_20261004T222800Z/gemini_l0_collector_high.owned_terminal.json), [Gemini findings](records/factory_runs/20261004/gemini_l0_collector_review_prep_20261004T222800Z/gemini_l0_collector_high/review.pending_root_qa.json).

Separately, Qwen delivered a new [source.qwen_untrusted.cpp](records/factory_runs/20261004/l0_compiler_two_prep_v2_20261004T214600Z/qwen_l0_query_measured_repair/source.qwen_untrusted.cpp), 18,540 bytes, SHA256 `27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2`. Its GCC 13.3 C++17 **object-only compile passed**, exit 0 in 0.454 seconds, with no warnings/errors and two compiler column-tracking notes. The object hash is `1fa2833788b88605de3b450c6a63f10c88724e0e9f9b9e3080eea30282505022`.

That candidate has **not** been linked or executed, and neither its provider tests nor independent CPU fakes have run. ROOT's full source inspection still found truncation/fail-open and identity/type/count concerns. A new independent CPU-fake v2 packet corrected a DRIVER_LIMIT fixture inconsistency before execution; its controller was syntax-parsed only. [Object receipt](records/root_continuation_20261004/l0_query_measured_repair_object_qa_20261004T2228Z/compile_receipt.json) and [unrun CPU-fake packet](records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/CPU_FAKE_ROOT_REVIEW_PACKET_V2.json) preserve that boundary.

## Intel peer copy CPU fake repair

The original provider peer proposal failed object compilation at five invalid Level Zero error-enum references. A minimal enum correction compiled, allowing CPU-fake tests to reveal unsafe timeout cleanup and lax CLI handling. The fake trace showed **seven teardown calls while work was still pending**, surplus CLI arguments were ignored, and the reported API label was incorrect. These original failures remain intact.

The local repair rejects surplus and duplicate flags before API calls, reports the actual finite synchronization API, and handles an unconfirmed submission by terminal quarantine. Timeout paths flush their result and exit without explicit Level Zero destruction or C++ static destructors. They report `destruction_skipped=true` and `cleanup_verified=false`. This avoids the measured explicit teardown mistake; it does not certify OS/driver reclamation of pending GPU resources.

The source [peer_copy_local.cpp](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/peer_copy_local.cpp) has SHA256 `284e6109f1d32db945ab7719bb77d9a1fc734887c9ebe5068bebc4ac0eef9f59`. Its fake [fake_level_zero_local.cpp](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/fake_level_zero_local.cpp) has SHA256 `96e2f0df7108f1ce31a540c18ae3f50f09b97fa54c5628f8556b86873cbe62d2`. The linked fake executable has SHA256 `1b889f1f11884b8b9d0cd92fb7badd3c6468035cdea8a3a4ac358f6535e27c40`.

Compilation and linking succeeded. The first unrestricted symbol dump exceeded its 128 KiB cap and was refused; that refusal was retained. A distinct filtered inspection then passed: all 24 called Level Zero APIs resolved to internal fake definitions, with ordinary CRT dependencies and no undefined ze/dlopen/dlsym/dlmopen entry points. A receipt hash/path ambiguity was clarified in a separate record rather than overwriting the original.

Actual runtime completed **eleven CPU-fake cases** at their expected statuses and exits:

| Fake behavior | Actual observation |
|---|---|
| Clean payload | 65,536 bytes / 16,384 words, zero mismatches |
| Corrupt payload | Exactly one mismatch at word 8192; FAIL/exit 1 |
| Peer unavailable | NOT_CHECKED/exit 2 |
| Cleanup API failure | FAIL/exit 1 |
| Malformed CLI | Exit 2 |
| Surplus and duplicate CLI | FAIL/exit 1, zero API calls |
| Fill, copy, readback and corrupt wait failures | Last API zeFenceHostSynchronize; pending=1, frees=0, no teardown; quarantine/exit 1 |

The original nine independent receipt methods moved from **4 PASS / 5 FAIL to 9 PASS / 0 FAIL**. Two additional unique methods also passed, including further timeout-stage subcases. The actual unittest execution count was **29**, including **18 duplicate discoveries**. Unique method coverage is **11**, not 29 new controls.

All recorded streams reached EOF with joined readers; no read errors, cap overflow or controller timeout occurred. Fifteen owned Windows processes were reaped and checked absent. Linux/source/artifact and assertion pins remained unchanged. This is synthetic host-malloc apparatus validation. Enumeration errors, changed counts, subdevices, constant-payload weaknesses, stale producer evidence and actual hardware cleanup remain unqualified. No source was promoted and no native Intel loader was invoked.

Evidence: [final peer adjudication](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/FINAL_CPU_FAKE_ADJUDICATION.md), [complete hashes and cases](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/FINAL_CPU_FAKE_ADJUDICATION.json), [runtime receipt](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/stub_runs_20261004T225852Z/receipt.json), [independent assertions](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/independent_assertions_20261004T225900Z/ASSERTION_RECEIPT.json), [original inspection refusal](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/stub_build_20261004T222818Z/BUILD_ADJUDICATION_REFUSED.json), [filtered inspection](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/symbol_inspection_20261004T225008Z/INSPECTION_RECEIPT.json), [residual gaps](records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z/RESIDUAL_GAPS.md).

## Completion adapter QA and review ingestion

The Qwen completion/FD adapter source remains unaccepted at SHA256 `99375e8072f22a7103517e0772f327b232dd3134f1f6820039a42a55f37c017c`. ROOT authored independent pure callback/state/FD controls rather than running the provider's tests. A contradictory initial READY/missing-FD fixture was corrected before execution. The actual v2 run still failed and exposed a separate QA keyword mistake (`detail` versus `message`).

A distinct v3 test source corrected that keyword and allowed observations of a valid producer-wait then host-signal order. The **v3 run executed ten methods, with nine failure events, one error and one passing method**. Multiple failing subtests account for the failure-event count; it is not an eleven-method suite. Important candidate defects remain:

- A callback RuntimeError escapes and cleanup is not attempted.
- READY can be produced with a missing/invalid export FD; the fake EGL import receives `-1`.
- Textual `"false"` is accepted through truthiness in admission/completion handling.
- NaN and infinity are accepted as deadlines.
- A public completion observation can manufacture proof, and mutable event dictionaries weaken retained state.

The valid CPU completion relay ordering was observed; the failure is not a blanket ban on CPU signaling after measured producer completion. The one passing retry control does not establish full reset qualification. No native or GPU calls occurred. The child and outer controller exited 1, were checked absent, readers reached EOF, and pins stayed unchanged.

During v2 reporting, a worker briefly overwrote two pinned review inputs. ROOT restored their exact original hashes from the embedded request before further work, and kept the post-run material separately. The original raw run evidence was preserved. V3 uses distinct files and retains unchanged inputs during its run. This was an evidence-handling correction, not an adapter fix.

Evidence: [v3 inner receipt](records/root_continuation_20261004/l0_egl_adapter_root_qa_v3_20261004T2254Z/runs/pure_qa_20261004T225945Z/receipt.json), [v3 raw test output](records/root_continuation_20261004/l0_egl_adapter_root_qa_v3_20261004T2254Z/runs/pure_qa_20261004T225945Z/stderr.bin), [v3 outer receipt](records/root_continuation_20261004/l0_egl_adapter_root_qa_v3_20261004T2254Z/runs/outer_20261004T2301Z/outer_receipt.json). Inner and outer hashes are `92faffe57bd149289b66323cdb67889b335b429c41855b71bcc94101e6439085` and `c82f4956e43b4928ca3b4d4fdc846eff006eada5ea64011c64312d11d448d292`.

Separately, ROOT repaired Muse terminal parsing. The old parser missed actual terminal `payload.text` and could accept a nonterminal structured review. The original independent suite had four failing cases. The revised parser passed **18/18** controls, including the actual historical terminal format, last-record rules and malformed/ambiguous refusal cases. Its source hash is `fd4be5277c9f6557a3f76d0d0312eae3ca5777b3a9c12aab4e098847653de4e1`. Win32 job containment, time bounds and stream caps were retained. Earlier output-shape refusals were not rewritten as historical passes. [Parser source](records/factory_runs/20261004/muse_l0_collector_prep_20261004T220000Z/parser_revision2/run_muse_collector.root_revision2.py) and [18-case GREEN output](records/factory_runs/20261004/muse_l0_collector_prep_20261004T220000Z/parser_revision2/GREEN.stderr.log) are preserved.

## Actual capability queries and JLink route findings

The WSL CUDA read-only capability query returned API success with support value **0** for device DMA-BUF, host DMA-BUF, GPUDirect RDMA and VMM RDMA. DMA_BUF_MMAP returned INVALID_VALUE, producing overall QUERY_ERROR/exit 1. It created no context/allocation/copy. This is a result for the observed WSL stack, not a universal NVIDIA limitation or a native Windows qualification. [CUDA query summary](records/root_continuation_20261004/external_cuda_capability_query_20261004T2005Z/execution_summary.md).

The exact Windows Level Zero loader DLL loaded, but `zeInit(GPU_ONLY)` returned **UNINITIALIZED / 0x78000001**. Enumeration was skipped. Its cause remains unresolved; this is not a measured driver count. [Loader smoke summary](records/root_continuation_20261004/level_zero_loader_smoke_20261004T2037Z/execution_summary.md).

The combined CUDA/Level Zero proposal failed object compilation at **eight API call sites**. No link or runtime followed. Muse and Gemini supplied request-changes reviews; the combined reviews contained sixteen findings. The Grok combined edit timed out after 600.15 seconds with no delivered patch and unknown usage; its owned process closed, and no automatic retry supplied a repair. [Compile findings](records/root_continuation_20261004/cuda_l0_source_compile_20261004T202000Z_attempt2/compile_qa_findings.md).

Intel device DMA-BUF to NVIDIA Vulkan still has an unresolved export/import contract conflict. An earlier purported native EGL consumer was actually a Python capability query saved with a C++ extension and did not perform the requested full payload experiment. Exporter metadata had additional false-acceptance concerns. These findings remain refusals. [Vulkan route research](records/root_continuation_20261004/intel_device_nv_vulkan_route_20261004T204500Z/RESEARCH.md) and [earlier EGL proposal audit](records/root_continuation_20261004/egl_proposal_independent_audit_20261004T2130Z/audit_findings.md).

The pinned Intel compute-runtime trace at commit `d4fc0756006fa28738766cb66034dc9acadea91e` narrowed actual FD ownership and synchronization behavior. Device-memory import success closes the incoming FD; early failure can leave it retained. The semaphore path treats FD 0 differently, and for positive FDs closes before an ioctl status is known. The inspected underlying wait paths include infinite waits and ignored ioctl errors. A logical DEVICE allocation declaration does not establish physical VRAM backing. [FD trace](records/root_continuation_20261004/l0_fd_sync_bridge_trace_20261004T2115Z/bridge_contract_findings.md).

A corrected candidate route is **CPU_RELAY_AFTER_L0_COMPLETION**: observe bounded actual producer GPU completion, then signal from the CPU without copying the payload through CPU memory. This is a possible serialized experiment. Compatible imports, FD ownership, cache visibility, layout, full payload comparison, backing and transport still need measurements. It is not an asynchronous GPU fence bridge or proof of direct P2P. [Synchronization research correction](records/root_continuation_20261004/dma_buf_sync_bridge_primary_20261004T2144Z/host_relay_correction_addendum.md).

**All methods have not been exhausted.** The work established neither the requested breakthrough nor universal impossibility.

## Native NVIDIA EGL consumer request

The new source-only consumer specification required actual Linux C++17 code using EGL device identity, a 64 KiB imported payload, a 256×64 RGBA8 texture, GPU texelFetch into an SSBO, and a full 16,384-word CPU reference comparison. It also required a producer corruption control, fresh nonce/control socket, finite synchronization, and cache/backing gates. These were requirements in the prompt, not completed experiments.

The actual Qwen `qwen3.8-max` request completed after **1,639.46 seconds** with HTTP 200, DONE, and **finish_reason=length**. It reported **155,407 tokens**: 56,261 input plus 99,146 completion; the 82,758 reasoning tokens are included in completion. Outer exit was 0, its owned process was reaped, and it was not killed. Successful HTTP and process closure did not satisfy the output schema.

The preserved output includes 50,287 content bytes and a complete extracted source string of 43,835 characters. The overall reply is incomplete; the extracted source also exceeds the strict 32 KiB source artifact limit. Both remain explicitly UNACCEPTED_REVIEW_ONLY. Neither was compiled or executed. The proposed next change to a 32,768-token final-reply allowance was **not prepared or launched** because the user stopped the work first.

Evidence: [length postmortem](records/factory_runs/20261004/nv_egl_payload_consumer_prep_20261004T221300Z/LENGTH_POSTMORTEM_REVIEW_ONLY/POSTMORTEM.json), [unaccepted partial content](records/factory_runs/20261004/nv_egl_payload_consumer_prep_20261004T221300Z/LENGTH_POSTMORTEM_REVIEW_ONLY/content.UNACCEPTED_PARTIAL_REVIEW_ONLY.txt), [unaccepted extracted source](records/factory_runs/20261004/nv_egl_payload_consumer_prep_20261004T221300Z/LENGTH_POSTMORTEM_REVIEW_ONLY/source.COMPLETE_STRING_UNACCEPTED_REVIEW_ONLY.txt).

The request used max_tokens=16,384, xhigh effort, thinking enabled, and no thinking_budget. Reported completion minus reasoning is 16,388, near the requested reply bound; this correlation does not prove the service's exact accounting semantics. Official [Qwen3.8-Max limits](https://help.aliyun.com/en/model-studio/qwen3-8-max) and [deep-thinking parameters](https://help.aliyun.com/en/model-studio/deep-thinking) were checked for a possible future request. No larger-reply retry occurred.

## Primary Intel research saved before stop

The [download receipt](records/root_continuation_20261004/intel_multi_arc_ze_peer_research_20261004T230000Z/download_receipt.json) records actual URLs, files and hashes. Saved primary material includes:

- [Intel multi-Arc platform guide PDF](records/root_continuation_20261004/intel_multi_arc_ze_peer_research_20261004T230000Z/intel_863931_rev1p0.pdf), 3,158,833 bytes, SHA256 `8e0f722ea8c7c20674dd80938172d79a78354a0c2ef35c596b203999b826dc90`, from the [official Intel guide](https://cdrdv2-public.intel.com/863931/863931_Platform%20Evaluation%20Guide%20for%20Multi-ARC%20Solution_Rev1p0.pdf).
- Selected official oneapi-src/level-zero-tests files at commit `88447c0abb2ad48bd4fee0b7dbb4ff8b5fcd9e82`, including ze_peer source, shared helpers, headers, kernels and license. [Pinned commit metadata](records/root_continuation_20261004/intel_multi_arc_ze_peer_research_20261004T230000Z/commit_metadata.json).
- Saved [compute-runtime issue 921](records/root_continuation_20261004/intel_multi_arc_ze_peer_research_20261004T230000Z/issue_921.json) and its comments/commit snapshots, from the [official repository issue](https://github.com/intel/compute-runtime/issues/921).

The research agent flagged UINT64_MAX waits and several caller paths that ignore validation return values in the downloaded benchmark. This is a preliminary source finding, not a complete upstream audit; benchmark exit 0 alone would not be an adequate payload parity certificate. The upstream software was not built or executed. The guide's multi-Arc/B60 Pro context does not establish consumer 8 GB Arc support or cross-vendor interoperability. **The intended research report and hardware experiment matrix were not written before stop.** Windows portability, chosen SKUs and direct transport remain NOT_CHECKED.

A pinned source-only Sysman header was also saved for an inventory proposal because the installed SDK lacked zes_api.h. The [saved v1.34.0 header](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/primary/zes_api.v1.34.0.h.txt), from the [official source](https://raw.githubusercontent.com/oneapi-src/level-zero/v1.34.0/include/zes_api.h), has SHA256 `569df31bd158aa479af53c604bc778b41c61e249ad841ea9e977525898991bc4`. It was not installed. The specification treats physicalSize=0 as unknown and does not use deprecated state.size or a logical device allocation as proof of dedicated residency.

## Provider usage and quota

Qwen, Gemini, Grok and Muse were actually used. The [final manager-scoped ledger](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/SCOPED_RESUME_44_CLOSED_USER_STOP_FINAL.json) closes **44 task jobs: 27 with known usage, 17 unknown, totaling 1,878,656 reported tokens**. It is a cumulative scoped ledger with frozen prior receipts, not an exact partition of every account request made during these five hours, a whole-Factory inventory, or a billing total.

| Provider | Closed task jobs | Known usage jobs | Unknown usage jobs | Reported tokens |
|---|---:|---:|---:|---:|
| Qwen | 33 | 21 | 12 | 1,360,280 |
| Gemini | 3 | 3 | 0 | 182,621 |
| Grok | 5 | 3 | 2 | 335,755 |
| Muse | 3 | 0 | 3 | Unknown |
| Total | 44 | 27 | 17 | 1,878,656 |

The separate [Grok capacity correction](records/factory_runs/20261004/grok_capacity_binding_focused_prep_20261004T213535Z/grok_capacity_binding_focused_high.owned_terminal.json) reported **96,597 tokens** and is outside this manager ledger. Earlier six-batch continuation ledgers are separate historical aggregates. They are not added to overlapping cumulative ledgers or presented as a new five-hour usage total. Unknown means unknown, not zero. Reasoning tokens are not added again to completion totals.

The latest Qwen compiler pair used qwen3.8-max and reported **193,042 tokens**. The collector delivered source; the peer repair hit length and supplied no accepted repair. [Pair closure and usage](records/factory_runs/20261004/l0_compiler_two_prep_v2_20261004T214600Z/CLOSED_TWO_QWEN_COMPILER_USAGE_RECEIPT.json). Direct HTTP workers launched **zero native child agents**; authorization for up to ten is not evidence that ten ran. No verified DeepSeek dispatch is recorded in the final scoped ledger.

The global Factory/GPT-OSS selector remained disabled. The Harness used isolated, owned provider calls and ROOT admission; it did not activate the global Factory/Rolex scheduler. Earlier GPT-OSS advisory calls are carry-in evidence, not a new live dispatcher. The user's independently running Muse terminal was untouched.

Latest saved quota observation: **34.4% remaining** on the active 180,000-credit Pro plan, observed at 22:31:15 UTC. The page's last-updated label was October 4 at 18:28:53 and reset label October 6 at 12:00; its time zone was not reported. Approximately 61,920 credits is arithmetic from a rounded percentage. The prior saved observation was 34.7%. The account balance was not refreshed after the stop. Tokens cannot be converted to credits from this evidence, and this work's share of account consumption is unproved. **The quota-consumption objective was not achieved.** [Saved quota observation](records/factory_runs/20261004/QUOTA_UI_OBSERVATION_20261004T2230Z.json).

## Owned jobs closed and work left unrun

At the user stop, only the two inventory-generation requests remained live. They were interrupted through their retained tool sessions, without name-based/PID kill or reattachment:

| Owned request | Retained session | Worker / wrapper PID | Final local state |
|---|---:|---|---|
| Qwen Windows CUDA capability source | 28728 | 85040 / 82664 | Session exit 1; both PIDs absent; no artifact or final usage |
| Qwen Intel Sysman inventory source | 84862 | 68028 / 37264 | Session exit 1; both PIDs absent; no artifact or final usage |

Both had HTTP 200 and reasoning progress but zero content at the last observation. The workers kept SSE in memory until normal termination, so interruption left **no final raw SSE file**. Request metadata and progress are retained; output and usage were not reconstructed. There is no clean EOF/cleanup certificate for these interrupted requests, and local termination does not confirm remote provider cancellation. Their final usage is UNKNOWN.

The [user stop receipt](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/USER_STOP_TWO_OWNED_QWEN_20261004T230832Z.json) and [bounded secret/process audit](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/SECRET_PROCESS_AUDIT_STOPPED_WAVE.json) confirm all four exact owned PIDs absent at the recorded check. The audit checked 58 text files against three configured credential strings and found zero matches; it does not certify every possible credential or external log. All three reporting agents finished and reported no remaining owned runtime processes.

The following preparations remain on disk and **were not launched or executed**:

| Preparation | Last state | File to start a future review |
|---|---|---|
| Completion adapter repair using actual v3 failures | Full source/QA inputs assembled; provider request unlaunched | [V3 request packet](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/qwen_completion_adapter_repair.V3_ROOT_REVIEW_PACKET.json) |
| Reverse NVIDIA Vulkan to Intel Level Zero route | Source-only prompt and API/FD references assembled; unlaunched | [Reverse-route packet](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/qwen_vulkan_nv_l0_intel_reverse_v2.ROOT_REVIEW_PACKET.json) |
| Original Q8 parity diagnostic | Failure context and pinned source assembled; unlaunched | [Q8 packet](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/qwen_q8_original_parity_diagnostic_v2.ROOT_REVIEW_PACKET.json) |
| Grok collector correction after Muse/Gemini | Separate bounded wrapper/prompt packet prepared; unlaunched | [Grok packet](records/factory_runs/20261004/grok_l0_collector_repair_prep_20261004T230400Z/GROK_COLLECTOR_V2_ROOT_REVIEW_PACKET.json) |
| New Qwen collector independent CPU fake | Fixture v2 corrected; controller syntax parsed; no compile/run admission | [CPU-fake packet](records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/CPU_FAKE_ROOT_REVIEW_PACKET_V2.json) |
| Larger final-reply consumer retry | Proposed only; no copy, helper edit or launch | [Stop/preparation index](records/factory_runs/20261004/qwen_five_software_wave_prep_20261004T223400Z/PREPARED_ARTIFACTS_AT_USER_STOP.json) |
| Multi-Arc hardware experiment matrix | Not written | [Primary download receipt](records/root_continuation_20261004/intel_multi_arc_ze_peer_research_20261004T230000Z/download_receipt.json) |

No provider, compiler, GPU test, research/download or factory work was restarted after the stop. Subsequent actions were closure checks and the requested documentation.

## Harness CAD and precursor work carried into this interval

The accepted user constraint is **one integrated four-mount support core, Tetris packing, GPU overhang allowed**. The revision-4 draft places three GPUs upright and one rolled across the top. This is a carried-in CAD draft, not a new mechanical qualification from this five-hour interval. It remains parametric because GPU, PCIe receiver/riser and PSU choices are undecided. Mechanical refinement was deferred while JLink was the priority.

Exact component envelopes, safe contact patches, cable/removal clearance, overhang loads, PETG coupons, slicer strategy, electrical limits and cooling still need qualification. No production print/STL release or physical four-card fit was completed. [Revision-4 native CAD evidence](records/cad_draft_20261004/native_build_revision4_runs.json) preserves the actual draft result and earlier collisions.

The existing Python/GPU precursor and PyRe locations are E:/python_gpu and E:/JE_Horizon. Earlier source-specific OpenCL work demonstrated an eight-layer residual MLP with CPU parity in both NVIDIA/AMD orders using host staging. Separate earlier HIP affine and D3D12/Vulkan transfer/control work remain useful carry-in evidence. They are not credited as new five-hour results or direct peer transport. [Precursor acceptance](records/J_LINK_ACCEPTANCE_20261004.md) and [vendor developer-tool record](docs/08_VENDOR_DEVELOPER_TOOLS.md).

The [recorded host inventory](records/root_continuation_20261004/intel_p2p_inventory_20261004T1820Z.json) contains one RTX 5070 Ti with 16 GB dedicated VRAM and AMD integrated graphics with shared memory; the bounded Windows query observed zero Intel GPUs. Four discrete 8 GB cards are not installed. An adapter listing is not backend peer discovery. No experimental source was promoted into the live PyRe project during this work.

## Evidence preservation and completion requirements

The [219-entry adaptation snapshot](records/ADAPTATION_SHA256_20261004_2148Z.json) passed its recorded integrity check. It is a frozen snapshot, not a current hash inventory for this new handoff or every later candidate. The earlier [Desktop documentation check](C:/Users/thoma/Desktop/status/harness-jlink-status-check-20261004-1841.json) verified 27 local links, 22 numerical evidence hashes, and live/dated equality at that checkpoint. The new verification receipt is separate; no historical manifest or failure receipt was rewritten to imply success.

Several older overview documents still describe intermediate failed numerical states or pending tests. Use the exact later receipt for the exact source/build/fixture, and this stopped-state handoff for navigation. A valid file/hash or complete refusal artifact does not certify that the requested engineering outcome works.

Future completion would require resolving the measured collector/adapter defects, demonstrating a compatible native export/import pair with finite synchronization and full numerical payload comparison, and independently establishing physical backing/residency and transport. Real GPU-producer corruption must be injected before the tested transfer boundary; a host-side comparator mutation is insufficient.

Actual Intel hardware is required to test both Intel–Intel directions and any Intel–NVIDIA candidate. The intended four cards then need matched one-/three-/four-card trials: genuine allocator OOM when insufficient, the same numerical workload passing on four distinct dedicated-memory cards, and measured KV/workspace high-water marks, residency and performance. Harness print/fit/load/thermal acceptance and controlled PyRe integration remain separate requirements.

**No reliable ETA, card-purchase recommendation, direct-P2P claim or full “must work” completion claim is justified. The user requested a stop; these requirements are recorded for a future authorized resume, and no continuation is scheduled.**
