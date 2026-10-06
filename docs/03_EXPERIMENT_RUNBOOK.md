# Experiment runbook

These recipes are based on the checked-out upstream tree. Verify each binary's --help and --list-devices on the host; device names are examples. Hardware qualification is pending. **Runnable-on-this-host check:** measured population is one discrete RTX 5070 Ti plus one AMD Raphael iGPU on shared system memory, zero Intel GPUs, C:\Windows\System32\ze_loader.dll absent — **directed peer pairs possible: zero**. Phases 2–4 and the integrated four-card release test are designs, not executable steps on this machine. The Windows installed-device smoke and working neural execution sections below ARE executable.

## Phase 0 — Before cards

Run planner tests and all four example JSONs. Review failure cases: total capacity insufficient, an individual layer too large, duplicate physical card aliases, too little workspace/KV reserve. The bounded PyRe source map is in 04_PYRE_INTEGRATION. If further discovery is needed, pass explicit narrow roots and a harness-owned output directory to audit_local_projects.ps1; the README gives that scoped recipe. Map the current scheduler before editing it. Preserve CPU fallback and durable run records.

Inspect upstream docs/build.md, docs/multi-gpu.md, docs/backend/SYCL.md and tools/rpc/README.md in repos/llama.cpp. All commands are tied to records/repositories.json; updating a repository requires revalidating flags and RPC compatibility.

## Phase 1 — One card, one backend

Record exact GPU SKU/VRAM, physical PCI ID, OS, firmware, driver, runtime/compiler and executable hash. Enumerate devices in the chosen runtime and verify negotiated PCIe speed/width under load. Compare a small workload against CPU numerical reference before capacity scaling. Baseline the current 5070 Ti separately; its relocation can change performance.

Requirements: current vendor driver; CMake/C++ toolchain; backend libraries. Windows native and Linux are separate qualification targets. WSL adds another compatibility layer and cannot be assumed to match native multi-GPU behavior.

## Build recipes

From repos/llama.cpp; install backend prerequisites from the upstream docs first.

```text
# Common API, any vendor with supported Vulkan features/operations
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DGGML_RPC=ON -DLLAMA_BUILD_TESTS=ON
cmake --build build-vulkan --config Release -j 4

# NVIDIA native, CUDA toolkit required
cmake -S . -B build-cuda -DGGML_CUDA=ON -DGGML_RPC=ON -DLLAMA_BUILD_TESTS=ON
cmake --build build-cuda --config Release -j 4

# AMD native; Linux example, replace target with actual architecture
cmake -S . -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=<actual-gfx-target> -DGGML_RPC=ON -DLLAMA_BUILD_TESTS=ON
cmake --build build-hip --config Release -j 4

# Intel native; source oneAPI environment first, Linux example
cmake -S . -B build-sycl -DGGML_SYCL=ON -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx -DGGML_SYCL_F16=ON -DGGML_RPC=ON -DLLAMA_BUILD_TESTS=ON
cmake --build build-sycl --config Release -j 4
```

Windows HIP needs its own Ninja/clang/architecture setup from upstream. Windows SYCL can use upstream win-build-sycl.bat or matching released packages. **Plan the Intel arm on Linux.** A Windows SYCL build yields compilation and enumeration only — Windows is unqualified for multi-Arc peer access, so no Windows toolchain can produce an Intel peer-access PASS. Qualified Intel parts are Arc Pro B60/B70 same-generation; consumer Arc B580/B570/A770 are unqualified. The recipes do not install drivers or promise that one toolchain can build every backend in one process. Use separate build directories and environments.

## Phase 2 — All NVIDIA, all AMD, all Intel

Enumerate first, then use returned names explicitly:

```text
llama-cli --list-devices
llama-cli -m <local-model.gguf> --device <device0>,<device1>,<device2>,<device3> --split-mode layer --tensor-split 1,1,1,1 -ngl 99 -c 2048 -n 64
```

Choose a licensed model whose measured load exceeds one card's usable capacity but fits the predicted sharded plan. Start with a smaller model to prove correctness first. Give unequal cards unequal splits based on actual usable memory and measured stage time. Ratio flags are coarse placement hints, not hard byte limits. Inspect logs and peak allocations.

