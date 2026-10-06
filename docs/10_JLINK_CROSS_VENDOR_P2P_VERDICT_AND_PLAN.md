# J-Link cross-vendor P2P — verdict, evidence and the only workable plan

Written 2026-10-05 03:21 UTC (2026-10-04 23:21 EDT). Supersedes no earlier document; extends
`02_J_LINK_RESEARCH.md`, `05_PRIMARY_SOURCES.md` and `09_FULL_GOAL_GATE_REGISTER.md`.

This document answers one question with primary sources: **can J-Link do peer-to-peer access to
dedicated VRAM across Intel, AMD and NVIDIA cards, and if not, what is the strongest design that
does work?**

## Verdict

**No. Cross-vendor direct dedicated-VRAM peer access does not exist as a supported mechanism on
consumer GPU hardware, on Windows or on Linux, as of 2026.** This is not a "we have not tried hard
enough" result. On Windows it is architecturally excluded by specification. On Linux the kernel
plumbing is vendor-neutral in principle but is gated shut by a PCIe-topology whitelist that contains
no consumer desktop host bridge, and every vendor compute API is sealed at the handle level.

Two independent blockers apply to this specific objective, and either one alone is fatal:

1. **The capability does not exist.** Detailed below, from specifications and driver source.
2. **The hardware is not present.** Measured on this host: one discrete GPU total, zero Intel GPUs,
   and the AMD device is an integrated APU with shared system memory. Peer access requires at least
   two peer-capable devices; cross-vendor peer access requires discrete cards from at least two
   vendors. No software can install a PCIe card.

### Measured host state (verified this session, three independent methods)

| Probe | Result |
|---|---|
| `Get-CimInstance Win32_VideoController` | `NVIDIA GeForce RTX 5070 Ti`; `AMD Radeon(TM) Graphics`. Two controllers. |
| `Get-PnpDevice -Class Display` | `PCI\VEN_10DE&DEV_2C05` (NVIDIA, discrete); `PCI\VEN_1002&DEV_164E` (AMD Raphael iGPU) |
| Exhaustive Intel scan (`-PresentOnly:$false`, all states, `VEN_8086` + Arc/Iris/UHD name match) | **ZERO Intel GPU devices — present, hidden or disabled** |
| `nvidia-smi -L` / `--query-gpu` | Exactly `GPU 0: NVIDIA GeForce RTX 5070 Ti`, 16303 MiB, `00000000:01:00.0` |
| Project's own `enumerate_opencl_devices()` | 2 GPU records. NVIDIA `DEVICE_LOCAL_MEMORY_REPORTED`, `host_unified=false`. AMD gfx1036 `host_unified=true`, classified **`SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM`**, identity `EPHEMERAL_RUNTIME_ID`. **Zero Intel.** |
| `C:\Windows\System32\ze_loader.dll` | Absent |

Population available for any peer experiment: **one** discrete card. Directed peer pairs possible:
**zero**. This is why every transport gate in `09_FULL_GOAL_GATE_REGISTER.md` remains open, and it
is a hardware fact, not a software defect.

## Part 1 — Why cross-vendor direct VRAM P2P is not available

### 1.1 Windows is excluded by specification, not by omission

The only cross-vendor sharing primitive WDDM/D3D12 exposes is the cross-adapter shared heap, and
Microsoft states the limit flatly: *"Cross-adapter shared resources are only supported in system
memory"* — cross-adapter heaps live in `D3D12_MEMORY_POOL_L0`, which *"is not efficient for
discrete/NUMA adapter architectures."* Microsoft does permit mixed vendors (*"any adapter ... from
any manufacturer, that supports Direct3D 12"*) and then stops at L0 exchange.

This **retroactively confirms a measurement this project already recorded**: the D3D12
NVIDIA→AMD 256 KiB copy with a real shared cross-adapter fence was a genuine GPU-initiated copy,
but the shared resource was L0 system memory. It was correctly classified as not-dedicated-VRAM.
That classification is now spec text, not inference. Note the trap in *"without the CPU marshaling
the data"*: the CPU is out of the data path, but system memory is in it.

The Vulkan route is separately closed: `OPAQUE_WIN32` handles require matching `driverUUID` **and**
`deviceUUID`. Third-party measurement records AMD→NVIDIA import failing with `VK_ERROR_UNKNOWN`
(-13) and AMD→Intel with an access violation inside `vkAllocateMemory`.

**Conclusion: no Windows cross-vendor dedicated-VRAM path exists. Closed.**

### 1.2 Mixed-vendor Vulkan device groups are impossible by specification

*"For two physical devices to be in the same device group, they must support identical extensions,
features, and properties."* Enforced by
`VUID-VkDeviceGroupDeviceCreateInfo-pPhysicalDevices-00376`. `VkPhysicalDeviceProperties` carries
`vendorID`, `deviceID`, `driverVersion` and `apiVersion`; no NVIDIA and AMD or Intel part can match.
Groups are also enumerated per-`VkInstance` with the loader dispatching to each ICD separately, so
each vendor reports only its own groups.

Peer memory features (`VK_PEER_MEMORY_FEATURE_COPY_SRC/COPY_DST/GENERIC_SRC/GENERIC_DST_BIT`) are
real — and reachable only **inside** a group. **Closed by specification.**

### 1.3 CUDA, HIP and Level Zero are each sealed at the handle level

- **CUDA** — `cudaDeviceCanAccessPeer(int*, int device, int peerDevice)` takes integer ordinals into
  the CUDA runtime's device list, which only the NVIDIA driver populates. There is no way to *name*
  a foreign device. CUDA's dma-buf surface is **export-only**; there is no import attribute.
- **HIP/AMD** — the seal is verbatim in the kernel, in `amdgpu_amdkfd_get_dmabuf_info()`:
  `if (obj->dev->driver != adev_to_drm(adev)->driver) /* Can't handle buffers from different drivers
  */ goto out_put;`. Foreign imports are additionally forced to `AMDGPU_GEM_DOMAIN_GTT`
  (system memory).
- **Level Zero** — the spec states other vendors live under other driver objects: *"More than one
  driver may be available in the system ... one driver may support two GPUs from one vendor,
  another driver supports a GPU from a different vendor"*, and *"The application is responsible for
  sharing memory and explicit submission and synchronization across multiple devices."*
  `zeDeviceGet`, `zeContextCreate` and `zeDeviceCanAccessPeer` all take exactly one
  `ze_driver_handle_t`. Peer queries across vendors cannot be constructed.

There is also **no "peer-accessible" allocation flag** in the Level Zero core API. `zeMemAllocDevice`
allocations are device-owned; peer reachability is a property of the *device pair*, not of the
allocation. `zeDeviceMakeMemoryResident` **does not exist** — residency is
`zeContextMakeMemoryResident(context, device, ptr, size)`. Do not write either into a plan.

### 1.4 The Linux dma-buf route is topology-gated shut on consumer desktops

`pci_p2pdma` requires *"two drivers to be co-operating inside the kernel"* and *"kernel defaults to
blocking such routing"*, with an allow list. Reading `drivers/pci/p2pdma.c` directly, the whitelist
contains only: Intel Xeon E5/E7 and Skylake-E host bridges, SPR/GNR DSA/IAX/QAT device IDs,
`PCI_VENDOR_ID_GOOGLE` with `PCI_ANY_ID`, and NVIDIA `0x2f95–0x2f98` (Grace **CPUs**).
**No consumer AMD chipset. No consumer Intel desktop host bridge.** Unlisted → `NOT_SUPPORTED`.

Driver-by-driver behaviour, read from source:

| Driver | Exports dedicated VRAM over dma-buf? |
|---|---|
| `amdgpu` | Yes — but `if (!attach->peer2peer) domains &= ~AMDGPU_GEM_DOMAIN_VRAM;` silently demotes to **GTT (system memory)** whenever `pci_p2pdma_distance()` fails. GFX12 DCC surfaces explicitly fall back to the system-memory path. |
| `xe` (modern Intel) | Yes via `XE_PL_VRAM0/1` → `xe_ttm_vram_mgr_alloc_sgt` — but only if the topology gate passes; otherwise `xe_bo_migrate(bo, XE_PL_TT, ...)` = system memory. |
| `i915` (legacy Intel) | **Never.** Forces migration to `INTEL_REGION_SMEM` on *every* attach. This permanently retires the recorded Intel→NVIDIA import-contract conflict for the i915 case: there is no Intel VRAM dma-buf to import. |
| `nvidia` open kernel module | `nv-dmabuf.c` can emit BAR1 physical addresses, but `nv_dma_buf_attach()` refuses **any NVIDIA GPU** attacher (*"NVRM: attaching GPU is not supported"*) and the surface is export-only. |

