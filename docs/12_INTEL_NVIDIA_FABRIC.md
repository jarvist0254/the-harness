# J-Link Intel B60 + NVIDIA RTX 5070 Ti fabric (heterogeneous arm)

Written 2026-10-05. New investigation arm; the pre-existing Intel-Intel P2P
work is FROZEN and untouched. Companion status:
`C:/Users/thoma/Desktop/status/harness-jlink-status.md` (2026-10-05),
`E:\the_harness\HANDOFF_LAST_5_HOURS.md`, `docs/10_*` (verdict + plan),
`docs/11_*` (achievement targets). This doc is the B60+5070Ti deliverable
index: feasibility matrix, diagrams, per-failure reasons, OS comparison,
harnesses, transport design, benchmark method, and next experiment.

Evidence classes (mandatory, per mission): PROVEN / DOCUMENTED / PLAUSIBLE /
FAILED / BLOCKED. Nothing untested is reported as proven.

FROZEN CHECKPOINT (2026-10-05, AMD phase start):
`records/CHECKPOINT_FROZEN_INTEL_NVIDIA_20261005T114254Z.json` pins the
SHA256 of all 38 files of this arm (j_link, this doc, both receipt dirs).
State: INTEL/NVIDIA SOFTWARE COMPLETE, HARDWARE VALIDATION PENDING. The
B60 validation trigger stands. Nothing here may be rewritten to fit AMD.

## 0. Host truth today

- Discrete GPUs: 1 (RTX 5070 Ti, 16303 MiB, `00000000:01:00.0`, DEV_2C05).
- Integrated: AMD Raphael (shared host memory, NOT dedicated VRAM).
- Intel GPUs: 0, exhaustive scan. `ze_loader.dll` absent.
- Directed cross-vendor pairs constructible: 0.
- Shell execution in this session is unavailable (tool pipe failure), so no
  command below was re-run here; every number re-states a pinned receipt or a
  cited source instead of inventing a new measurement.

## 1. Card facts

