# Three-vendor capability matrix + topology routing (AMD arm, 2026-10-05)

FROZEN: Intel/NVIDIA state pinned at
`records/CHECKPOINT_FROZEN_INTEL_NVIDIA_20261005T114254Z.json`.
Companion: `docs/13_AMD_ARCHITECTURE.md` (directional findings),
`docs/12_INTEL_NVIDIA_FABRIC.md` (frozen arm). Evidence states: PROVEN /
DOCUMENTED / PLAUSIBLE / SIMULATED / FAILED / BLOCKED / UNKNOWN.

## 1. Capability matrix (each direction independent; no symmetry assumed)

Legend: cell = best tier with its evidence. T2P=TRUE_DIRECT_P2P,
EXT=EXTERNAL_MEMORY, SZC=SHARED_ZERO_COPY, PDM=PEER_DMA,
PIPE=PINNED_DMA_PIPELINE, HST=HOST_STAGING.

| Source -> Dest | Best tier today | Evidence | Enforcing layer of the boundary |
|---|---|---|---|
| NVIDIA -> NVIDIA | PDM-grade peer (NCCL SHM doc'd fallback) | PLAUSIBLE (consumer GeForce P2P unmeasured here) | driver/runtime probe per pair |
| Intel -> Intel | Level Zero peer, ~15% gain | DOCUMENTED (#921, 2x B60 AM5) | kernel allow-list + ACS/IOMMU BIOS |
| AMD -> AMD | `hipMemcpyPeer`, directed | DOCUMENTED + third-party measured | same root + PCIe atomics |
| (this host: HIP 6.4 runtime PROVEN on gfx1036 iGPU, 1 CU, host-shared; peer matrix empty -- single device, no pair; discrete cells stay NOT_CHECKED) | | | |
| NVIDIA -> Intel | PIPE (Qwen payload is Linux-only PROPOSED) | PLAUSIBLE | CUDA no-import + L0 one-driver-handle |
| Intel -> NVIDIA | HST (reverse explicitly refused by payload CLI) | BLOCKED-as-designed | payload scope; CUDA no-import |
| NVIDIA -> AMD | PIPE (D3D12 L0 path staged PROVEN 256 KiB) | PROVEN-staged | Vulkan UUID / amdgpu GTT demote |
| AMD -> NVIDIA | PIPE (same L0 shape, this direction UNRUN) | PLAUSIBLE | nv attach refuses NVIDIA attachers only; AMD->NV importer unproven |
| Intel -> AMD | PIPE via L0-shaped path | UNKNOWN leaning BLOCKED | xe GTT fallback + amdgpu demote |
| AMD -> Intel | PIPE via L0-shaped path | UNKNOWN leaning BLOCKED | same, mirrored |

No T2P cell is above UNKNOWN today: zero working direct legs exist, so
the triangle-bridge hypothesis stays UNKNOWN (recorded in the AMD matrix
receipt). The matrix runner (`j_link/amd_future_matrix.py`, 45 cells)
recomputes this the moment hardware appears.

## 2. NVIDIA<->AMD and Intel<->AMD experimental designs

Shared skeleton (M1..M5 per direction, control R + N1 mandatory):
1. M1: directed capability queries both ways (`hipDeviceCanAccessPeer`,
   Vulkan peer features, D3D12 adapter pair) -- record, do not trust.
2. M2: 64 MiB checksum transfer on the best available tier.
3. M3: control R -- dedicated-vs-shared deltas on BOTH endpoints.
4. M4: N1 same-size host-staged baseline; at-or-below means staged.
5. M5: device-side corruption control must FAIL loudly (exit 1).
NVIDIA<->AMD extras: BAR1/ReBAR readback both cards; link gen/width warm;
   pageable-vs-pinned ratio (expect ~3-4x on NVIDIA leg per stream_bench).
Intel<->AMD extras: Linux-only; allocator MUST be `zeMemAllocDevice`
   (never `sycl::malloc_device`, 1:1 host mirror); compression-disable key
   set or reads lie.

## 3. Topology-aware routing (scheduler design)

```
            NVIDIA (16 GB)
           /              \
  PIPE/EXT?              PIPE (L0-staged PROVEN)
         /                  \
Intel (24 GB) ----?-?---- AMD (TBD)
   (UNKNOWN-leaning-BLOCKED both ways)
```

- Routing table key: (src, dst) -> ordered tier list with MEASURED cost
  (GB/s, latency, CPU%) from receipts, never from spec sheets.
- Bridge rule: a two-hop route is eligible only if BOTH legs are
  staging-free at the claimed tier; else the route demotes to the lowest
  staged tier on the path and says so.
- Cost rule: never assume the shorter hop-count wins; compare measured
  end-to-end bytes/sec including sync overhead (a 2-hop 20 GB/s peer path
  beats a 1-hop 3.4 GB/s staged path; a 1-hop staged path beats a 2-hop
  staged path with two sync penalties).
- Scheduler inputs: `describe_pool` (logical inventory) + per-pair
  selection from `select_transport` + `simulate_pipeline` timings.
  Implemented as data + pure functions today (`transport.py`,
  `feed_measurements.py`); a daemon scheduler is explicitly out of scope
  until a first direct leg proves.

## 4. Residency verification extension (cross-vendor)

Base: Control R (`j_link/residency_probe.py` hurdles documented:
nvidia-smi per-context granularity, PDH Dedicated-Usage coarseness,
single-GPU host). Extensions for the triangle:
- R+1 migration detector: sample before, mid-transfer, after; a dip that
  recovers post-sync indicates driver migration (xe GTT fallback, amdgpu
  demote, SYCL host mirror) -- FAIL the direct claim on sight.
- R+2 host-activity witness (`j_link/residency_witness.py`, live-tested):
  host committed-bytes sampled around the wrapped command; unexplained
  retained growth with a "direct" claim demotes to PIPE/HST. Known limit
  (measured: 200 MiB transient child alloc read as 11 MB): samples bracket
  the command, so transient in-flight staging that is freed on exit is
  NOT caught -- a concurrent sampling thread is the documented next step.
- R+3 engine witness where observable: CUDA/NVML copy-engine utilization,
  AMD SDMA counters via `amd-smi`/rocprof; DMA-without-CU/SM activity
  corroborates (never proves) the DMA path.
- Refusal instrumentation: every BLOCKED cell must name the refusing
  layer (API / user-mode driver / kernel / IOMMU / fabric / firmware)
  with the exact error, errno, or spec sentence.

## 5. Benchmark methodology (reproducible)

Sizes 8 KiB / 4 MiB / 64 MiB / 512 MiB (matches stream_bench); warmup +
link-warm (idle Gen1 lies); checksum every transfer; pin kernel, driver,
runtime per run; rerun Tier 0 after any update. Mandatory controls R, N1,
N2 on every M2. Commands:
- `python -B -m unittest discover -s j_link/tests` (112 green 2026-10-05)
- `python -B j_link/amd_probe.py` / `python -B j_link/amd_future_matrix.py`
- `python -B j_link/rtx5070ti_harness.py` / `python -B j_link/b60_future_matrix.py`
- `nvcc -O2 -o stream_bench.exe j_link/stream_bench.cu` (CUDA 12.8 +
  VS2022 14.41) then `stream_bench.exe --json`, `--inject-corruption`
  (expect exit 1 with word-exact fault).

## 6. Hardware-validation resume (exact)

Immediate next step (no hardware needed): reboot for the pending AMD
installer + Microsoft Update, then `hipcc --version` and `rocminfo`.
Required for matrix execution: one discrete AMD GPU (RDNA,
slot-mounted CPU root, PCIe atomics, Linux + ROCm) and/or Intel B60.
On arrival:
1. `python -B j_link/amd_probe.py` must flip to AMD_DISCRETE_PRESENT.
2. Matrix runner must construct >0 pairs; execute M1..M5 per direction.
3. Success bar per leg: M2 match + R deltas both endpoints + M4 slower.
4. First proven leg re-opens the bridge hypothesis; until then the
   triangle routes pinned/staged and the matrix says so.
AMD branch state: SOFTWARE COMPLETE, HARDWARE VALIDATION PENDING.

## 7. Freeze hygiene (honest record)

- `records/CHECKPOINT_FROZEN_INTEL_NVIDIA_20261005T114254Z.json` (38 files)
  is the Intel/NVIDIA checkpoint. `docs/12_INTEL_NVIDIA_FABRIC.md` received
  two annotation-only edits after that stamp (checkpoint pointer, VRAM-row
  label); no evidence, number, or verdict changed. Current tree state for
  the AMD arm is pinned separately at
  `records/CHECKPOINT_AMD_PHASE_BASE_20261005T114557Z.json` (9 files;
  supersedes the 114521Z 7-file pin, which stays immutable).
- `j_link/transport.py` tier additions are additive: all pre-existing
  constant names, selection order for old tiers, and old tests pass
  unchanged (112/112).