The recorded project observation *"Intel DMA-BUF → NVIDIA Vulkan: import-contract conflict
unresolved"* therefore resolves into **two independently fatal** problems rather than one ambiguity:
i915's forced migration (or xe's topology gate), and CUDA's total absence of dma-buf import.

**A silent-corruption hazard worth recording permanently:** on a kernel patched to force the
whitelist open, a 256 MB `zeCommandListAppendMemoryCopy` returned `ZE_RESULT_SUCCESS` while
**4,194,304 of 4,194,304 elements came back wrong**. `ZE_RESULT_SUCCESS` is not a correctness
certificate. Intel acknowledged the misleading error path. **Every peer transfer must carry a
checksum, always.** This independently confirms the principle already in `02_J_LINK_RESEARCH.md`.

The dma-buf abstraction itself is still contested at maintainer level in 2026: the mapping-type/PAL
series is RFC-only with no v2, and a competing "let importers ask how P2P traffic is routed" series
was NAK'd by the amdgpu maintainer on 2026-09-29/30 (*"the exporter is completely opaque to the
importer and that is for really good reasons"*). **This is not a stable foundation for a product.**

### 1.5 Collectives, RDMA and translation layers do not bridge vendors

- **NCCL** ranks are *"n CUDA devices"*; **RCCL** depends on the HIP runtime; **oneCCL** officially
  supports Intel Data Center GPU Max only. **RCCL and oneCCL have no native Windows build at all** —
  this upgrades the earlier "not implied" caution to "documented absent".
- **MSCCL++** is the closest: it does real direct VRAM access and ships CUDA *and* ROCm backends —
  but its CMake is mutually exclusive (`if(NVIDIA_FOUND AND AMD_FOUND) ... set(MSCCLPP_USE_ROCM
  OFF)`). A mixed-vendor build cannot be configured.
- **UCX** has `cuda_ipc` and `rocm_ipc`, using vendor-private handle types and disjoint
  `access_mem_types` masks. No cross-vendor transport; no native Windows.
- **Host-staged fallback is documented, not assumed.** NCCL: *"SHM is used between devices when
  peer-to-peer cannot happen, therefore, host memory is used."* NVIDIA: *"the pushed data is staged
  through a buffer in pinned system memory."*
- **GPUDirect RDMA** is GPU↔**NIC**, not GPU↔GPU, Tesla/Quadro only, Linux only. **AMD PeerDirect**
  is Instinct MI300X/MI200/MI100 only. Consumer GeForce and Radeon are excluded.
- **ZLUDA / SCALE / chipStar / HIPIFY** deliver API or kernel *compatibility*. None creates
  cross-vendor allocation pooling, and none claims to. ZLUDA's tree contains no `p2p`, `peer` or
  `multi_gpu` component. chipStar selects exactly one backend/platform/device.
- **CXL** coherency is host↔device, not device↔device, and no shipping consumer GPU implements it.
- **UALink** is the only standardized cross-vendor direct-memory fabric (load/store + DMA, up to
  1024 endpoints) — and **NVIDIA is not a member**, with silicon in labs H2 2026 and products in
  2027. It structurally cannot bridge to NVIDIA and has zero consumer applicability for at least
  two product generations.

### 1.6 Literature and repository search

**Provenance discipline for this section.** Claims below are split by how they were obtained.
"First-hand" means the query was issued and its raw response read directly in this session.
"Delegated" means a research subagent reported it and it was **not** independently re-verified — the
arXiv API returned HTTP 429 (rate limited) on every direct retry attempted here, so delegated arXiv
negative-search counts could not be confirmed and are marked accordingly.

**First-hand, verified this session:**

- GitHub repository search `cross-vendor GPU peer memory` → HTTP 200, **`total_count: 0`**, no items.
- GitHub repository search `heterogeneous GPU memory pooling` → HTTP 200, **`total_count: 0`**, no items.
- arXiv `cs.DC` recent listing → 172 entries; surfaced **ThunderEP, arXiv:2609.40093**, *"Efficient
  Expert-Parallel Communication on PCIe-Connected Consumer GPUs"*, fetched and read directly.

**ThunderEP is the single most relevant paper found, and it strengthens rather than weakens the
verdict.** It is about expert-parallel MoE inference on consumer PCIe GPUs — the closest published
analogue to J-Link's workload — and its own framing concedes the core point:

> *"The cost becomes particularly pronounced on PCIe-based consumer GPU systems, where **all
> inter-GPU transfers traverse CPU memory**. However, existing MoE-specialized EP communication
> libraries assume that direct GPU-to-GPU access is available, **largely overlooking consumer
> GPUs**. Therefore, most LLM frameworks instead rely on NCCL, whose **CPU-staged communication**
> incurs redundant PCIe transfers..."*

Its contribution is to make the *host-staged* path faster — removing ring relay hops, moving data
through DMA engines to avoid compute contention, and reducing completion-flag polling overhead in CPU
memory — integrated into vLLM. Test population: **RTX 4090 and RTX 5090, i.e. NVIDIA↔NVIDIA, same
vendor.** Reported gains: 2.00× dispatch and 1.53× combine over NCCL, up to 1.66× end-to-end.

Three conclusions follow, and all three belong in the J-Link plan:

1. **Even same-vendor consumer PCIe GPUs have no usable direct P2P.** A 2026 paper built entirely
   around optimizing CPU-memory-traversing transfers, on two current NVIDIA consumer cards, is strong
   evidence that the host-staged path is the real baseline — not a fallback.
2. **The optimization targets are concrete and transferable to a mixed-vendor design:** eliminate ring
   relay hops, use DMA/copy engines rather than compute shaders for boundary movement, and minimize
   completion-flag polling. These apply verbatim to §2.1 and are the highest-value engineering work
   available without any new hardware.
3. **Measured headroom is roughly 2×, not orders of magnitude.** ThunderEP's 2.00×/1.53× over NCCL
   bounds what better host staging can buy. It does not approach peer-DMA bandwidth, which is
   consistent with the ~9× host-staged-vs-peer gap recorded in §2.4 control N1.

**Delegated, NOT independently re-verified — treat as leads requiring confirmation before citation:**
HetCCL (reported arXiv 2601.22585) and memory-heterogeneous serving work (2606.29986, 2509.17542)
reported as network/RDMA-staged; CXL pool papers (2602.22457, 2511.20172) reported as host-attached
rather than GPU→GPU VRAM; Harvest (2602.00328) reported as peer-VRAM caching with no cross-vendor
claim. The arXiv negative searches reported as `all:"disaggregated GPU memory"` → 0 results could
**not** be reproduced here due to rate limiting and are therefore **UNVERIFIED**.

**One delegated correction that matters and is consistent with everything first-hand:** reported
arXiv 2602.18007 ("Joint Training on AMD and NVIDIA GPUs") achieves its device-direct path via
**GPUDirect RDMA over BlueField-3 DPUs**, not PCIe peer-to-peer. *"Without host-memory staging" ≠
"direct VRAM peer access."* Verify the ID before citing.

The repositories that advertise mixed-vendor use (`tightwad`, `memsplice`) are delegated findings and
are described as explicit store-and-forward over llama.cpp RPC plus file transfer with SHA-256
verification; the third-party project publishing real numbers is reportedly optimizing its
**host-staged fallback** (3.5 GiB/s → 8.61 GiB/s). Neither was re-verified first-hand this session.


### 1.7 What Intel *does* support — and why it still does not satisfy this objective

> **PARTIALLY SUPERSEDED BY §1.10.** This section was written from delegated research. §1.10 records
> what was subsequently confirmed **first-hand** from the two vendored Intel primary sources, and it
> (a) upgrades most of this section's substance to verified, (b) **overturns** the "requires a PCIe
> switch" framing, and (c) shows the VRAM capacities and Battlematrix figures quoted below are
> **unsupported by any vendored source**. Read §1.10 as authoritative where the two differ.