Test at context 512/2048/8192 if supported, one and several active sequences, then repeated cycles. Compare logits/tensors with explicit tolerances; generated prose alone is weak correctness evidence. Quantization and different kernels may cause small drift. Require all cards to own unique model blocks; duplicated models/CPU offload do not satisfy the single-model VRAM-capacity gate.

Probe directed peer access per pair using CUDA/HIP (Level Zero: **Linux only**). The Intel peer tool is **ze_peer from level-zero-tests**, not compute-benchmarks — upstream excludes it on non-UNIX (if(UNIX) add_subdirectory(ze_peer) else() message(WARNING "Skipping ze_peer: test only supported on Linux")) and its source uses fork(), socketpair(PF_UNIX), sigaction() and SCM_RIGHTS. level-zero-tests builds on Windows; **the P2P benchmark inside it does not.** Known tool defect: with -c, per-pair bandwidth is wrong while the total is correct. Do not force P2P when a runtime rejects it; if any directed query is false, that pair is REFUSED — record it, do not attempt copies. **A green Level Zero conformance run proves nothing about cross-card peer access.** Run host/device/device transfer benchmarks at 8 KiB, 1 MiB, 64 MiB and larger supported sizes, both alone and concurrently. Include synchronization and host staging. Store bandwidth, latency and correctness checks. AMD TransferBench is included for this purpose; consult its --help and architecture/build support rather than applying it indiscriminately across vendors.

## Phase 2a — Intel Level Zero peer ladder (Linux only)

Sourced from `10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md` §2.4. This phase is not runnable on the current Windows host: zero Intel GPUs are installed and `C:\Windows\System32\ze_loader.dll` is absent, so directed peer pairs possible here are zero. Directed off-diagonal pairs for n cards = n(n−1): 2 cards → 2, 3 cards → 6, four cards → 12. The Level Zero directed matrix stays at 12 even with the display 5070 Ti installed, because the RTX 5070 Ti is not a Level Zero device and no zeDeviceCanAccessPeer pair involving it can be constructed. Engine-count ceiling: Intel reports two engines per B60 Pro device (one compute+copy, one copy-only), so a 12-flow full mesh on four cards is **not schedulable**; Intel's own four-card example uses exactly 4 flows. Cap concurrency at min(n·E, available engines) and record the engine map from `ze_peer -q` first.

Each tier is gated on the previous one:

1. **Tier 0 capability** — inventory and alias dedup; `zeDeviceCanAccessPeer(A,B)` **and** `(B,A)` recorded separately; `zeDeviceGetP2PProperties` with `ACCESS` and `ATOMICS` recorded separately (`ACCESS=1, ATOMICS=0` permits copies but not remote atomics, which constrains all-reduce design); memory ordinals; engine map; `lspci -vvv` ACS state and host-bridge vendor:ID; negotiated `LnkSta`. If any directed query is false, that pair is **REFUSED** — record it, do not attempt copies.
2. **Tier 1 correctness** — `ze_peer -t transfer_bw -z <size> -o {write,read} -s A -d B -v` at 8 KiB / 4 MiB / 64 MiB / 256 MB, repeated with `--regular_cmdlist`, with `-x src` and `-x dst`, on the copy-only engine, and cross-process with `--ipc`.
3. **Tier 2 performance** — bandwidth write/read, latency, bidirectional (`-b`), multi-engine single target. Calibration only: Intel official B60 Pro Gen5 x8 ≈ 20 GB/s unidirectional, up to 40 GB/s bidirectional, 4-card ring 79.37 GB/s at 512 MB. Third-party B70 behind a Gen4 switch: 28.5 GB/s per direction, 56.5 GB/s bidirectional write, checksum clean.
4. **Tier 3 rings/concurrency (n≥3)** — scatter; all (n−1)! distinct directed rings (2 for n=3, **6 for n=4**); disjoint perfect matchings; bidirectional ring; gather. Intel's own four-card ring is `ze_peer -t transfer_bw --parallel_pair_targets 0:1,1:2,2:3,3:0 -z 134217728 -o write -v -c`. Known tool defect: with `-c`, per-pair bandwidth is wrong while the total is correct — take per-pair numbers from non-`-c` runs.
5. **Tier 4 workload** — `CCL_TOPO_P2P_ACCESS=1 mpirun -np 4 1ccl_benchmark -l allreduce ...`, then `allgather` / `alltoall`, then GEMM sanity.