| Item | RTX 5070 Ti | Arc Pro B60 |
|---|---|---|
| Architecture | NVIDIA Blackwell, GB203-300 | Intel Xe2-HPG Battlemage, BMG-G21 |
| VRAM | 16 GB GDDR7, 256-bit, ~896 GB/s (PROVEN, this host) | 24 GB GDDR6, 192-bit, 456 GB/s (Intel datasheet v1.0, first-hand §7b) |
| PCIe | x16 PCIe 5.0 | x8 PCIe 5.0 |
| CUDA cores / Xe2 | 8960 CUDA | 20 Xe2 cores, 160 XMX, 12.29 TFLOPS FP32 |
| Device id | 10DE:2C05 (measured here) | 8086:E211 (per #921) |
| Evidence | PROVEN (this host) | DOCUMENTED (convergent third-party specs; Intel ARK fetch still pending -- intel.com returned 301-to-404 this cycle, so capacity stays DOCUMENTED, not PROVEN) |

## 2. Feasibility matrix (cross-vendor, this host class)

| # | Mechanism | Win | Linux | Class | Reason |
|---|---|---|---|---|---|
| 1 | CUDA P2P / UVA to Intel | BLOCKED | BLOCKED | BLOCKED | `cudaDeviceCanAccessPeer` takes ordinals into NVIDIA's own device list; no way to name a foreign device. No import attribute (export-only dma-buf). |
| 2 | Level Zero peer to NVIDIA | BLOCKED | BLOCKED | BLOCKED | `zeDeviceCanAccessPeer` takes one `ze_driver_handle_t`; cross-vendor pair unconstructible by spec. |
| 3 | Vulkan device group | BLOCKED | BLOCKED | BLOCKED | Identical props required (VUID-00376); vendorID can never match. |
| 4 | Vulkan external-memory import (cross-vendor) | BLOCKED | PLAUSIBLE-narrow | mixed | Windows: OPAQUE_WIN32 needs matching driverUUID+deviceUUID; measured AMD→NVIDIA VK_ERROR_UNKNOWN. Linux: fd path exists in principle; Qwen's CUDA→L0 64 KiB payload is the open experiment (PROPOSED, not run). |
| 5 | D3D12 cross-adapter heap | DOCUMENTED-staged | N/A | staged | Works (256 KiB NVIDIA→AMD PASS here) but spec requires L0 system-memory backing: GPU-initiated, CPU-free, still host-staged. Never dedicated-VRAM P2P. |
| 6 | dma-buf / pci_p2pdma direct VRAM | N/A | BLOCKED-consumer | BLOCKED | Whitelist has no consumer AMD/Intel host bridge; i915 never exports VRAM; NVIDIA refuses NVIDIA-GPU attachers; CUDA has no import. Switch chassis is the only opener (genuinely open, untested here). |
| 7 | NCCL/RCCL/oneCCL/MSCCL++/UCX bridge | BLOCKED | BLOCKED | BLOCKED | No library expresses a mixed-vendor communicator (MSCCL++ CMake mutually exclusive; UCX disjoint masks; NCCL=RCC SHM fallback documented). |
| 8 | GPUDirect RDMA / PeerDirect | BLOCKED | BLOCKED | BLOCKED | GPU↔NIC, Tesla/Quadro + Instinct-only; consumer GeForce excluded. |
| 9 | ZLUDA / SCALE / chipStar / HIPIFY | BLOCKED | BLOCKED | BLOCKED | API/kernel compatibility only; no pooling, no p2p component. |
| 10 | CXL / UALink | BLOCKED | BLOCKED | BLOCKED | CXL is host↔device, no consumer GPU implements it; UALink excludes NVIDIA, silicon 2027+. Track only. |
| 11 | PINNED_DMA_PIPELINE | PLAUSIBLE | PLAUSIBLE | route | Both GPUs DMA against one pinned host allocation, chunked + overlapped. Simulator + protocol written (`j_link/pinned_dma_pipeline.py`); needs measured bandwidths. Staged, never P2P. |
| 12 | HOST_STAGING (+ RPC / Vulkan layer split / PyRe graph) | PROVEN | PROVEN | baseline | Narrow paths measured on this host (OpenCL 6 sizes, Vulkan 256 KiB fixture, ggml RPC 4 stages). THE mixed-vendor route. |
| 13 | Same-vendor Intel P2P (2x B60, AM5 Linux) | N/A | DOCUMENTED | adjacent | #921: canAccess=1 both ways, Gen5 x8, kernel 7.1.2 + compute 26.22.38646.4, ACS+IOMMU off, RenderCompressedBuffersEnabled=0. No switch needed on Zen. Adjacent milestone, not cross-vendor. |

## 3. Architecture diagrams

### A. PINNED_DMA_PIPELINE (the route -- staged, CPU orchestrates, DMAs move)

```
Intel VRAM                    Pinned host RAM                 NVIDIA VRAM
+--------+  DMA chunk k    +-----------------+  DMA chunk k   +--------+
| chunk 0| --------------> | chunk 0 READY   | -------------> | chunk 0|
| chunk 1| ----+           | chunk 1 FILLING |                |  ...   |
| chunk 2|     | overlap   +-----------------+                +--------+
+--------+ <---+  (NVIDIA consumes chunk k while Intel fills k+1)
   ^ CPU sequences chunk ids + fences; CPU never memcpys payload bytes.
```

### B. HOST_STAGING baseline (N1 control -- sequential two-hop)

```
Intel VRAM --> [full object to host] --> NVIDIA VRAM
(successive, no overlap; the number every "P2P" claim must beat)
```

### C. EXTERNAL_MEMORY attempt path (Qwen payload -- Linux only, PROPOSED)

```
CUDA cuMemAlloc --> cuMemGetHandleForAddressRange(DMA_BUF_FD)
  --> zeMemAllocDevice(import fd) --> L0 copy --> host readback verify
Payload parity only; transport/residency NOT proven by parity alone.
```

### D. Logical pool (capacity without coherent address space)

```
GPU0 NVIDIA 16 GB: layers 0..N (resident, local alloc)
GPU1 Intel 24 GB:  layers N+1..M (resident, local alloc)
HOST pinned:       streaming chunks + KV overflow (bounded)
Coordinator places whole layers/experts/stages; migrates only if profitable.
Summed 40 GB is inventory, never one malloc.
```

## 4. Windows vs Linux

- Windows: cross-vendor dedicated-VRAM path CLOSED by spec (D3D12 L0-only,
  Vulkan UUID match, no dma-buf). Shipped J-Link on Windows = pipeline +
  staging + RPC/Vulkan layer split. Control R via PDH/nvidia-smi sampling.
- Linux: one narrow opener (CUDA-export -> L0/Vulkan dma-buf import,
  Qwen payload) + the switch-chassis p2pdma variant; both need a two-card
  rig and residency proof. Same-vendor Intel P2P is Linux-only (ze_peer
  uses fork/socketpair/sigaction + SCM_RIGHTS; excluded on non-UNIX).
- Plan: develop pipeline + staging on Windows now (real 5070 Ti numbers);
  validate imports + Intel P2P on Linux when a B60 lands.

## 5. New source in this arm (frozen Intel-Intel work untouched)

- `j_link/transport.py` -- hierarchy, residency-gated selection, pool view,
  terminology guard (staged never labeled direct).
- `j_link/pinned_dma_pipeline.py` -- chunk planner + overlap simulator
  (PLAUSIBLE; promotes only with measured bandwidths).
- `j_link/rtx5070ti_harness.py` -- nvidia-smi topology/BAR/ReBAR/CUDA
  presence probe, JSON receipt (run when shell is back).
- `j_link/stream_bench.cu` -- CUDA probe: pinned vs pageable H2D/D2H
  bandwidth at 8 KiB/4 MiB/64 MiB/512 MiB, 2-stream overlap gain, FNV
  checksum every transfer, device-side corruption control. COMPILED and
  MEASURED 2026-10-05 (receipts in `records/stream_bench_20261005/`).
  Toolchain that works: CUDA **v12.8** nvcc + VS2022 BuildTools MSVC
  14.41, no override flag. CUDA 12.3 + MSVC 14.41 fails (STL1002: STL
  needs CUDA >= 12.4; even an empty .cu fails, so it is the pairing, not
  the source). The probe is written as C (no STL) as belt-and-braces.
- `j_link/feed_measurements.py` -- receipt validator + transport planner;
  executed live against the measured receipt (1 GiB plan: 19.8 ms
  pipelined vs 37.3 ms sequential, 1.88x, PLAUSIBLE with stated symmetric
  assumption).
- `j_link/b60_future_matrix.py` -- B60 recognition (8086:E211) + directed
  2-pair x 5-test matrix; today correctly yields 0 pairs + HOST_STAGING.
- `j_link/tests/test_transport.py`, `test_pinned_dma_pipeline.py` -- pure
  unit tests, no GPU needed.
- `j_link/feed_measurements.py` (+ `test_feed_measurements.py`) --
  validates a `stream_bench --json` receipt (refuses corrupt/unmeasured
  data), derives stage bandwidths (symmetric assumption explicit,
  overridable), selects the transport, and plans pipelined vs sequential
  timelines. Stays PLAUSIBLE until both halves are measured with R + N1.
- Qwen payload: CUDA->L0 64 KiB payload PROPOSED (record path in matrix
  receipt); reverse direction explicitly refused by its CLI. Not copied
  here -- run from the record when a two-card Linux rig exists.

## 6. Benchmark methodology (every viable approach)

Sizes 8 KiB / 4 MiB / 64 MiB / 512 MiB; warmup + sync; checksum every
transfer; report GB/s + latency-vs-size + CPU% + overlap factor +
topology (gen/width per link). Mandatory controls: R (both-endpoint
residency), N1 (same-size host-staged baseline -- a "P2P" number at or
below it IS host-staged), N2 (checksum always; success codes lied twice
on record). Pin kernel/driver/runtime per run; rerun Tier 0 after updates
(NEO 25.44/25.48 regression precedent).

## 7a. Measured NVIDIA-half results (PROVEN, 2026-10-05, this host)

- Device: RTX 5070 Ti, cc 12.0, driver 591.86, `00000000:01:00.0`, 16303
  MiB total / 13966 free at sample time. Link: **Gen1 x16 idle, Gen5 x16
  max** -- benchmarks must warm the link before trusting a number.
- `stream_bench --json`, exit 0, all 8 checksums OK
  (`records/stream_bench_20261005/stream_bench_receipt.json`):
  pinned round-trip 1.0 (8 KiB, latency-bound) / 56.8 / **57.6** /
  56.8 GB/s; pageable 0.34 / 18.2 / 15.9 / 14.3 GB/s (~3-4x pinned
  penalty -- pinning is mandatory, not optional).
- Overlap gain 0.99-1.00: **no H2D+D2H overlap on this path** -- the two
  directions serialize, so the pipeline's overlap lives in chunk-level
  pipelining (measured plan above), not in bidirectional concurrency.
- Corruption control: exit 1 with the fault at exactly words/2 and
  `got=0x94BA7E31` (pattern^mask) on all 8 cases -- detection PROVEN.
- `nvidia-smi -q` filter returned only a "BAR1 Memory Usage" line: no
  ReBAR status line is exposed this way on Windows here; BAR/ReBAR sizing
  stays an open probe (Linux `lspci -vvv` when a B60 rig exists).
- Correction to earlier session notes: the `j_link/tests` suite DOES exist
  (an early file-glob misled me into reporting it absent) -- **101 tests,
  all OK**, including the 21 new heterogeneous-arm tests.

## 7b. B60 research notes (2026-10-05 cycle)

**Claim 7 RESOLVED first-hand this cycle: B60 = 24 GB CONFIRMED (PROVEN
document provenance, hardware still absent).** Official Intel datasheet
v1.0 (2025, (c) Intel), fetched HTTP 200 from `cdrdv2-public.intel.com`
(2,904,836 bytes, 2 pages, text-extracted via PyMuPDF; archived with
provenance in `records/b60_datasheet_20261005/`): "24GB of onboard
graphics memory", "Dedicated Memory: 24GB of GDDR6", 456 GB/s, 192-bit,
20 Xe2-HPG, 160 XMX, 197 INT8 TOPS, 12.28 FP32 TFLOPS, PCIe Gen 5.0 x16
(x8 electrical) with 4.0 backwards compat, 120-200W TBP, Windows 11/10 +
Ubuntu, Vulkan 1.3 / oneAPI / OpenCL 3.0 / DX12U. The bandwidth↔capacity
transcription-error hypothesis is dead: 24 GB is stated as dedicated
memory in three separate places. The older UNVERIFIED flags in docs 02 /
05 / 10 / 11 (and the Desktop status claim 7) are superseded by this
receipt -- those files were left byte-identical outside this arm's scope;
their next editor should flip the flag and cite this section.

- ReBAR: DOCUMENTED (Intel). B60 press-deck test config lists
  "Resizable BAR: Enabled" (driver 32.0.101.6791); Intel Arc Pro desktop
  quick-start calls ReBAR enablement one of the most important setup steps.
  Caveat (delegated, single third-party report): B70 passthrough exposing
  only a 16 GB BAR on some platforms. Re-check BAR sizing live when a B60
  lands; the RTX harness already captures the NVIDIA side.
- L0 dma-buf import shape: DOCUMENTED (Intel oneAPI GPU optimization
  guide, media-interop chapter): `ze_external_memory_import_fd_t` chained
  into `ze_device_mem_alloc_desc_t` -> `zeMemAllocDevice`. All published
  examples are same-vendor (media) interop -- no cross-vendor import is
  shown. intel.com returns 403/404 to this client, so this is recorded
  from convergent snippets + Qwen's header-pinned analysis, not a
  first-hand page read.
- Allocator warning, DIRECTLY relevant to the pipeline (DOCUMENTED, ggml
  upstream commit `7580507`, release b9145): `sycl::malloc_device` on the
  `xe` driver routes through the TTM dma-buf path and mirrors every VRAM
  allocation 1:1 in system RAM; the fix is `zeMemAllocDevice`. Consequence:
  the Intel side of PINNED_DMA_PIPELINE must allocate staging via Level
  Zero device/host allocators, never `sycl::malloc_device`, or host RAM
  doubles silently and control R misreads.

## 7. Recommended next experiment (cheapest, unblocks the most)

1. Restore shell execution; run `j_link/rtx5070ti_harness.py` (live
   topology/BAR/ReBAR/props receipt) + new unit tests
   (`python -B -m unittest discover -s j_link/tests`).
2. Add the `cudaMemcpyAsync` stream benchmark (pinned vs pageable,
   1-stream vs N-stream, H2D/D2H overlap) -- turns pipeline inputs from
   assumed into PROVEN on the NVIDIA half.
3. Confirm B60 24 GB from Intel ARK before any purchase (claim 7).
4. On a Linux + B60 rig: run the Qwen CUDA->L0 payload with control R +
   N1; either promote EXTERNAL_MEMORY or record exactly which layer
   refuses (that refusal is itself the boundary proof the mission asks for).