Multi-Arc peer access is **real**, and it is **not** limited to Xe-Link datacenter parts: Battlemage
**Arc Pro B60 / B70** *(capacities previously recorded here as 24 GB / 32 GB are **UNVERIFIED** — no
vendored Intel source states a VRAM capacity, and those numbers coincide exactly with doc 863931's
PCIe **bandwidth** figures of 24 GB/s payload and 32 GB/s bus, so a bandwidth↔capacity transcription
error upstream is a live possibility; confirm from Intel ARK before purchase — see §1.10)* do P2P over
ordinary PCIe, and Intel publishes an official platform-evaluation guide (doc 863931 rev 1.0, **read
first-hand this session**). Project Battlematrix (*"up to 8 Intel Arc Pro B60 GPUs"*, *"up to 192 GB of
combined VRAM"*) is **not vendored and was not fetchable** — unconfirmed. But every qualification runs
the wrong way for this objective:

- **Linux-only.** `ze_peer` is excluded on non-UNIX by upstream build configuration
  (`if(UNIX) add_subdirectory(ze_peer) else() message(WARNING "Skipping ze_peer: test only supported
  on Linux")`), and its source uses `fork()`, `socketpair(PF_UNIX)`, `sigaction()` and passes a
  dma-buf fd via `SCM_RIGHTS`. `level-zero-tests` builds on Windows; **the P2P benchmark inside it
  does not.** Intel's own collateral is written entirely in Linux terms.
- **Arc Pro only.** Consumer Arc B580/B570/A770 carry no Intel multi-GPU peer qualification. A regex
  over the full Windows Arc Pro driver release notes (32.0.101.8306 WHQL, Level Zero 1.24.3) returns
  **zero** occurrences of `peer`, `p2p`, `multi-gpu`, `multiple gpu` or `xe link`.
- **Intel's compatibility table — UNVERIFIED, not in either vendored source:** `dGPU + dGPU (same
  gen)` = Yes, *"if on same PCIe root, recent driver"*; `dGPU + dGPU (diff gen)` = **No**;
  `iGPU + dGPU` = **No**, *"not supported due to architectural and driver limitations."* Neither
  doc 863931 nor `compute-runtime#921` contains the strings "iGPU" or "dGPU", so this table comes from
  some other Intel page that was not vendored and could not be fetched. Treat as a lead. It does not
  affect an all-Arc-Pro population either way.
- **It is a throughput optimization, not a capacity unlock.** oneCCL quantifies the P2P-vs-USM gain
  as *"around 15% higher throughput"* at batch=30, with automatic fallback via `CCL_TOPO_P2P_ACCESS`.
  Nothing in Intel's documentation claims P2P lets one workload allocate a buffer larger than one
  card's VRAM. **This is the single most important correction to the project's working assumption.**
  *(The ~15% figure is delegated; doc 863931 does not state it. Worth confirming against Intel's
  multi-Arc quick-start guide, which is not vendored.)*
- **The binding constraint is the host platform — CORRECTED by §1.10.** The measurements originally
  recorded here for 2× Arc Pro B70 (consumer Intel root complex with separate root ports →
  `pci_p2pdma_distance` = `NOT_SUPPORTED`, `zeDeviceCanAccessPeer` = 0 both directions, copy refused;
  same host with the RC whitelisted by patch → `SUCCESS` but **100% silent data corruption**; PLX
  PEX880xx switch with ACS redirect **ON** → refused; **OFF** → `canAccessPeer` = 1 both directions,
  **28.00 GB/s, checksum PASS 268,435,456/268,435,456 bytes**) are **third-party and appear in no
  vendored source.** They remain plausible and the silent-corruption datum is consistent with the
  first-hand Arc compression-race finding in #921 — but they are leads, not verified results.
  **The conclusion drawn from them was too strong and is withdrawn:** a PCIe switch is *not*
  universally required. First-hand evidence in §1.10 shows Intel Arc Pro P2P working on an ordinary
  **AMD AM5** motherboard with no switch at all. The real gate is the kernel chipset allow-list plus
  BIOS ACS/IOMMU state. Design against Intel's own first-hand calibration (**~20 GB/s unidirectional /
  40 GB/s bidirectional at Gen5 x8**, doc 863931 p14) rather than the third-party 28.00 GB/s.


Also note: the project's recorded `zeInit(GPU_ONLY)` → `ZE_RESULT_ERROR_UNINITIALIZED` on Windows is
a **NO_DRIVER_INSTALLED** result and carries zero information about Windows peer capability. Zero
Intel GPUs means no Intel graphics driver, means no `ze_intel_gpu64.dll`, means nothing for the
loader to bind to — which is its documented graceful-failure behaviour. The probe also used a
self-built loader rather than the Intel-shipped pair. **Plan the Intel arm on Linux.**

### 1.8 Settled-unsupported — do not spend further budget here

1. Any Windows cross-vendor dedicated-VRAM path.
2. Mixed-vendor Vulkan device groups.
3. NCCL / RCCL / oneCCL / MSCCL++ / UCX as a cross-vendor bridge.
4. ZLUDA / SCALE / chipStar / HIPIFY creating pooled VRAM.
5. CXL as a consumer-GPU VRAM bridge.
6. `i915` exporting Intel dedicated VRAM over dma-buf.
7. CUDA importing a foreign dma-buf.
8. GPUDirect RDMA / PeerDirect on GeForce / Radeon consumer cards.

### 1.9 Genuinely still open (all Linux-only, all research-grade)

1. **NVIDIA-VRAM-export → AMD-import, with residency measured.** `nv_dma_buf_attach` refuses only
   *NVIDIA* GPU attachers, not foreign ones, and `nv-dmabuf.c` does emit BAR1 physical addresses for
   framebuffer memory. A third party got working P2P on a Quadro RTX 5000 with an **FPGA** as bus
   master after removing the C2C/framebufferless checks. **Nobody has published the GPU-as-importer
   variant.** Highest-value open experiment; needs a patched open kernel module.
2. **AMD/Intel exporter → foreign importer when the topology gate actually passes.** An **external
   PCIe switch chassis** could make `pci_p2pdma_distance()` succeed. This is the one place where the
   hardware plan could change the answer. Requires both GPUs behind one switch, ACS off, IOMMU
   passthrough.
3. **Residency measurement methodology.** No project found — including the one claiming a positive —
   measures whether bytes were in VRAM or GTT at transfer time. Building that measurement
   (`mem_info_vram_used` / `mem_info_gtt_used` sysfs deltas around a transfer) is cheap, novel, and
   is exactly the discriminator `09_FULL_GOAL_GATE_REGISTER.md` already demands.
4. **`VK_EXT_external_memory_host` HOST_MAPPED_FOREIGN_MEMORY.** Measured feature mask `0x0` on both
   installed GPUs. Re-query on driver updates; cheap.
5. Track (do not build on) the dma-buf mapping-type/PAL and `p2pdma_provider` kernel series.

### 1.10 First-hand verification from the vendored Intel primary sources (added 2026-10-05)

Two Intel primary sources are already on disk and were read directly this session, offline, with no
network dependency. They **upgrade several §1.7 claims from delegated to first-hand**, and they
**contradict one load-bearing claim**. This section supersedes the corresponding parts of §1.7 and
§2.2 where they differ.

Sources, both under
`records\root_continuation_20261004\intel_multi_arc_ze_peer_research_20261004T230000Z\`:
- `intel_863931_rev1p0.pdf` — 27 pages, 3,158,833 bytes, extracted with PyMuPDF 1.27.2 (34,649 chars).
  Title page: *"Platform Evaluation User Guide for Intel® Multiple GPU Solution"*, Document Number
  863931-1.0, September 2025. Revision history: *"Initial release for B60 Pro."*
- `issue_921.json` + `issue_921_comments.json` — `intel/compute-runtime#921`, parsed with `json`.

#### Now FIRST-HAND confirmed (previously listed as delegated in §6.2)