Mandatory negative controls:

1. **N1** — host-staged two-hop at the same sizes must be **materially slower** (~3 GB/s vs ~28 GB/s peer, ≈9×). If a "P2P" number is at or below the host-staged number, **it is host-staged**; this is the single most important control.
2. **N2** — checksum on every transfer, because `ZE_RESULT_SUCCESS` with 100% corrupt data is a documented reachable state.
3. **N3** — query-vs-outcome consistency in both directions.
4. **N4** — ACS-redirect on/off toggle on the same boot.
5. **N5** — IOMMU on/off.
6. **N6** — `CCL_TOPO_P2P_ACCESS=0` vs `=1`.
7. **N7** — same-device ceiling.
8. **N8** — `NEOReadDebugKeys=1 RenderCompressdBuffersEnabled=0` for D2D, without which Intel documents the bandwidth is **doubled** spuriously.
9. **N9** — cross-generation pair → must refuse.
10. **N10** — iGPU+dGPU pair → must refuse.
11. **N11** — consumer-Arc substitution → expect refusal; establishes whether Arc-Pro scoping is a real capability limit or only a documentation limit.
12. **N12** — single-card `ze_peak` sanity.
13. **N13** — driver-version regression pair across the installer pin and a newer hand-installed NEO.

Also record: a green Level Zero conformance run proves nothing about cross-card peer access. At the pinned commit `88447c0` — whose entire purpose was "Add new zeDeviceCanAccessPeer scenarios" — every P2P conformance test is vacuous for two distinct physical cards: one asserts only `EXPECT_EQ(a2b, b2a)` (symmetry; `false == false` passes), two call `get_p2p_properties` with **no assertion on the result at all**, and the newly added tests assert only the trivial self-peer cases. All `GTEST_SKIP()` when device count < 2. **A full PASS on a single-GPU machine is indistinguishable from a full PASS on a qualified four-card machine.**

## Phase 3 — Mixed vendors using Vulkan

Use one Vulkan build and choose each physical card once. Check supported operations using test-backend-ops; start with the operator set actually used by the selected model. Repeat the same layer-split experiment and record cross-device host-staging traffic. Reject an unsupported operator, invalid output or repeated fallback that defeats the intended capacity test. Compare against each single-card and same-vendor baseline at the same model/quantization/context/batch settings.

## Phase 4 — Mixed native workers through RPC

Use matching commit builds with RPC enabled. On one Windows host, the provided start_rpc_worker.ps1 selects a device and binds to loopback. Example invocations after discovering actual backend names:

```powershell
.\scripts\start_rpc_worker.ps1 -Binary 'E:\the_harness\repos\llama.cpp\build-cuda\bin\Release\ggml-rpc-server.exe' -Device CUDA0 -Port 50052
.\scripts\start_rpc_worker.ps1 -Binary 'E:\the_harness\repos\llama.cpp\build-hip\bin\Release\ggml-rpc-server.exe' -Device ROCm0 -Port 50053
.\scripts\start_rpc_worker.ps1 -Binary 'E:\the_harness\repos\llama.cpp\build-sycl\bin\Release\ggml-rpc-server.exe' -Device SYCL0 -Port 50054
.\scripts\start_rpc_worker.ps1 -Binary '<fourth-card backend RPC binary>' -Device '<fourth distinct physical GPU>' -Port 50055
```

ROCm0 is an example; use the actual name. In another terminal:

```text
llama-cli --rpc 127.0.0.1:50052,127.0.0.1:50053,127.0.0.1:50054,127.0.0.1:50055 --list-devices
llama-cli -m <local-model.gguf> --rpc 127.0.0.1:50052,127.0.0.1:50053,127.0.0.1:50054,127.0.0.1:50055 --device <four returned-RPC-device-names> --split-mode layer --tensor-split 1,1,1,1 -ngl 99 -c 2048 -n 64
```

Select only RPC names so coordinator native aliases do not double-count cards. Confirm startup memory/CPU footprint. Workers must own tensor computation; four whole-model chat servers are a task pool. The fourth worker can use any qualified backend, but must map to a fourth unique physical card. The three named vendor devices are examples, not measured identifiers.

