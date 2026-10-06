# Experiment runbook

These recipes are based on the checked-out upstream tree. Verify each binary's --help and --list-devices on the host; device names are examples. Hardware qualification is pending.

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

Windows HIP needs its own Ninja/clang/architecture setup from upstream. Windows SYCL can use upstream win-build-sycl.bat or matching released packages. The recipes do not install drivers or promise that one toolchain can build every backend in one process. Use separate build directories and environments.

## Phase 2 — All NVIDIA, all AMD, all Intel

Enumerate first, then use returned names explicitly:

```text
llama-cli --list-devices
llama-cli -m <local-model.gguf> --device <device0>,<device1>,<device2>,<device3> --split-mode layer --tensor-split 1,1,1,1 -ngl 99 -c 2048 -n 64
```

Choose a licensed model whose measured load exceeds one card's usable capacity but fits the predicted sharded plan. Start with a smaller model to prove correctness first. Give unequal cards unequal splits based on actual usable memory and measured stage time. Ratio flags are coarse placement hints, not hard byte limits. Inspect logs and peak allocations.

Test at context 512/2048/8192 if supported, one and several active sequences, then repeated cycles. Compare logits/tensors with explicit tolerances; generated prose alone is weak correctness evidence. Quantization and different kernels may cause small drift. Require all cards to own unique model blocks; duplicated models/CPU offload do not satisfy the single-model VRAM-capacity gate.

Probe directed peer access per pair using CUDA/HIP/Level Zero. Do not force P2P when a runtime rejects it. Run host/device/device transfer benchmarks at 8 KiB, 1 MiB, 64 MiB and larger supported sizes, both alone and concurrently. Include synchronization and host staging. Store bandwidth, latency and correctness checks. Intel compute-benchmarks and AMD TransferBench are included for this purpose; consult their --help and architecture/build support rather than applying them indiscriminately across vendors.

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

## Integrated four-card release test

These are proposed qualification steps, not completed hardware results. Freeze counts, durations and component-specific limits in a run manifest before executing; preserve failed receipts rather than rerunning until one appears green.

1. Freeze source, binaries, model hashes, OS/drivers and card SKUs. Map A–D to four unique physical GPUs and receiver links. Record dedicated capacity, observed free memory and measured peak allocations per card. Keep the host/display 5070 Ti separate from this four-card result; exclude AMD integrated shared memory from purchased VRAM totals.
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
| Transfer | Directed matrix, sizes, concurrency, synchronization; checksums/parity |
| Useful performance | End-to-end load, prefill, decode, latency and throughput against baselines |
| Failure | Worker exit, OOM and cancellation lead to explicit failed/retryable state |
| Durability | Terminal loss/restart preserves only committed completed work; in-flight replay specified |
| Thermal/electrical | Links stable, connectors/support temperatures qualified, load/stability checks |

A failed worker's KV cache may be lost; never claim transparent session recovery without checkpoints/replay. Reject or retry from a documented boundary. For PyRe admission, the initial release can queue or reduce context rather than crash or pretend unused memory exists.

Use records/benchmark_template.json for future results. Null fields mean unmeasured. Record separately: display card relocation, CPU-root vs chipset path, driver versions, quantization, batch/context/sequence count and software hash. No hardware PASS is implied by CPU planner or RPC smoke tests.