| Claim | First-hand source |
|---|---|
| The Intel multi-GPU family is **Arc Pro B50 / B60 / B70**, and "Arc Pro" is the correct branding | #921 title: *"…(regression NEO 25.40→25.44, Arc Pro B50/B60/B70)"*; `sycl-ls` output in #921 body: `Intel(R) Arc(TM) Pro B60 Graphics` |
| Device IDs: **B60 = 0xe211**, **B70 = 0xe223** (Battlemage G31) | #921 comment 5 and body `lspci` |
| **`zeDeviceCanAccessPeer` returns `canAccess=1` in BOTH directions on 2× Arc Pro B60** | #921 comment 5: `P2P 0 -> 1: ze_result=0x0 canAccess=1` / `P2P 1 -> 0: ze_result=0x0 canAccess=1` |
| **Regression window NEO 25.40 good → 25.44/25.48 broken** | #921 comment 2 *"Can confirm, the regression is between NEO 25.40 and 25.48"*; comment 4 names working `25.40.35563.4` vs broken `25.44.36015.5/.8`; root cause = BMG internal engine/context init changed eager→deferred |
| **AMD AM5 host runs Intel Arc P2P** — this is the load-bearing one for reusing the existing MSI PRO X870-P | #921 comment 16 hardware block: *"2x Intel Arc Pro B60, device ID 8086:e211 — **AMD AM5 / PCIe 5.0 motherboard** — Both GPUs linked at PCIe 5.0 x8"*; comment 27 (most recent, 2026-06-28): *"**Verified P2P works on AM5 host with 7.1.2 kernel, Intel Compute 26.22.38646.4**"* |
| **The kernel chipset allow-list is the actual gate** | #921 comment 25 asks *"does this mean Intel B70's can actually do P2P DMA if the kernel allow lists the chipset?"* — comment 26 answers *"**Yes**, though make sure you have the latest 7.1 kernel"* |
| **VRAM compression corrupts P2P reads**; workaround `NEOReadDebugKeys=1 RenderCompressedBuffersEnabled=0` | #921 comments 19–21, 24; Intel contributor `jwarchul` (comment 23) confirms it as one of *"two distinct issues"* |
| Fixes are merged: `e91243a9d03de849f45d8b862a62afd4424cff8b` (pre-7.1 kernels) and `258518f8039afba59c46d98bb7f6f068d12f026d` (compression); kernel ≥ 7.1 | #921 comment 23 (Intel CONTRIBUTOR), comment 24 (reporter confirms resolved). **Both commit hashes are vendored on disk as `*.commit.json` in the same directory.** |
| Linux-only | #921 labels: `Type: Bug`, **`OS: Linux`**, `Status: Merged`; doc 863931 uses Ubuntu throughout (`lspci -vvv` "under Ubuntu", `intel_iommu=off` in grub) and contains **zero** occurrences of "Windows" |
| **Disable PCIe ACS and IOMMU** — Intel's own instruction, with the reason | doc 863931 §2.0, p9: *"Suggest disabling the PCIe ACS (Access Control Service) and IOMMU features. **ACS would route all the data transfer back to the root complex.** IOMMU would introduce unnecessary address translation. **Both features would block the P2P transfer.**"* Verified by `ACS-` in `lspci -vvv` (ARICtl). |
| `ze_peer` (P2P) and `ze_peak` (bandwidth) from `oneapi-src/level-zero-tests`; oneCCL for AllReduce/AllGather/AllToAll | doc 863931 §3.0, p12 |
| **B60 Pro, PCIe Gen5 x8: ~20 GB/s unidirectional write between two devices, up to 40 GB/s bidirectional** | doc 863931 p14, verbatim |
| **4-GPU ring: `--parallel_pair_targets 0:1,1:2,2:3,3:0 -z 134217728 -o write -v -c` → ~20 GB/s per pair, 79.37 GB/s total for 512 MB** | doc 863931 p18, verbatim |
| **The `-c` known tool defect** — per-pair bandwidth wrong, total correct | doc 863931 p18, verbatim: *"When '-c' option added, there is a known issue that the bandwidth of each pair is not correct, but the total bandwidth is correct."* |
| Cross-socket P2P is UPI-limited | doc 863931 p14: *"If 2 GPUs are under different CPU sockets, the P2P throughput would be impacted by the UPI connection as well."* |
| Bandwidth arithmetic: Gen5 x8 = 32 GB/s bus, **24 GB/s payload** after 128/130 encoding + TLP; 22.7 GB/s D2H measured is "reasonable" | doc 863931 p19 |

#### CONTRADICTION — §2.2's "a real external PCIe switch is required" is TOO STRONG

Doc 863931 contains **zero** occurrences of "switch", "root port", "Re-size"/"Resizable BAR", or
"VT-d". Its entire topology prescription is *disable ACS and disable IOMMU*. And #921 comment 16 has
2× Arc Pro B60 doing P2P on an ordinary **AMD AM5 motherboard** with both cards at PCIe 5.0 x8 — no
switch mentioned — with comment 27 later verifying P2P works on that class of host.

**Corrected rule:** the gate is the **kernel's chipset allow-list plus ACS/IOMMU state**, not the
presence of a PCIe switch. On an **AMD Zen host** (`family >= 0x17`) the allow-list passes without a
switch. A switch is what you need on a host whose root complex is *not* allow-listed — notably
consumer **Intel** desktop chipsets. Since the existing host is AM5 (MSI PRO X870-P, Ryzen 7 7700),
**no PCIe switch chassis is required for the Intel Arc arm.** That materially lowers the cost of the
Intel path and reverses part of §2.2's purchasing conclusion. The bifurcation caveat still stands for
a different reason: four x4 branches are four separate root ports and would each need to pass the
gate, whereas #921's working rigs use x8 links.

#### Still UNVERIFIED after this pass

- **VRAM capacities.** Doc 863931 contains **zero** occurrences of "VRAM", "graphics memory",
  "24 GB" or "32 GB" *as capacities* — its only "24GB" and "32GB" hits are **PCIe bandwidth** figures
  (24 GB/s payload, 32 GB/s bus). The B60 = 24 GB / B70 = 32 GB capacities therefore have **no**
  support in either vendored source. The only capacity-shaped evidence is a `lspci` capture in #921
  showing `Physical Resizable BAR — BAR 2: current size: 32GB` and `Region 2 … [size=32G]` on a B70,
  which is *consistent with* 32 GB VRAM under full ReBAR but is a BAR aperture size, not a stated
  capacity. **Treat both capacities as unconfirmed.** Given the earlier "24 GB"/"32 GB" figures match
  this document's bandwidth numbers exactly, a bandwidth↔capacity transcription error somewhere
  upstream is a live possibility. Confirm from Intel ARK before any purchase.
- **The iGPU+dGPU = No / diff-gen dGPU+dGPU = No compatibility table.** Zero occurrences of "iGPU" or
  "dGPU" in doc 863931, and none in #921. This table is **not** from either vendored source. It is
  presumably from Intel's multi-Arc quick-start guide, which is **not vendored on disk** and could not
  be fetched (intel.com 301→404). Unconfirmed.
- **Project Battlematrix "up to 8 GPUs / up to 192 GB combined VRAM".** Zero occurrences of "192",
  "8 GPUs", "combined" or "aggregate" in doc 863931. Not vendored, not fetchable. Unconfirmed.
- **The 28.00 GB/s / checksum-PASS-on-268,435,456-bytes measurement** and the
  **ACS-redirect ON→refuse / OFF→pass** A/B result. Not in either vendored source; third-party only.
  Note doc 863931's own first-hand calibration is **~20 GB/s unidirectional / 40 GB/s bidirectional on
  Gen5 x8** — use Intel's numbers as the baseline and treat 28 GB/s as a third-party data point
  (plausible: it sits between, and that rig was Gen4 x8 behind a switch).
- **`multi-arc-bmg-offline-installer-26.18.8.2-combo`.** Not named in either vendored source. #921
  comment 21 instead prescribes: kernel ≥ 7.1, `intel-compute-runtime ≥ 26.18`, oneAPI 2026.0+, and
  `NEOReadDebugKeys=1 RenderCompressedBuffersEnabled=0`. Comment 27's verified-good stack is
  **kernel 7.1.2 + Intel Compute 26.22.38646.4** — prefer that, it is the most recent confirmed-good.

#### Net effect on the Intel arm — materially better than §1.7 implied

§1.7 framed Intel multi-Arc as fragile and switch-gated. The vendored evidence says something
stronger and more usable: **as of 2026-06-28, 2× and 4× Arc Pro B60/B70 P2P is verified working on an
AMD AM5 host with kernel ≥ 7.1 and Intel Compute ≥ 26.22**, the blocking regressions are **merged and
closed** (#921 `state: closed`, `state_reason: completed`, `Status: Merged`), and an Intel contributor
confirmed the fixes. The operator's existing AM5 motherboard is in the working class.

What has **not** changed: this is all **same-vendor Intel** P2P. Nothing in either source touches
cross-vendor peer access, and #921 comment 18 records that the multi-GPU **Vulkan** backend has
*"atrocious, even negative performance gains per added gpu"* — so the Vulkan fallback is not a
substitute. The §1.1–§1.5 cross-vendor verdict is unaffected.

**Also note the honest caveat in #921 comment 11:** *"Seems Arc Pro is low priority (few people have
them)"* — written 2026-05-17, before the Intel fix landed. Support responsiveness on this platform is
thin, and the regression window (25.40→25.44 breaking, fixed only by 26.18/26.22 + kernel 7.1) shows
the stack can break silently between releases. **Pin kernel and compute-runtime versions and re-run
Tier 0 after any update.**