## Windows installed-device smoke — 2026-10-04

The current host has NVIDIA RTX 5070 Ti plus AMD gfx1036 integrated graphics, not four purchased discrete cards. Existing Python has Torch CUDA, CuPy, NumPy and PyOpenCL. No driver/toolkit installation is required for this fixture:

```powershell
python .\j_link\opencl_smoke.py
python .\j_link\opencl_smoke.py --inject-corruption
```

Default runs both AMD-to-NVIDIA and NVIDIA-to-AMD pipelines at 32, 2,048 and 262,144 FP32 elements (largest buffer 1 MiB). Source kernel computes 2*x+1, an explicit host NumPy copy bridges separate contexts, and destination kernel computes 3*x-2. CPU reference is 6*x+1. The corruption command must return FAIL/exit 1; ordinary runs return PASS/exit 0 only on measured parity. Missing pairs return NOT_CHECKED/exit 2.

This is EXPLICIT_HOST_STAGED compute/transfer plumbing. AMD reported memory is shared host memory, not dedicated discrete VRAM. Single smoke timings are not bandwidth/performance qualification. Intel, direct peer DMA and four-card inference are not established.

`--probe-invalid-context` is an optional isolated negative control. This machine's attempted cross-platform single-context creation caused native access violation 0xC0000005; this is a real driver/runtime failure, not a clean API rejection. It is not repeated by default. See immutable OpenCL result records. All probe children have bounded supervision.

The retained `j_link/vulkan_smoke.cpp` also passed a 256 KiB NVIDIA-to-AMD transfer. It uses GPU fill/copy commands and forwards the actual NVIDIA readback through host memory; it does not test compute shaders. The accepted build used VS 18, verified official Vulkan headers in `records/vendor_headers/vulkan_1.4.321/include`, and the import library derived from this host's existing loader in `records/vulkan_smoke_20261004/sdk_link`. Build and run records, including the failing corruption control, are in `revision_3`. Preserve the internal 10-second fence deadline and separate 60-second process supervision when rerunning.

`j_link/d3d12_smoke.cpp` passed a different 256 KiB path: an explicit shared cross-adapter heap, placed buffer resources on NVIDIA/AMD, and a GPU cross-adapter fence handoff. All bytes matched; injected corruption failed at byte 12,345. See `records/d3d12_smoke_20261004/placed_heap_revision/receipt.md` and its VS 18/SDK 10.0.26100 build wrapper. The API requires L0 system memory; returned heap descriptors were recorded, physical residency was not measured. This is not dedicated-VRAM P2P. The earlier committed-buffer E_INVALIDARG is a preserved implementation failure, superseded by this working legal API path. Keep the 10-second completion and 60-second process limits.

Four actual CPU-backed RPC workers also passed the current `j_link/rpc_four_worker_smoke.cpp` fixture. Its four stages and three tensor transfers prove CPU/RPC plumbing only. Windows out-of-source build, commands, output and cleanup are in `records/rpc_four_worker_20261004`. This does not qualify the CUDA/HIP/SYCL/Vulkan worker builds described above.

## Working neural execution experiment

The retained `j_link/opencl_executor.py` runs a deterministic eight-layer FP32 residual MLP across the installed NVIDIA/AMD pair. Each owner uploads its unique assigned weights once before inference; its activations stay in device buffers between local layers. Actual GPU activation bytes cross the vendor boundary through host memory. CPU reference states derive independently from the original input. Each layer's full tensor is compared, and GPU events, weight hashes, ownership and transfer counters are recorded.

```powershell
python -B -m unittest discover -s j_link/tests -v
python -B j_link/opencl_executor.py --output records/my_fresh_mlp_default.json
python -B j_link/opencl_executor.py --reverse --output records/my_fresh_mlp_reverse.json
python -B j_link/opencl_executor.py --inject-corruption --output records/my_fresh_mlp_corruption.json
python -B j_link/opencl_executor.py --policy-mib 1
python -B j_link/opencl_executor.py --device-ids p9:d9
```

