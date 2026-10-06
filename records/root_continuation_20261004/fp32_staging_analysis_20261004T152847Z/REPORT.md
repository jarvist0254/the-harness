# F32-preserving noncontiguous Vulkan staging: proposed narrow experiment

## Binding and scope

The analyzed clean source is pinned commit `0faee5004297c3bcfa40b7bf11750127b8c1fd7d`. Its ggml-vulkan.cpp SHA-256 is `86c7d9251ecddff54f6a53956cfd22c94ef9090064789b7a362d56cb1b3cadef`, matching the clean manifest; that manifest matches recorded provenance hash `ca13617b918efe05af725be2faae155649932598fea2e5f9f61be50234a5ec6a`. The CMake cache selects this clean source directory. The fixture compile command links libraries from that build and includes these headers. Compile receipt source `2aff3925…57c371` and binary `d9034fe8…bf44c4` match the latest mixed-run receipt and current fixture bytes. The run declares the same pinned commit. This is a consistent recorded source/build/fixture chain, not independent reproducible-build proof or a captured runtime library-load trace. Historical archive and every compiled object were not revalidated.

Latest baseline: f32_disable_cooperative_matrices/baseline/run_receipt.json (the proposed receipt.json filename does not exist). Same F32 model, F32 KV, NVIDIA then AMD, all 29 reported GPU layer assignments, F16/FUSION/COOPMAT/COOPMAT2 disabled. Numeric failures3, max absolute error0.014285564422607422, RMSE0.0028475802273649183, all151936 logits finite. Nothing here establishes which branch executed or that staging caused those failures. No source mutations, builds or model runs occurred.

## Source-backed behavior

In ggml_vk_mul_mat_q_f16 (6270 onward), x_non_contig includes !dim01_contiguous even with coopmat2 off (6316–6317). The local staging type is F16 except BF16 source0 (6319). y_non_contig also includes !dim01_contiguous independently of cooperative matrices (6333–6339). y_f32_kernel becomes false when Y is noncontiguous (6341). Pipeline lookup and the qx fallback therefore select F16 staging/multiply types (6345–6353), and copy pipeline lookup explicitly requests that staging type (6389–6399).

Disabling device->fp16 controls compute capability/pipeline creation (4272–4274), not this local staging-type decision. The no-FP16 shader branch still creates F32/F32 and mixed F16/F32 input pipelines with FP32 arithmetic (2737–2742). Thus FP32 arithmetic does not by itself mean intermediates never round to F16 storage. Existing F32→F32 copy pipelines are available (6061–6066;3283), generated with float input/output (vulkan-shaders-gen.cpp866). The generic copy shader preserves values through float assignment and uses tensor stride indexing.

The vector helper already requests same-type noncontiguous copies (6681–6685); do not change it merely because its variable names contain fp16. Main dispatch selects vector paths for small output-column counts and otherwise the matrix helper (7295–7300). MUL_MAT_ID has analogous conversion logic (7369–7447), but dense Qwen3 execution of that path is unproven and a separate change would broaden this experiment.

## Exact narrow patch specification for Qwen, then Gemini/Grok review

Change ONLY ggml_vk_mul_mat_q_f16 in a fresh derived source tree. Preserve all original clean source and compiled artifacts.

1. Define a precision-preservation predicate for this admitted diagnostic: source0 and source1 are both GGML_TYPE_F32, device->fp16 is false, and both device->coopmat_support and device->coopmat2 are false. Keep legacy behavior for all other type/capability combinations. Do not route unsupported cases to CPU math or silently widen eligibility.
2. Under that predicate, choose the existing local staging type as GGML_TYPE_F32 instead of GGML_TYPE_F16. Otherwise retain BF16/F16 selection exactly. Renaming f16_type/to_fp16 variable names is optional clarity only; do not implement the change as a comment-only rename.
3. Keep x_non_contig/y_non_contig and qx/qy staging admission true where required: noncontiguous F32 must still be copied to contiguous scratch. Do NOT set these flags false to avoid conversion, because that bypasses necessary layout handling. Existing map lookups then select F32/F32 keys both before and after x staging; copy lookup selects cpy_f32_f32. Keep the missing-map/pipeline assertions; no F16 or CPU fallback inside this predicate.
4. Update BOTH scratch size formulas alongside the type: staged x_sz = ggml_type_size(selected_staging_type)*x_ne; staged non-quantized y_sz = ggml_type_size(y_f32_kernel ? GGML_TYPE_F32 : selected_staging_type)*y_ne. Direct X qx_sz remains type_size(src0)*x_ne/block_size(src0); direct Y qy_sz remains type_size(src1)*y_ne/block_size(src1). Leave quantize_y's Q8_1 size/alignment formula unchanged. Under the predicate, no F32/Q8_1 map exists, so quantize_y lookup falls back false; assert this in diagnostic coverage rather than assuming every hardware configuration.