## Part 2 — The plan that actually works

Because direct cross-vendor P2P is unavailable, J-Link's deliverable must be **explicit sharded
placement over a host-staged tensor bridge**. This is not a compromise; it is what NCCL itself does
when P2P is unavailable, and what llama.cpp RPC does across processes.

### 2.1 Architecture (promotes `02_J_LINK_RESEARCH.md` Ideas 2 and 3 from "fallback" to "the route")

1. **Vendor-native worker processes** — separate CUDA / HIP / SYCL(→Intel) / Vulkan processes, each
   owning its own allocations and kernels, joined by a coordinator that moves bounded buffers
   through host memory with sequence numbers and explicit completion events.
2. **Never pass a foreign raw pointer.** A tensor is `{object_id, owning worker/device, shape, dtype,
   bytes, generation, checksum}`.
3. **Coarse-grained pipeline/expert placement, not tensor parallelism.** Maximize compute per
   boundary byte: whole layers, whole experts, whole stages. Tensor-parallel all-reduces across a
   host-staged boundary will lose to a single GPU — and there is no collective library that can even
   *express* a mixed-vendor communicator (§1.5).
4. **Vulkan separate device objects for the first mixed-vendor run** (never a device group);
   vendor-native RPC workers for production.
5. **Add the residency gate nobody else has.** Per transfer, record source and destination
   dedicated-vs-shared bytes before and after, plus a sysfs/ADL/NVML delta proving the payload left
   dedicated VRAM and re-entered dedicated VRAM. Without this, a passing byte-comparison is
   indistinguishable from the false-positive class documented in §1.4.

### 2.2 Load-bearing purchasing conclusion

> **CORRECTED 2026-10-05 by §1.10.** An earlier revision of this section asserted that "only a real
> external PCIe switch can move the topology gate." That is **too strong** and is superseded. The
> first-hand vendored evidence (`intel/compute-runtime#921` comments 16, 25–27) shows Intel Arc Pro
> P2P working on an ordinary **AMD AM5** motherboard with no switch. Read §1.10 before relying on any
> part of this section.

**For pooled capacity, four same-vendor cards strictly dominate any mixed-vendor population**,
because a mixed population can only ever use the host-staged path, while a same-vendor population
gets that vendor's own P2P (CUDA / HIP / Level Zero) subject to a directed probe. This conclusion is
unchanged and is the single most important purchasing fact in this document.

**The peer-access gate is the kernel's chipset allow-list plus BIOS ACS/IOMMU state — not the
presence of a PCIe switch.** Corrected rule:

- **AMD Zen host (`family >= 0x17`)** — allow-list passes without a switch. Verified working:
  2× Arc Pro B60 on AM5 at PCIe 5.0 x8, and P2P confirmed on an AM5 host with kernel 7.1.2 +
  Intel Compute 26.22.38646.4 (#921 comments 16, 27). **The existing MSI PRO X870-P / Ryzen 7 7700
  is in this class, so no switch chassis is required for an Intel Arc arm.**
- **Consumer Intel desktop host** — root complex is *not* allow-listed; this is where a real external
  PCIe switch (or a patched kernel) becomes necessary.
- Either way, Intel's own instruction applies: **disable PCIe ACS and IOMMU**, because *"ACS would
  route all the data transfer back to the root complex"* and *"Both features would block the P2P
  transfer"* (doc 863931 §2.0).

**Bifurcation caveat, restated on the correct grounds.** Motherboard x4/x4/x4/x4 bifurcation still
does not give you a four-card P2P domain, but the reason is not "no switch." It is that the four
branches are four separate CPU root ports, each of which must independently pass the gate, and every
verified-working rig in the vendored evidence uses **x8** links, not x4. Bandwidth also halves:
doc 863931's ~20 GB/s unidirectional / 40 GB/s bidirectional figures are for **Gen5 x8**; a Gen4 x4
branch has a ~6.5 GB/s realistic one-way ceiling (§2.3). This directly affects the planned
MSI PRO X870-P E1 four-branch layout and is recorded against `01_HARNESS_MASTER.md`.

**Practical consequence for a purchase decision:** if peer bandwidth matters, prefer **fewer cards on
wider links** (2× at x8/x16) over **four cards at x4**. Four x4 cards maximize aggregate capacity but
minimize per-pair bandwidth and multiply the gate risk. Two configurations worth costing:
- **2× Arc Pro B70 at x8/x16** — best per-pair bandwidth, lowest gate risk, smaller capacity.
- **4× Arc Pro B60 at x4** — best aggregate capacity, ~half the per-pair bandwidth, four gates to pass.

**Do not order until the VRAM capacities are confirmed** (§1.10 "Still UNVERIFIED"): the 24 GB / 32 GB
figures have no support in either vendored Intel source and suspiciously match that document's PCIe
*bandwidth* numbers. Confirm from Intel ARK first.


**The qualified Intel path, restated from the first-hand evidence in §1.10** (this replaces an
earlier version of this paragraph that required a PCIe switch and cited an unverifiable installer):

- **Cards:** 2+ Intel Arc Pro B60 and/or B70 (Battlemage; B60 = `0xe211`, B70 = `0xe223`), **same
  generation and family**. Confirm VRAM capacities from Intel ARK before ordering — they are not
  established by any vendored source.
- **Host:** Linux. An **AMD Zen (AM5) host passes the kernel allow-list without a PCIe switch** —
  verified working (#921 comments 16, 27). A consumer Intel desktop host is the case that needs a
  switch or a patched kernel.
- **Known-good stack, most recent confirmation 2026-06-28:** **kernel ≥ 7.1** (7.1.2 verified) +
  **Intel compute-runtime ≥ 26.22** (26.22.38646.4 verified). The earlier `≥ 26.18` guidance and the
  `multi-arc-bmg-offline-installer-26.18.8.2-combo` pin are **not** named in either vendored source —
  prefer the 7.1.2 / 26.22 combination, which is the one explicitly reported working.
- **BIOS:** disable **PCIe ACS** and **IOMMU** (Intel doc 863931 §2.0: both "would block the P2P
  transfer"). Verify with `lspci -vvv` showing `ACS-` under Ubuntu. `intel_iommu=off` in grub, then
  `update-grub` and reboot.
- **Runtime env for multi-device workloads:** `NEOReadDebugKeys=1 RenderCompressedBuffersEnabled=0`
  until the compression fix is confirmed present in the installed runtime — without it, **P2P reads
  return garbage** (#921 comments 19–21).
- **Link width matters:** every verified-working rig uses **x8**, and Intel's ~20/40 GB/s figures are
  for **Gen5 x8**. A four-way x4 bifurcation halves that and multiplies the gate risk (§2.2).
- **Unqualified:** consumer Arc (B580/B570/A770) carries no peer qualification in any vendored
  source; **Windows is unqualified** — #921 is labelled `OS: Linux`, doc 863931 never mentions
  Windows, and `ze_peer` is excluded from the build on non-UNIX.
- **Version-pin discipline is mandatory:** the NEO 25.40 → 25.44/25.48 regression silently broke
  multi-BMG enumeration and was only resolved by kernel 7.1 + compute-runtime 26.18/26.22. Pin both
  and re-run Tier 0 after any update. #921 comment 11 also records that *"Arc Pro is low priority
  (few people have them)"* — expect thin vendor support.


### 2.3 Performance ceiling (design against these numbers)

Host staging costs **two** PCIe traversals per boundary crossing, serialized unless double-buffered.

| Link | Theoretical | Realistic | Host-staged round trip | Pipelined double-buffer |
|---|---|---|---|---|
| PCIe 5.0 x16 | 64 GB/s | ~50–55 GB/s | ~25–27 GB/s | ~50 GB/s |
| PCIe 4.0 x16 | 32 GB/s | ~25 GB/s | ~12.5 GB/s | ~25 GB/s |
| **PCIe 4.0 x4** (the planned branches) | 8 GB/s | ~6.5 GB/s | **~3.2 GB/s** | ~6.5 GB/s |
| PCIe 4.0 x1 | 2 GB/s | ~1.6 GB/s | ~0.8 GB/s | ~1.6 GB/s |

Corroborating real cross-vendor measurements: host-staged 3.5 GiB/s symmetric, optimized to
8.61 GiB/s for 256 MiB; a cross-vendor shared host arena at 5.2–6.1 GiB/s. These sit exactly where
x4/x8 host-staged theory predicts.

Consequence for LLM inference: single-request decode traverses pipeline stages **sequentially**, so
N cards do not give N× speed. **Expect capacity wins, not throughput wins.** At a pipelined
6.5 GB/s on x4, a 4 MiB boundary crossing is ~0.6 ms.

Hard ceilings that no software can beat without new hardware: no shared address space, no
cross-vendor atomics, no NVLink/xGMI/UALink-class bandwidth, and no way to run one kernel that
dereferences a pointer resident on another vendor's card. **Design every operator boundary as an
explicit copy.**

### 2.4 Directed test matrices

Directed off-diagonal pairs for *n* cards = **n(n−1)**: 2 cards → 2, 3 cards → 6, **4 cards → 12**,
adding the 5070 Ti for a *mixed-vendor host-staged* matrix → 20.

**Clarification to `02_J_LINK_RESEARCH.md` line 93** *(corrected 2026-10-05 — an earlier revision of
this document wrongly asserted that line 93 said "20 pairs for four cards"; it does not)*: the pair
counts there are already arithmetically correct — *"Four external cards require 12 directed
off-diagonal pairs; adding the display 5070 Ti requires 20."* The residual defect is narrower and is
one of **labelling**, not arithmetic. The 20 is unlabelled, and it sits under a plan whose item 2
covers "directed CUDA/HIP/**Level Zero** capability queries", so a reader can carry 20 into the Level
Zero matrix. It must not: the RTX 5070 Ti is not a Level Zero device at all, so no
`zeDeviceCanAccessPeer` pair involving it can be constructed and the **Level Zero** directed matrix
for four Arcs stays at **12**. Label 20 as host-staged/mixed-vendor only. On the current host the
runnable pair count is **zero**.

**Engine-count ceiling:** Intel reports two engines per B60 Pro device (one compute+copy, one
copy-only), so a 12-flow full mesh on four cards is **not schedulable**. Intel's own four-card
example uses exactly **4 flows**. Cap concurrency at `min(n·E, available engines)` and record the
engine map from `ze_peer -q` first.

Intel peer tiers, in order, each gated on the previous:

- **Tier 0 capability** — inventory and alias dedup; `zeDeviceCanAccessPeer(A,B)` **and** `(B,A)`
  recorded separately; `zeDeviceGetP2PProperties` with `ACCESS` and `ATOMICS` recorded separately
  (`ACCESS=1, ATOMICS=0` permits copies but not remote atomics, which constrains all-reduce design);
  memory ordinals; engine map; `lspci -vvv` ACS state and host-bridge vendor:ID; negotiated
  `LnkSta`. If any directed query is false, that pair is **REFUSED** — record it, do not attempt
  copies.
- **Tier 1 correctness** — `ze_peer -t transfer_bw -z <size> -o {write,read} -s A -d B -v` at
  8 KiB / 4 MiB / 64 MiB / 256 MB, repeated with `--regular_cmdlist`, with `-x src` and `-x dst`,
  on the copy-only engine, and cross-process with `--ipc`.
- **Tier 2 performance** — bandwidth write/read, latency, bidirectional (`-b`), multi-engine single
  target. Calibration figures, split by evidence grade:
  - **First-hand (Intel doc 863931 rev 1.0, read this session):** B60 Pro at **Gen5 x8** ≈ **20 GB/s
    unidirectional** write, up to **40 GB/s bidirectional**; 4-card ring **79.37 GB/s** total for
    512 MB (~20 GB/s per pair). Gen5 x8 = 32 GB/s bus, **24 GB/s payload** after 128/130 encoding and
    TLP overhead; 22.7 GB/s D2H is called "reasonable". **Design against these.**
  - **Third-party, two distinct and unreconciled figures — do not treat either as a target:**
    (a) B70 behind a **Gen4 switch**: **28.5 GB/s per direction, 56.5 GB/s bidirectional write**,
    checksum clean; (b) a separate report of **28.00 GB/s with checksum PASS on 268,435,456 /
    268,435,456 bytes**, ACS redirect OFF (and refused with ACS redirect ON). These are close but not
    identical and come from different rigs/sources; neither appears in any vendored Intel document and
    neither was re-verified. **The discrepancy is recorded rather than resolved.** Note both sit
    *above* Intel's own Gen5-x8 unidirectional figure, which is unexpected for a Gen4 link and is a
    reason to treat them as unvalidated until reproduced with control N1 alongside.

- **Tier 3 rings/concurrency (n≥3)** — scatter; all `(n−1)!` distinct directed rings (2 for n=3,
  **6 for n=4**); disjoint perfect matchings; bidirectional ring; gather. Intel's own four-card ring
  is `ze_peer -t transfer_bw --parallel_pair_targets 0:1,1:2,2:3,3:0 -z 134217728 -o write -v -c`.
  Known tool defect: with `-c`, per-pair bandwidth is wrong while the total is correct — take
  per-pair numbers from non-`-c` runs.
- **Tier 4 workload** — `CCL_TOPO_P2P_ACCESS=1 mpirun -np 4 1ccl_benchmark -l allreduce ...`, then
  `allgather` / `alltoall`, then GEMM sanity. **Support-tier caveat (resolves an ambiguity in this
  document):** §1.5 records that oneCCL *officially* supports Intel Data Center GPU Max only, while
  this tier and the §1.7 ~15% figure both rely on oneCCL's Arc/Battlemage flags. These are not in
  conflict but they are different tiers, and Tier 4 must be read as running in the **documented-but-
  not-officially-supported Arc/BMG tier**: oneCCL's README ships explicit Arc/BMG build flags and
  `CCL_TOPO_P2P_ACCESS` works there, but Intel does not list Arc Pro as a supported product. Treat
  any Tier 4 result as **engineering evidence, not a vendor support commitment**, and record the exact
  oneCCL version, build flags and whether the Arc/BMG path was compiled in. Do not cite a Tier 4
  number as Intel-supported without that record. Linux only — oneCCL has no native Windows build.

**Mandatory negative controls:** (N1) host-staged two-hop at the same sizes must be **materially
slower** (~3 GB/s vs ~28 GB/s peer, ≈9×) — if a "P2P" number is at or below the host-staged number,
**it is host-staged**; this is the single most important control. (N2) checksum on every transfer,
because `ZE_RESULT_SUCCESS` with 100% corrupt data is a documented reachable state. (N3) query-vs-
outcome consistency in both directions. (N4) ACS-redirect on/off toggle on the same boot.
(N5) IOMMU on/off. (N6) `CCL_TOPO_P2P_ACCESS=0` vs `=1`. (N7) same-device ceiling. (N8)
`NEOReadDebugKeys=1 RenderCompressdBuffersEnabled=0` for D2D, without which Intel documents the
bandwidth is **doubled** spuriously. (N9) cross-generation pair → must refuse. (N10) iGPU+dGPU pair
→ must refuse. (N11) consumer-Arc substitution → expect refusal, establishes whether Arc-Pro scoping
is a real capability limit or only a documentation limit. (N12) single-card `ze_peak` sanity.
(N13) driver-version regression pair across the installer pin and a newer hand-installed NEO.

**Also record: a green Level Zero conformance run proves nothing about cross-card peer access.** At
the pinned commit `88447c0` — whose entire purpose was *"Add new zeDeviceCanAccessPeer scenarios"* —
every P2P conformance test is vacuous for two distinct physical cards: one asserts only
`EXPECT_EQ(a2b, b2a)` (symmetry; `false == false` passes), two call `get_p2p_properties` with **no
assertion on the result at all**, and the newly added tests assert only the trivial self-peer cases.
All `GTEST_SKIP()` when device count < 2. **A full PASS on a single-GPU machine is indistinguishable
from a full PASS on a qualified four-card machine.**

## Part 3 — Software that must be fixed before any hardware arrives

Current state, from receipts on disk and from commands re-run this session (all first-hand, exit 0):

**Passing now on this host** — `j_link` unit tests **80/80 OK** (79 before this session's
`_parse_bytes_value` fix, +1 new regression test; an earlier revision of this document said 79/79 in
one place and 80/80 in two others — 80/80 is correct and is the post-fix count); `cad` tests
**15/15 OK**; `planner.py` on `examples/mixed.json` → `PLANNED_NOT_ALLOCATED`, exit 0;
`verify_adaptation.py` against the newest dated `records\ADAPTATION_SHA256_*.json` (currently
`..._20261005_110323Z.json`) → **219 checked, 0 failures**, exit 0
(re-pinned this cycle after the documentation corrections below drifted the prior
`..._20261004_2148Z.json` manifest, which by project convention remains immutable and still records
that drift; same 219 paths, current hashes, `prior_manifest` chained. Cite it newest-by-filename-sort,
not by exact stamp, so the reference cannot dangle on the next re-pin);
numpy 2.2.6 + pyopencl 2025.2.6 with both NVIDIA CUDA and AMD platforms enumerating.

**RED / failing and unresolved:**

| Item | Receipt | Failure |
|---|---|---|
| Completion/FD adapter v3 | `records\root_continuation_20261004\l0_egl_adapter_root_qa_v3_20261004T2254Z\runs\pure_qa_20261004T225945Z\receipt.json` | `PURE_QA_FAILED_OR_INCOMPLETE`, returncode 1 — 10 methods, 9 failure events, 1 error, 1 pass. Unaccepted. |
| Completion/FD adapter v2 | `...\l0_egl_adapter_root_qa_v2_20261004T2228Z\runs\outer_20261004T2240Z\RESULT_ADJUDICATION.md` | READY produced with export FD `-1`; string `"false"` accepted; `inf`/`nan` deadlines accepted; callback `RuntimeError` escapes `run()`. |
| Original Q8_0 Vulkan parity | `records\vulkan_llm_qualification_20261004\whole_model_qualification_receipt.md` | `REAL_INFERENCE_EXECUTED_NUMERIC_PARITY_FAILED` — 99,853/151,936 failing logits default, 99,891 reverse; corruption control inconclusive because the baseline already failed. |
| Combined CUDA + Level Zero source | `...\cuda_l0_source_compile_20261004T202000Z_attempt2\compile_qa_findings.md` | `COMPILE_FAILED`, 10 diagnostics over 8 distinct call sites, no object produced. |
| Original L0 collector | `...\l0_query_replacement_audit_20261004T211418Z\STUB_ADJUDICATION_EXECUTED.md` | 4 proved defects: unquoted hex breaks JSON; external-properties query compiled out by `#if defined(<enum token>)`; `DEVICE_LOST` mislabelled; root count has no UUID dedup. |
| Original provider peer-copy | `...\l0_peer_errorcode_compile_20261004T2151Z\stub_runs_20261004T220255Z\case_results.json` | `pending_teardowns=7`, `pending_at_exit=1` — teardown while work pending; surplus CLI args silently ignored (exit 0); wrong API attributed. |
| ~~`device_inventory.py` latent defect~~ **FIXED this session** | `j_link\device_inventory.py`, `_parse_bytes_value` | **Was:** an unconditional `return _finite_whole(raw)` made the entire `isinstance(raw, str)` branch **unreachable dead code**, so string-typed AMD `dedicated_memory_bytes` / Intel `memory_size` always yielded `None` → `invalid_total`. **Now fixed and regression-tested.** The numeric return is guarded by `isinstance(raw, (int, float))`, making the string branch reachable and matching sibling `_parse_mib_value`. Verified before/after by direct probe: `_parse_bytes_value('17179869184')` was `None`, now `17179869184`. **Safety property proven, not assumed:** `_extract_amd` hardcodes `'observed_free_bytes': None` and `_parse_bytes_value` is called only from the AMD and Intel extractors, so no admission decision can flip from refused to eligible — the string case still ends `eligible_count = 0`, with the refusal reason correctly moving from `invalid_total` to `unknown_free`. New test `test_string_byte_values_parsed_but_never_admitted` pins all ten parser cases plus that end-to-end refusal. Suite went 79 → **80 tests, OK, exit 0**; the 219-entry integrity manifest still passes (`device_inventory.py` and its test are not among the 219 pinned paths, verified by direct grep of the manifest). |

**Structural notes:** `device_inventory.py` and `cad\integrated_core.py` are **libraries with no
entry point** — no `main()`, no `argparse`. Any claim that they "run" as CLIs is wrong.
`integrated_core.build()` cannot run under the default `python` 3.10.11 (`find_spec('FreeCAD')` →
`None`); a 3.11 interpreter previously compiled it. `rpc_smoke.cpp` (two-worker) has **no binary on
disk** and its documented build path is Linux `g++` against a `GGML_RPC=ON` llama.cpp build.
`scripts\audit_local_projects.ps1` — the newest file in the repo — has **never been run**
(`records\local_audit` absent) although both scan roots exist.

**Prepared-but-unrun work, classified:**

- **Executable now (no new hardware):** Windows CUDA capability inventory (`nvcuda.dll` present and
  pinned; spec is `cuInit`-only and allocation-free) — but no source exists yet, the request was
  interrupted at zero content; original Q8_0 parity diagnostic (the 639,446,688-byte model and the
  attempt-5 Vulkan binaries are both present and hash-matched); completion/FD adapter repair (pure
  Python, no hardware dependency); collector CPU-fake v2 (WSL Ubuntu-24.04 + GCC 13.3 available;
  gated on review admission, not hardware).
- **Blocked on hardware that is not installed:** Intel SYSMAN inventory (zero Intel GPUs, no
  `ze_loader.dll`; its own spec returns status `NOT_CHECKED` with exit code 2 by construction — the
  status token carries no numeric suffix, per the root adjudication rule *"Do not suffix status names
  with exit numbers"*); reverse
  NVIDIA-Vulkan→Intel-Level-Zero route (needs an Intel L0 root device as dma-buf importer, plus
  Linux); multi-Arc experiment matrix (needs ≥2 Intel Arc cards).
- **Blocked for other reasons:** the larger-reply NV-EGL consumer retry was never prepared, and its
  predecessor hit `finish_reason=length` at 155,407 tokens with a 43,835-character artifact
  exceeding the 32 KiB cap.

## Part 4 — Recommended execution order

1. ~~Fix the `device_inventory._parse_bytes_value` dead-code branch~~ **DONE this session** (see
   Part 3; 80/80 tests OK, integrity manifest unaffected). Remaining RED software that needs no
   hardware: the completion/FD adapter (v2+v3 findings) and the collector's four proved defects.
   Re-run the suite plus new coverage for each fix.
2. **Adopt ThunderEP's three optimizations in the host-staged bridge (§1.6).** This is the
   highest-value work available without any new hardware, it is backed by measured 2.00×/1.53×
   results on consumer PCIe GPUs, and it applies unchanged to a mixed-vendor coordinator:
   (a) remove ring relay hops so each boundary crossing is a single source→host→destination path
   rather than a multi-hop ring; (b) move boundary data with **DMA/copy engines** instead of compute
   shaders, so transfer does not contend with expert/layer computation and the two can overlap;
   (c) minimize **completion-flag polling** overhead in host memory. Concretely for J-Link: the
   existing `opencl_executor.py` boundary forwarding should be re-profiled against these three axes,
   and the per-stage timing it already records (startup, warm execution, source readback,
   destination upload) is the right instrumentation to prove the gain.
3. Run the prepared **original Q8_0 parity diagnostic** — this is the one open question that could
   change the numerical picture, and everything it needs is already on disk (model 639,446,688 bytes,
   hash-matched; attempt-5 Vulkan binaries present). Do not substitute the dequantized F32 fixture
   and do not widen tolerances.
4. Run the prepared **Windows CUDA capability inventory** (source must be generated and
   compile-admitted first; the earlier request was interrupted at zero content).
5. Build the **residency measurement harness** (§1.9 item 3). This is cheap, novel, and is the only
   thing that can distinguish a real peer path from a silent host bounce.
6. Re-query `HOST_MAPPED_FOREIGN_MEMORY` on each driver update.
7. Only then, if the operator funds hardware: buy **four same-vendor cards** (§2.2), or for the Intel
   arm specifically **2+ Arc Pro B60/B70 on Linux behind a real PCIe switch**, and run the Tier 0–4
   matrix with all thirteen negative controls.
8. Treat every result as scoped. A successful API call, compiler exit, enumeration, benchmark number
   or generated test stub cannot substitute for measured inference with residency evidence.

## Part 5 — What this document does not claim

It does not claim universal impossibility for all future hardware, bespoke drivers, or datacenter
parts. UALink and the open Linux dma-buf/P2PDMA items in §1.9 remain live research questions. It does
not change any recorded PASS or FAIL. It does not select GPU, receiver, riser or PSU SKUs, and it is
not a purchasing recommendation — §2.2 is a conditional engineering consequence, contingent on the
operator deciding to buy anything at all.

## Part 6 — Verification status: what is first-hand and what is not

This document mixes two evidence grades and the difference matters most for the purchasing
conclusion in §2.2. Recorded explicitly so no reader mistakes one for the other.

### 6.1 First-hand — issued and read directly in this session

| Claim | How verified |
|---|---|
| Zero Intel GPUs on this host; one discrete NVIDIA; AMD device is an integrated APU | `Get-CimInstance Win32_VideoController`, `Get-PnpDevice -Class Display`, exhaustive `Get-PnpDevice -PresentOnly:$false` with `VEN_8086` + Arc/Iris/UHD match, `nvidia-smi -L`, and the project's own `enumerate_opencl_devices()`. Reproduced three times. |
| `C:\Windows\System32\ze_loader.dll` absent | `Test-Path` |
| GitHub repo search `cross-vendor GPU peer memory` → `total_count: 0` | HTTP 200 raw JSON read directly |
| GitHub repo search `heterogeneous GPU memory pooling` → `total_count: 0` | HTTP 200 raw JSON read directly |
| ThunderEP = arXiv:2609.40093, RTX 4090/5090, "all inter-GPU transfers traverse CPU memory", 2.00×/1.53× over NCCL | Abstract fetched and read directly via the arXiv search UI |
| `j_link` 80/80 OK, `cad` 15/15 OK, planner exit 0, `verify_adaptation` 219/0 | All four commands executed this session, raw output quoted |
| The `_parse_bytes_value` dead-code defect and its fix | Read in source, demonstrated by direct execution before and after, regression test added |
| `_extract_amd` hardcodes `observed_free_bytes: None`, so the fix cannot flip an admission | Read in source at line 221; confirmed end-to-end by probe (`eligible_count = 0` for both string and int input) |

### 6.2 Delegated — reported by research subagents, NOT re-verified here

> **Partially superseded by §1.10.** The Intel items below were re-verified first-hand from vendored
> primary sources after this list was first written. Items now confirmed are struck through in effect
> — see §1.10's "Now FIRST-HAND confirmed" table for the authoritative split.

Still in the delegated grade: everything in §1.1–§1.5 resting on vendor specifications, kernel source
or third-party measurement. That includes the D3D12 L0 "system memory only" quote, the Vulkan
`OPAQUE_WIN32` UUID-matching requirement, the `pci_p2pdma.c` whitelist contents, the
amdgpu/xe/i915/nvidia dma-buf behaviours, the RCCL/oneCCL "no native Windows build" finding, the
MSCCL++ mutually-exclusive CMake, and the UALink membership and schedule.

**Moved OUT of delegated into first-hand by §1.10:** doc 863931 rev 1.0 contents (including the
ACS/IOMMU requirement, ~20/40 GB/s on Gen5 x8, the 4-GPU ring 79.37 GB/s figure and the `-c` tool
defect); the Arc Pro B50/B60/B70 family and branding; device IDs `0xe211`/`0xe223`;
`zeDeviceCanAccessPeer` returning `canAccess=1` both directions on 2× B60; the NEO 25.40 → 25.44/25.48
regression window; **AM5-host P2P working**; the kernel-allow-list gate; the VRAM-compression P2P
corruption and its `RenderCompressedBuffersEnabled=0` workaround; and the merged fix commits.

**Still delegated and NOT in any vendored source:** the **Battlematrix** figures, the **28.00 GB/s /
checksum-PASS-on-268,435,456-bytes** measurement, the **ACS-redirect ON→refuse / OFF→pass** A/B
result, the **4,194,304-of-4,194,304 silent-corruption** result, the **iGPU+dGPU / diff-gen
compatibility table**, and the **Arc Pro B60 = 24 GB / B70 = 32 GB capacities** (see §1.10 — the
capacities are positively unsupported by both vendored sources and may be a bandwidth↔capacity
transcription error).

**These are credible and internally consistent, and several are corroborated by more than one
independent source, but they were not confirmed first-hand in this session.** They are leads with
strong provenance, not verified facts.

### 6.3 Blocked verification — attempted and failed

- **Every `intel.com` and `ark.intel.com` fetch this session returned HTTP 301 to
  `corpredirect.intel.com/Redirector/404Redirector.aspx`.** Four distinct URLs attempted (Arc Pro B60
  product page, Arc Pro family page, Project Battlematrix developer article, ARK Arc Pro B-series
  series page). None resolved. Therefore the Arc Pro B60/B70 capacities and the Battlematrix
  "up to 8 GPUs / up to 192 GB combined VRAM" figure could **not** be confirmed against Intel
  directly. Re-attempt before any purchase decision.
- **Mitigation found:** Intel doc **863931 rev 1.0** *is* vendored on disk and **was** read offline
  this session via PyMuPDF (`pdftotext` is not installed on this box; PyMuPDF 1.27.2 is). That is how
  §1.10's confirmations were obtained without network access. It did **not** contain the VRAM
  capacities, the compatibility table, the Battlematrix figures, or any mention of a PCIe switch,
  iGPU/dGPU, or Windows.
- **The arXiv API (`export.arxiv.org/api/query`) returned HTTP 429 on every attempt**, so the
  delegated negative-search counts (notably `all:"disaggregated GPU memory"` → 0 results) are
  **UNVERIFIED** and must not be cited as fact. ThunderEP itself was confirmed through the arXiv
  search UI, not the API.

### 6.4 Minimum confirmation set before spending money

Revised after §1.10. Items already discharged are marked done; the remainder are ordered by how much
of the plan they can invalidate.

1. ~~Read Intel doc 863931 offline~~ — **DONE this session.** It confirms the ACS/IOMMU requirement,
   the `ze_peer`/`ze_peak` tooling, the Gen5-x8 bandwidth figures and the 4-GPU ring recipe. It does
   **not** contain VRAM capacities.
2. ~~Confirm AM5-host P2P behaviour~~ — **DONE, first-hand,** from #921 comments 16 and 27: verified
   working on an AM5 host, kernel 7.1.2, Intel Compute 26.22.38646.4. **No PCIe switch required on an
   AMD Zen host.** This is the finding that most improves the plan.
3. **Arc Pro B60 / B70 VRAM capacities — STILL OPEN AND NOW THE HIGHEST PRIORITY.** Unsupported by
   both vendored sources; the "24 GB / 32 GB" figures match doc 863931's PCIe *bandwidth* numbers
   (24 GB/s payload, 32 GB/s bus) exactly, so a transcription error is a live possibility. The only
   capacity-shaped evidence is a `lspci` ReBAR line showing `BAR 2: current size: 32GB` on a B70.
   Capacity drives the entire value proposition, so **confirm from Intel ARK (retry when intel.com
   resolves) before ordering anything.**
4. **Current Intel driver/kernel pins.** Confirmed-good as of 2026-06-28 is **kernel ≥ 7.1 +
   compute-runtime ≥ 26.22**; re-check for a newer regression before purchase, since the
   25.40 → 25.44 break shows this stack can regress silently.
5. **That any cited bandwidth figure is peer DMA and not a host bounce** — control **N1**. Applies to
   the third-party 28.00 GB/s claim; Intel's own ~20/40 GB/s is the safer baseline to design against.
6. **The iGPU+dGPU / diff-gen compatibility table** — not in either vendored source. Matters because
   the host already has an AMD iGPU; if Intel's real guidance excludes iGPU+dGPU mixing it does not
   affect an all-Intel Arc population, but it should be confirmed rather than assumed.
7. **`drivers/pci/p2pdma.c` in the kernel version actually to be installed** — the AMD Zen
   blanket-enable (`family >= 0x17`) is delegated; #921 confirms the *outcome* on AM5 but not the
   mechanism. Read the source in the target kernel before relying on it for a four-card build.

Items 3, 4 and 7 are the ones that can still change the order. Item 3 first.