Use fresh result paths to preserve previous receipts. Normal and reversed runs require PASS/exit 0. The corruption run must execute the remaining GPU layers, produce a measured final-reference mismatch, report its negative control as detected, and return FAIL/exit 1. Budget refusal is REFUSED/exit 2; a missing device is NOT_CHECKED/exit 2. No runtime discovery or execution happens outside the parent's 60-second child supervisor. The test suite exercises admission before native allocation with mocks; absence of counters in a denial receipt is not a measured zero-allocation result.

The installed pair passed all eight kernels and CPU comparisons in both orders, maximum final absolute error `8.344650268554688e-06` at `atol=rtol=5e-5`. All eight corruption kernels executed; the last four stage comparisons and final parity failed, final error `1.001207709312439`. This is an actual small neural execution result. It is not a GGUF/attention/KV/LLM result, and the AMD device uses shared host memory. See `records/J_LINK_ACCEPTANCE_20261004.md` and `records/opencl_executor_20261004/final_revision/receipt.md` for the final source and logs.

## Real-model Vulkan diagnostic sequence

The clean pinned llama.cpp export now builds a real Vulkan model backend. Qwen3-0.6B Q8_0 executes with 29/29 layer slots offloaded across NVIDIA and AMD, but both vendor orders fail the fixed provisional per-logit gate `abs(gpu-cpu) <= 0.01 + 0.01*abs(cpu)`. Independent single-device runs also fail, so the mixed-device transport is not established as the sole cause. All 151,936 last-token logits are finite. Keep these failures; successful loading or generated text does not establish parity.

A separate CPU-dequantized F32 GGUF has a distinct path, SHA256 and representation. It also fails with default Vulkan settings. With child-local `GGML_VK_DISABLE_F16=1`, mismatches decrease from 20,558 to 105 of 151,936; maximum absolute error is about 0.0180932 and RMSE about 0.00398585. The unchanged comparator still refuses it. The requested context is 128, but this pinned runtime pads it to an actual 256; both values are included in the fixture identity. Exact inputs, commands, hashes, placement logs and process bounds are under `records/vulkan_llm_qualification_20261004`.

The subsequent diagnostic requested F32 for both K and V caches in both CPU-reference and GPU contexts, retaining the model, tokens, batching, device pair and tolerance. Its source passed independent static admission, a clean compile and GPU-free self-test before bounded execution. Actual runtime logs confirm F32 cache types and 29/29 offloaded layer slots. This baseline still failed on 34/151,936 logits, maximum error 0.0176945 and RMSE 0.00361094; see `records/vulkan_llm_qualification_20261004/f32_kv_f32_baseline_receipt.json`.

A further one-factor child-local `GGML_VK_DISABLE_FUSION=1` experiment retained F32 weights/KV and `GGML_VK_DISABLE_F16=1`, the same binary and workload, and the unchanged comparator. It still failed on 21/151,936 logits, maximum error 0.0164737 and RMSE 0.00349164. The process exited 1 in 7.565 seconds, without timeout, and was absent afterward. See `records/vulkan_llm_qualification_20261004/f32_disable_fusion/baseline_receipt.json`. These are diagnostic failures, not an accepted model configuration. No reverse-order or comparator-corruption follow-up was run after these failed baselines.

The same pinned source `2aff3925329a8ca6ca4834f665a8ed07acb1d3e341f73908dfecb3989057c371`, binary `d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4` and derived F32 model were also tested separately on each GPU with F32 KV, F16/fusion disabled, the same sixteen tokens and the unchanged tolerance. Both single-device runs executed all 29 offloaded layers and produced finite logits, but failed parity:

| Diagnostic population | Mismatches / 151,936 | Maximum absolute error | RMSE |
|---|---:|---:|---:|
| NVIDIA `Vulkan0` only | 47 | 0.0196537971 | 0.00389753967 |
| AMD `Vulkan1` only | 3 | 0.0149828196 | 0.00281893771 |
| NVIDIA + AMD, with cooperative matrices also disabled | 3 | 0.0142855644 | 0.00284758023 |