| Quantity | F32-preserving predicate |
|---|---|
| x_ne | product of source0 dimensions |
| padded_n | qy staging ? round up ne11 to selected pipeline wg_denoms[1] : ne11 |
| y_ne | padded_n * ne10 * ne12 * ne13 |
| X staged bytes | 4*x_ne; prior conversion used2*x_ne |
| Y staged bytes | 4*y_ne; prior conversion used2*y_ne |
| destination bytes | 4*ggml_nelements(dst), unchanged |
| split-K scratch | destination bytes*split_k, unchanged |
| direct descriptor input ranges | ggml_nbytes(src0/src1), retaining actual strided extent |
| staged descriptor ranges | x_sz/y_sz, updated together with physical scratch size |

5. Preserve size-limit rejection and preallocation maxima (6407–6425), descriptor reservations (6428–6439), scratch buffer size assertions (6464–6478), exact descriptor ranges (6521–6522) and all offsets. Scratch X/Y start at offset0; source offsets remain vk_tensor_offset+view_offs or UMA host mapping offsets. Do not replace strided input extents with logical element bytes.
6. Preserve copy push constants and packed destination strides from ggml_vk_cpy_to_contiguous (6178–6196), including its post-copy sync. Preserve pre-reuse sync flags, Y cache keyed by actual copy pipeline pointer/tensor/K-padding state (6492–6504), and post-multiply scratch reuse flags (6546–6550). An F32 copy pipeline pointer naturally differs from the F16 pipeline; do not weaken this cache identity. Keep dimension/batch strides in elements and the original matmul/split-K dependencies. ggml_vk_sync_buffers resets scratch reuse flags and emits pipeline memory barriers covering shader/transfer read/write accesses on the command queue (1149–1170); preserve that dependency rather than adding host waits. Padding beyond copied Y's actual rows remains the pre-existing algorithm's guarded-tile behavior; do not invent a zero-fill or alter padded_n without separate shader evidence.

A change only to copy destination type is incorrect: matmul types, byte counts and descriptor ranges would disagree. A change only to sizeof(float) is also incorrect: F16 copies would write a half-sized payload subsequently misinterpreted.

## Bounded next experiment, not yet executed

First review the exact derived diff and source hashes. Build into a new isolated output directory using the same pinned clean archive and SDK/configuration. Rebuild the affected Vulkan library and relink the identical fixture source against that new build; record all source/manifest/configuration/library/executable hashes. Verify the fresh binary actually selects the fresh build artifacts, not old libraries from search paths. Preserve the old3-failure baseline.

Before a model run, admit bounded GPU operator probes for actual F32 noncontiguous X only, Y only, both, and contiguous control, using an independently computed CPU reference outside the GPU execution path. Include transposed/strided batched inputs and values that discriminate F16 rounding (e.g.1.0001), record selected pipeline types and staged byte sizes, and require finite results and fixed tolerance. No CPU runtime fallback may perform the GPU path. Quantized/F16/BF16 paths are untouched and separately regression-tested if changes spill beyond the predicate. Native probe execution needs root admission.

Then run only the same mixed baseline command under the same four child-local disable flags, --kv-f32, ordered Vulkan0,Vulkan1, layer split[1,1], requested context128/actual256, batch/ubatch32, threads4, tokens0–15, flash attention disabled, the same2,390,150,816-byte model hash, and atol=rtol=.01. Owned hidden process60-second cap, bounded logs and cleanup. Fresh composite experiment identity must include patched source/build hashes in addition to unchanged workload/model/environment. Record all151936 finite comparisons, count, max error, RMSE, actual requested/observed offload and selected devices; AMD shared memory remains unqualified dedicated VRAM.

Stop on missing artifact binding, unexpected CPU placement/fallback, timeout, nonfinite output, wrong workload or numeric failure. Do not run reverse order or corruption until baseline passes. If it fails, preserve the exact failure and investigate another hypothesis; do not claim this path explains residual errors. This is numerical diagnosis, not four-card capacity, P2P, throughput or production qualification.
