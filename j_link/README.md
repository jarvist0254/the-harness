# J-Link prototype scope

The full four-card goal is still active; the following accepted small fixtures do not complete it. See `../docs/09_FULL_GOAL_GATE_REGISTER.md` for the full gate register. The later real-model Vulkan fixture currently fails numerical parity and is recorded separately under `records/vulkan_llm_qualification_20261004`.

planner.py is a pure capacity partitioner. It has no hardware discovery or allocation authority. Four example profiles model all-NVIDIA, all-AMD, all-Intel and mixed populations with hypothetical capacities. Block sizes include model-specific memory estimates, not a universal bytes-per-layer formula.

Current profiles contain four external hypothetical 8 GB cards, each with a 6,656 MiB modeled budget after 1,024 MiB reserve and 512 MiB workspace. The 24,576 MiB synthetic workload fits four but fails with three. The host/display 5070 Ti is excluded unless supplied as a distinct fifth physical device. No example is a measured GGUF/KV budget.

`opencl_executor.py` is the experimental single-workload executor. It computes eight deterministic FP32 residual MLP layers (`relu(x + x @ W + b)`, width 512, batch 8) using unique resident weights across separate NVIDIA and AMD OpenCL contexts. Activations remain in device ping-pong buffers within each owner's stage; actual GPU readback is forwarded through bounded host memory at a context boundary. Every layer is also read back for an independent CPU comparison, so this diagnostic mode is not a performance benchmark. Each weight is uploaded once before the first kernel. It is separate from the earlier transfer probes below.

```powershell
python -B j_link/opencl_executor.py --output records/my_fresh_default_result.json
python -B j_link/opencl_executor.py --reverse
python -B j_link/opencl_executor.py --inject-corruption
python -B -m unittest discover -s j_link/tests -v
```

Default discovery requires actual NVIDIA and AMD GPUs. `--device-ids` accepts one through four discovered GPU IDs; physical aliases, CPU/software/subdevices and ambiguous same-vendor identities are refused. A single-card baseline needs `--policy-mib 17` for the default workload. Nine MiB per device is the experiment's artificial policy cap, not a free-memory measurement. Unknown runtime allocation limits cannot qualify admission. The parent supervises all runtime discovery and execution inside a child with a 60-second deadline; there are no persistent workers.

PASS requires finite tensor parity, unique layer ownership and actual completed kernels. Corruption changes the real activation at the first vendor boundary, then requires a measured final mismatch against the original CPU reference; homogeneous-vendor corruption requests are refused. Exit codes are 0 PASS, 1 FAIL, 2 REFUSED/NOT_CHECKED. The recorded default and reverse installed-device runs passed, and corruption was detected; exact source and acceptance evidence are in `records/opencl_executor_20261004`. The AMD device is integrated shared-host memory. Four discrete cards, Intel, direct P2P, larger-than-one-card LLM capacity and speed benefits remain separate qualification gates.

opencl_smoke.py is experimental test apparatus, not a J-Link executor. It runs actual kernels on separate installed AMD/NVIDIA contexts with explicit host staging, tests exact FP32 parity in both directions, and limits buffers to 1 MiB and execution to 60 seconds. Run it with existing NumPy/PyOpenCL. `--inject-corruption` must fail. An optional `--probe-invalid-context` isolates a known native driver failure and is not run by default. Results distinguish AMD integrated/shared host memory from NVIDIA dedicated memory; no direct P2P or pooled allocation is claimed.

`vulkan_smoke.cpp` is a separate Windows transfer fixture. It passed NVIDIA GPU fill/readback, forwarding of those actual host-staged bytes, and AMD copy/readback for all 256 KiB; `--inject-corruption` returned exit 1 with one mismatch. It tests transfer commands, not compute shaders or model operators. Verified official headers, the local loader import library, source hashes, compile command and bounded run logs are in `records/vulkan_smoke_20261004`; accepted results are in `revision_3`. Fence waits use a 10-second deadline and recorded runs had a separate 60-second process limit.

`d3d12_smoke.cpp` passed NVIDIA-to-AMD copying through an explicit shared cross-adapter heap with placed buffer resources and GPU fence synchronization. All 256 KiB were verified; `--inject-corruption` failed at the injected byte 12,345. The API requires L0 system memory, and physical residency was not measured. This is experimental GPU-copy plumbing, not direct VRAM P2P or an inference executor. Accepted VS 18/Windows SDK build and bounded run evidence are in `records/d3d12_smoke_20261004/placed_heap_revision`. Earlier rejected sources and the illegal committed-buffer failure remain preserved.

rpc_smoke.cpp executes two matrix stages through two genuine ggml RPC workers and transfers a tensor between them. In this session both workers are CPU-backed. This proves RPC allocation/compute/transfer plumbing and arithmetic parity; it does not prove GPU support, VRAM pooling, LLM inference or performance.

For a Linux CPU/RPC build, follow the pinned llama.cpp build docs with GGML_RPC=ON. Compile this small client against that build:

```bash
g++ -std=c++17 j_link/rpc_smoke.cpp -Irepos/llama.cpp/ggml/include -L<build>/bin -Wl,-rpath,<absolute-build>/bin -lggml -lggml-rpc -lggml-base -o rpc_smoke
```

In two terminals start ggml-rpc-server with --host 127.0.0.1 --port 50062 and --port 50063. In a third run `./rpc_smoke 127.0.0.1:50062 127.0.0.1:50063`. No model download is needed. Stop both workers afterward. Check current upstream flags before rebuilding on a different commit.

Future GPU tests must identify the actual device behind each endpoint and record numerical, allocation and transfer measurements. The worker launch helper stays in foreground for qualification; detached durable supervision belongs to the later PyRe integration.

`device_inventory.py` is a pure captured-output adapter. A fresh real NVIDIA CSV capture verifies the exact known `[MiB]` headers, canonical PCI identity and byte conversion. Admission rechecks freshness and rejects unknown/shared capacity, invalid metadata and conflicting identities. It is an instantaneous observation, not a reservation or allocator. AMD/Intel JSON selectors are declared synthetic contracts; live CLI formats and dedicated free capacity are not qualified. See `records/device_inventory_20261004` for provider provenance and controls.

`rpc_four_worker_smoke.cpp` is the current four-worker fixture. On this Windows host it passed four graph stages and three interworker tensor copies through four real CPU-backed ggml RPC workers, producing `[136,312,184,424]`. All four owned workers were closed afterward. Build/run evidence is in `records/rpc_four_worker_20261004`; this is `CPU_ONLY_NOT_GPU_QUALIFICATION`. The earlier two-worker fixture remains historical evidence.