The last row additionally set child-local `GGML_VK_DISABLE_COOPMAT=1` and `GGML_VK_DISABLE_COOPMAT2=1`, retaining `GGML_VK_DISABLE_F16=1` and `GGML_VK_DISABLE_FUSION=1`. It exited 1 without timeout in 5.562 seconds. Logs reported all 29 offloaded layers, split 15/14 between NVIDIA/AMD, and F32 KV. The lower mismatch count does not establish an accepted model or prove the cause of the remaining error. No reverse-order or corruption follow-up was admitted after this failed baseline. Exact metrics, inputs, placement and environment-inclusive identities are in [single-device results](../records/vulkan_llm_qualification_20261004/f32_single_device_disable_fusion/fixture_result_report.md) and [cooperative-matrix-disabled results](../records/vulkan_llm_qualification_20261004/f32_disable_cooperative_matrices/result_report.md). Driver memory and model-buffer logs are not physical-residency, direct-P2P or four-card-capacity proof.

The proposed intermediate-capture collector has no complete provider-generated C++ candidate: its Qwen implementation request timed out and the one authorized retry was truncated. The Python artifact comparator is a separate pure diagnostic component. Raw Grok revision `2786a0213039cdeb1654dd1de7688e9f628672a963355fcfef6ebe94cba87495` passed the original 62 controls but failed three additional malformed-input controls. Root repaired `_canonical_name` and `_validate_expected`; revision `e383241176f39fea1697857275148664406d6b012990458841201e1a1f5b4b21` passed all 65 independent synthetic controls with zero forbidden calls. See [independent review](../records/provider_quality_review/layer_diagnostic_rootQA_20261004T151531Z/INDEPENDENT_REVIEW.json). This does not establish a native collector, GPU execution, authenticated origin or model parity. Opened-handle identity binding and dynamic rename/reparse races remain unchecked. Diagnostic capture changes graph batching/fusion and must be labelled intrusive; distinguish the first observed numerical difference from the first fixed-tolerance violation.

Further diagnostics need a source-backed hypothesis, an explicitly recorded factor and an experiment identity covering the child environment. Run reverse order and logit corruption only after a clean baseline passes. A logit perturbation tests the comparator; it does not test corruption in the inter-device transport. Any later F32 result is scoped to that representation and cannot supersede the original Q8_0 failure or prove four-card capacity. Do not widen the fixed tolerance to manufacture acceptance.

### FP32 staging operator baseline and pending patch

The revision-2 original-build `Vulkan0` operator fixture produced a valid six-case numerical RED: 10,240 of 12,288 finite outputs violated the fixed gate `2e-5 + 2e-6*abs(double_reference)`. The contiguous case had zero failures; each of the five noncontiguous layouts failed all 2,048 comparisons. It exited 1 in 1.281 seconds without assertion, timeout, truncation or pin changes. See [original-build result](../records/root_continuation_20261004/fp32_staging_operator_fixture_revision2_20261004T155012Z/runtime_original_RED_20261004T155418Z/RESULT.md) and its independent adjudication. This discriminates the original staging behavior; it does not establish the cause of the three remaining whole-model logit failures.

The sixth closed isolated provider batch supplied a three-region source patch through Qwen implementation, Gemini static review and Grok editing. It changes only the all-F32/no-FP16/no-cooperative-matrix type selection and X/Y staged byte counts, preserving the quantized Y formula. The final JSON patch is still unapplied and awaiting ROOT runtime admission; no patched operator or model result is claimed. See [batch ledger](../records/factory_runs/20261004/fp32_staging_repair_20261004T153127Z/USAGE_FINAL_SIXTH.json) and [staged patch](../records/factory_runs/20261004/fp32_staging_repair_20261004T153127Z/grok_fp32_patch/patch.pending_root_qa.json). The global Factory remains off, and no provider jobs remain running.

## Cross-vendor capability and research boundary

The [primary-source research record](../records/root_continuation_20261004/cross_vendor_research_20261004T150959Z/RESEARCH.md) describes explicit AMD/NVIDIA heterogeneous pipeline training on an enterprise two-node GPU/DPU population, Linux DMA/RDMA implementations, and vendor-specific DirectGMA paths. **AMD PeerDirect is Instinct MI300X/MI200/MI100 only — consumer Radeon is excluded**; there are no official AMD consumer RDMA peer experiments. The heterogeneous-training finding is **delegated, not independently re-verified**: its device-direct path is **GPUDirect RDMA over BlueField-3 DPUs**, not PCIe peer-to-peer — "without host-memory staging" ≠ "direct VRAM peer access." Verify the arXiv ID before citing. Those configurations do not qualify this Windows consumer host, Intel hardware, direct peer access or pooled VRAM. Public author code for the heterogeneous training paper was not found within the documented search bounds; linked dependencies are not that implementation.

