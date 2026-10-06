# Single-device F32/KV-F32 diagnostic summary

Status: both GPU executions completed and met runtime placement/input gates; both failed the declared numeric parity tolerance. These are diagnostic results, not qualification passes.

The sequential runs used the same pinned llama.cpp executable and derived F32 model, with `--kv-f32`, tokens 0–15, requested context 128 / actual context 256, batch and ubatch 32, 4 CPU threads, flash attention disabled, and `atol=rtol=0.01`. Child-only environment overrides were `GGML_VK_DISABLE_F16=1` and `GGML_VK_DISABLE_FUSION=1`; the parent's corresponding Vulkan flags remained unset. Each run had a 60-second deadline. Neither timed out; each retained process exited, was reaped, and was absent after wait. Source, executable, model, Python, and runner hashes were unchanged before and after.

| Device | Result | Parity metrics | Layer/device evidence | Composite experiment SHA-256 |
|---|---|---|---|---|
| `Vulkan0`, NVIDIA GeForce RTX 5070 Ti | `NUMERIC_PARITY_FAIL`, exit 1, 5.797 s, PID 91440 | 47 / 151,936 mismatches; max abs 0.0196537971; RMSE 0.00389753967; CPU and GPU logits finite | 29/29 layers offloaded and individually logged; F32 K/V; 56 MiB KV buffer (28 MiB each K/V); model buffer 2,273.75 MiB | `b3056a95f4d28547e96a52c8247325d7bb88a35cd1f97086ef043e83bb916f0b` |
| `Vulkan1`, AMD Radeon(TM) Graphics | `NUMERIC_PARITY_FAIL`, exit 1, 9.469 s, PID 56256 | 3 / 151,936 mismatches; max abs 0.0149828196; RMSE 0.00281893771; CPU and GPU logits finite | 29/29 layers offloaded and individually logged; F32 K/V; 56 MiB KV buffer (28 MiB each K/V); model buffer 2,273.75 MiB plus 593.50 MiB Vulkan host buffer | `e5b2aaf824cf3838023c27518887d5e9b4d3d8e4b62e47ecf99b5b9dc2102c81` |

Pinned inputs: source `2aff3925329a8ca6ca4834f665a8ed07acb1d3e341f73908dfecb3989057c371`; executable `d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4`; derived model `bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80` (2,390,150,816 bytes). The C++ workload hashes are `cdbdb8530e40fa03f667e060ca1b8b41fa620a3b903ef0a80b9dfecb2b11dd22` (NVIDIA) and `1310bdd77212d9f56e7184bda7bb39c1d2ad45be56e95621cdba216a63f5375a` (AMD).

Raw stdout, stderr, static manifests, composite identities, and per-run JSON receipts are preserved in `NV/` and `AMD/`. Runtime-reported free memory before model allocation was 15,227 MiB for NVIDIA and 45,960 MiB for AMD; these are driver-reported values, not dedicated-residency proof. No post-run GPU free-memory sample was taken. This pair establishes only that both single-device paths executed all 29 layers and produced finite outputs that exceeded the declared tolerance; it says nothing about cross-vendor transport, P2P, physical VRAM capacity, or production readiness.
