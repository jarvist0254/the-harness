# Preparation: derived F32 model with F32 KV cache

This is a read-only preparation note. No source was changed, no binary was built, and no GPU run was started for this candidate. The current authorized fixture remains the compile-fixed whitelist source at `fixture_model_whitelist/llama_logits_model_whitelist_compilefix.cpp` (SHA256 `bbb705b5419fcc369f8d1eed54e4cae0683899cfdd8d7c1eac2e662881c23c12`) and binary SHA256 `f0657ce0b942d3825bd7cab53cca8cdcd19e4c828a7376c506a68103125246bc`.

The pinned public API exposes `llama_context_params.type_k` and `type_v` as `enum ggml_type` fields in `include/llama.h:395–396`; both are explicitly marked experimental. The pinned default context initializes them to `GGML_TYPE_F16` in `src/llama-context.cpp:3781–3782` and passes them to KV-cache construction at lines 390–391. The cache creates K/V tensors from those types in `src/llama-kv-cache.cpp:233–234` and accounts bytes with `ggml_nbytes` at lines 1914–1931.

Setting both cache types to `GGML_TYPE_F32` is valid for this Qwen3 test. The checked restrictions reject differing K/V types for MLA and DeepSeek4 models and require Flash Attention for quantized V caches; F32/F32 on Qwen3 with Flash Attention disabled triggers neither restriction (`src/llama-context.cpp:3836–3869`). The `type_k`/`type_v` assignments must be made in both fixture contexts: CPU reference (`ctx_params(false)`) and Vulkan target (`ctx_params(true)`). The admitted child environment remains `GGML_VK_DISABLE_F16=1` only.

The existing measured F16-cache baseline used 28.00 MiB per context: CPU K+V 14+14 MiB, and GPU K+V 14+14 MiB distributed as 15 MiB on Vulkan0/NVIDIA and 13 MiB on Vulkan1/AMD. F32 is expected to double that cache storage to approximately 56 MiB per context: CPU K+V 28+28 MiB, GPU K+V 28+28 MiB total, approximately 30 MiB NV and 26 MiB AMD before allocator alignment. The incremental expected storage is about 56 MiB across the two contexts. Existing mixed-device F32 logs show model buffers NV 900.13 MiB, AMD 1373.62 MiB, Vulkan host 593.50 MiB; available device memory was reported as NV 15,227 MiB and AMD UMA/shared 45,960 MiB. This is a planning estimate; runtime stderr must report the actual cache sizes and placement.

The F32 model fixture is `records/models/qwen3_06b_f32_derived/Qwen3-0.6B-Q8_0-dequant-F32.gguf`, SHA256 `bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80`, 2,390,150,816 bytes. Existing matching-context Vulkan baseline remains `f32_default_receipt.json`: 29/29 layer slots offloaded across both devices, all logits finite, 20,558/151,936 outside the unchanged 0.01/0.01 tolerance (max absolute error 0.0629427433, RMSE 0.0149727387). The child-local F16-disabled F32 run remains a separate failure at `f32_f16disable_receipt.json`: 105 mismatches, max absolute error 0.0180931687, RMSE 0.0039858519. Neither result is replaced by an F32-KV experiment.

Before a future build/run, the Grok candidate must be inspected and pass all of these static gates:

- It keeps the exact derived-model path, SHA/size whitelist and metadata checks, 16 token IDs, requested context 128 / actual context 256, batches 32, 4 threads, and 0.01/0.01 tolerance.
- It sets both CPU and GPU context `type_k` and `type_v` to `GGML_TYPE_F32` and exposes those settings in JSON.
- It adds K/V cache types to the C++ canonical workload hash and self-tests that F16 and F32 cache choices produce distinct hashes.
- It leaves the prior Q8_0 and F32 results untouched and does not alter comparison thresholds or precision settings.

The known build template is `fixture_model_whitelist/compile_model_whitelist.cmd`; after admission, copy it to a new fixture directory and change only the source and output executable paths. Compile with the existing VS18 x64 environment and clean pinned headers/libraries. Save source diff/hash, compiler stdout/stderr, exit code, PID cleanup, executable hash, and integrated self-test receipt. Before inference, verify the exact derived model hash/size.

For an admitted run, launch only the default NV→AMD command under the existing direct-child 60-second bound:

```text
llama_logits_kv_f32.exe --model E:\the_harness\records\models\qwen3_06b_f32_derived\Qwen3-0.6B-Q8_0-dequant-F32.gguf --expected-sha256 bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80 --devices Vulkan0,Vulkan1
```

Set `GGML_VK_DISABLE_F16=1` on that child only. Record the fixture C++ workload SHA separately from an outer composite SHA that includes source, binary, model, environment delta, command and context/tolerance fields. Runtime evidence must include JSON logits/finiteness/fail count, full backend stderr, both K/V types and measured per-backend KV buffers, 29/29 layer-placement statement, elapsed/exit, timeout and process absence. If the default does not return clean parity PASS with both GPUs and all expected layers, stop; do not run reverse or corruption controls. A passing result would qualify only this distinct derived-F32/F32-KV workload.