The bounded `vulkaninfoSDK.exe` query timed out at 30.032 seconds; its partial result remains [historical evidence](../records/root_continuation_20261004/external_memory_capability_20261004T144953Z/capability_result_report.md). A different root-admitted exact-property query completed in 0.297 seconds, exit 0. Both installed NV/AMD GPUs advertise HOST_ALLOCATION importability and 4096-byte alignment; both return no HOST_MAPPED_FOREIGN_MEMORY features for transfer-only and storage-plus-transfer buffers. Measured feature mask 0x0 on both installed GPUs. This is one of the five genuinely open items — re-query on every driver update; the check is cheap (doc 10 §1.9 item 4). No Intel device was enumerated. [Exact result and pinned receipt](../records/root_continuation_20261004/external_memory_exact_query_20261004T152518Z/runtime_20261004T153645Z/runtime_findings.md) preserve the full matrix. No logical device, allocation, import or transfer occurred. Ordinary-host imports remain unexecuted; OpenCL external-handle support remains NOT_CHECKED. Any later import experiment needs separate bounded admission, valid backing, pointer-specific memory-type queries, lifetime/ownership/synchronization, full parity and meaningful corruption controls. Shared system backing must not be reported as direct VRAM P2P.

No Intel GPU is present (exhaustive scan including hidden and disabled: zero devices). Intel/NVIDIA direct P2P is not "unproven pending a breakthrough" — it is **SETTLED-UNSUPPORTED**: architecturally excluded on Windows by specification, and gated shut on Linux consumer desktops by the p2pdma whitelist. Eight areas are settled; do not spend further budget there. Five items remain genuinely open, all Linux-only and research-grade. The four external card SKUs remain undecided. Keep the CAD parametric; hardware selection and purchasing are not resolved by these measurements or research.

## Integrated four-card release test

These are proposed qualification steps, not completed hardware results. Freeze counts, durations and component-specific limits in a run manifest before executing; preserve failed receipts rather than rerunning until one appears green.

1. Freeze source, binaries, model hashes, OS/drivers and card SKUs. Map A–D to four unique physical GPUs and receiver links. If A–D are four motherboard-bifurcated x4 branches, they are four **separate root ports** and will NOT form a P2P domain (PCI_P2PDMA_MAP_NOT_SUPPORTED) — each branch must independently pass the peer gate, and that gate is the **kernel's chipset allow-list plus BIOS ACS/IOMMU state, not the presence of a PCIe switch**. On an AMD Zen host (`family >= 0x17`), which this AM5 host is, the allow-list passes with no switch and ACS redirect disabled; a switch is only required where the root complex is *not* allow-listed (notably consumer Intel desktop chipsets). Also expect roughly half the peer bandwidth on x4 branches: every verified-working Intel rig uses x8 links, and Intel's ~20 GB/s unidirectional / 40 GB/s bidirectional calibration is for Gen5 x8, so two cards on x8/x16 will out-peer four cards at x4 while four x4 cards hold more aggregate capacity. Prefer four **same-vendor** cards — for pooled capacity they strictly dominate any mixed-vendor population. Record dedicated capacity, observed free memory and measured peak allocations per card. Keep the host/display 5070 Ti separate from this four-card result; exclude AMD integrated shared memory from purchased VRAM totals.
2. Qualify the small computation on all four cards first. Supply four independently discovered runtime IDs to the command below, then repeat with `--reverse` and, for mixed vendors, `--inject-corruption`. Require every card to own unique resident layers, actual completed kernels on all owners, independent tensor parity, and correct host-staging counters. Repeat the same width/layers/policy with only three IDs and require modeled capacity refusal. Same-vendor corruption is refused because this control specifically targets a vendor boundary.

   ```text
   python -B j_link/opencl_executor.py --device-ids <A> <B> <C> <D> --width 512 --batch 8 --layers 16 --policy-mib 9 --output <fresh-result.json>
   ```

   This demonstrates modeled blocks of 32 MiB versus three 8 MiB layer budgets. Actual weights total only `16,809,984` bytes. Bounds of width 512, sixteen layers, policy 64 MiB and combined model buffers below 32 MiB deliberately prevent an 8 GB physical-capacity test.
3. Establish real capacity with a separate qualified model runtime. Use a hashed licensed local model, fixed quantization/context/batch and supported operators. Its measured unique device-resident requirements must exceed the largest single card's usable dedicated memory while fitting the four-card plan. Require the identical one-card configuration to refuse capacity and the four-card configuration to pass, with no CPU layer/offload fallback or whole-model replication. To prove that the fourth card is necessary, additionally choose a measured workload exceeding the three-card usable budget and verify three-card capacity refusal. Do not substitute planner estimates, output prose or artificial policy caps for these measurements.
4. Qualify required operations and directed transfers on the pinned runtime builds. Capture tensor/logit tolerance, peak memory, actual transport, latency and throughput against single-card and same-vendor baselines. Use only returned physical/backend or RPC device names. Four CPU workers do not satisfy this gate.
5. Exercise bounded failure controls before extended loading. Stop one owned RPC worker while an inference is active, cancel a coordinator run, request a policy refusal, and exercise allocator failure through a mock or isolated small allocation fixture; never deliberately exhaust the desktop's shared memory. Require explicit failed state, no partial-success receipt, owned-process/port cleanup and release of leases. Restart from a documented committed boundary and verify which state is replayed. This small executor has no durable restart or worker-recovery contract; those tests remain future integration requirements.
6. Qualify the actual integrated core and electrical path. Measure PSU/receiver/connector/fastener geometry and removal paths; print fit/load coupons before the continuous core. Record component masses, supported overhang, total printed mass, actual cable bends, simultaneous startup/load and connector/support temperatures. Require four links to remain stable under simultaneous computation. A proposed initial sequence is twenty cold-start/load/cleanup cycles followed by a two-hour steady mixed load, with logs sampled every second. Stop on a parity error, link reset, connector damage, unsafe measured temperature or a component's documented limit. These durations are test-design choices, not completed endurance results; select thermal/load thresholds from the final components and filament data before testing.

## Qualification matrix and pass conditions

| Gate | Required evidence |
|---|---|
| Discovery | Stable physical identity; no duplicate backend aliases |
| Allocation | Measured peak per-device use; reserved space; no double-counted shared host memory |
| Larger model | Unique weight/KV ownership on multiple cards; larger than one card's budget |
| Numerical correctness | Fixed tensor/logit fixtures; tolerance, dtype and quantization recorded |
| Transfer | Directed matrix — n(n−1): 2→2, 3→6, 4→**12**; **20 only for a mixed-vendor host-staged matrix**, since the 5070 Ti is not a Level Zero device. Sizes, concurrency, synchronization. **Checksum on every transfer** (ZE_RESULT_SUCCESS with 100% corrupt data is a documented reachable state). **Mandatory host-staged negative control N1**: if a "P2P" number is at or below the host-staged number it IS host-staged (≈9× gap expected). Query-vs-outcome consistency both directions; ACS-redirect and IOMMU on/off toggles; CCL_TOPO_P2P_ACCESS=0 vs =1; same-device ceiling; cross-generation and iGPU+dGPU pairs must refuse; NEOReadDebugKeys=1 RenderCompressdBuffersEnabled=0 for D2D or Intel documents the bandwidth is spuriously doubled |
| Useful performance | End-to-end load, prefill, decode, latency and throughput against baselines |
| Failure | Worker exit, OOM and cancellation lead to explicit failed/retryable state |
| Durability | Terminal loss/restart preserves only committed completed work; in-flight replay specified |
| Thermal/electrical | Links stable, connectors/support temperatures qualified, load/stability checks |

A failed worker's KV cache may be lost; never claim transparent session recovery without checkpoints/replay. Reject or retry from a documented boundary. For PyRe admission, the initial release can queue or reduce context rather than crash or pretend unused memory exists.

Use records/benchmark_template.json for future results. Null fields mean unmeasured. Record separately: display card relocation, CPU-root vs chipset path, driver versions, quantization, batch/context/sequence count and software hash. No hardware PASS is implied by CPU planner or RPC smoke tests.
