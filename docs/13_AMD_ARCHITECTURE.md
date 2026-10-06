# AMD architecture research record (three-vendor arm, 2026-10-05)

FROZEN: Intel/NVIDIA state pinned at
`records/CHECKPOINT_FROZEN_INTEL_NVIDIA_20261005T114254Z.json`. Nothing
below rewrites it. Evidence states: PROVEN / DOCUMENTED / PLAUSIBLE /
SIMULATED / FAILED / BLOCKED / UNKNOWN. Web sources are delegated until
read first-hand; snippet-only items are marked as such.

## 1. Software stack, bottom to top

| Layer | Component | Relevance to cross-vendor P2P |
|---|---|---|
| HW | SDMA engines (per-card DMA, independent of CUs); CP DMA via gfx ring; PCIe BARs + ReBAR | SDMA is the engine that would drive the AMD leg of a pinned pipeline |
| Kernel | `amdgpu` (TTM/GEM, VRAM+GTT domains, dma-buf export), `amdkfd`/KFD (HSA compute, SVM, GEM-handle dma-buf export since 6.8) | Exporter side of every Linux sharing path; silently demotes VRAM->GTT when `pci_p2pdma_distance()` fails |
| Kernel | `pci_p2pdma` whitelist, IOMMU/ATS/PASID, ACS | The topology gate: unlisted host bridge -> NOT_SUPPORTED |
| Runtime | ROCr, HIP (`hipDeviceCanAccessPeer`, `hipMemcpyPeer`, IPC handles), ROCm (Linux native; Windows now ROCm Core SDK train, HIP SDK retired) | Same-vendor P2P API; IPC handles are same-vendor only |
| Portable | Vulkan radv/amdvlk (external memory fd/host/dma-buf), OpenCL | Cross-vendor meeting point; host-allocation import has no UUID restriction |
| Windows | WDDM/D3D12 cross-adapter heaps (L0 system memory only), no native ROCm P2P path | Same L0 staging trap as NVIDIA<->AMD measurement |

## 2. Directional findings (each direction independent)

### AMD -> AMD (same vendor, reference point)
DOCUMENTED + third-party MEASURED: `hipDeviceCanAccessPeer`=1 both ways on
slot-mounted pairs (2x 7900 XTX gfx1100, ROCm 6.4.3; AMD Starship root;
gfx1201 pair at 10.2 GB/s over Gen3 x16 PLX). Constraints: same PCIe root,
PCIe atomics end-to-end (slots, bridges, re-clockers), NOT eGPU/Thunderbolt
enclosures, NOT chipset-switched x4 slots without atomics. This is the
adjacent T2-analog for AMD and the only TRUE_DIRECT_P2P cell with positive
evidence anywhere in J-Link.

### NVIDIA -> AMD / AMD -> NVIDIA
- Windows Vulkan OPAQUE_WIN32: BLOCKED (measured AMD->NVIDIA
  VK_ERROR_UNKNOWN; needs matching driverUUID+deviceUUID).
- D3D12 cross-adapter: DOCUMENTED-staged (256 KiB NVIDIA->AMD PASS here,
  L0-backed by spec). Direction NVIDIA->AMD proven-staged; AMD->NVIDIA
  same mechanism, PLAUSIBLE (not yet run).
- Linux dma-buf: AMD ATTACHER of NVIDIA export is the one open variant
  (nv_dma_buf_attach refuses only NVIDIA GPU attachers). NVIDIA ATTACHER
  of AMD export: BLOCKED (`amdgpu_amdkfd_get_dmabuf_info` refuses foreign
  drivers; GTT-forced). CUDA IMPORT of anything: BLOCKED (no import
  attribute at all). So the dma-buf arrow is one-way at best, and only
  NVIDIA-export->AMD-import is even PLAUSIBLE.
- Third-party measured precedent (delegated, `vulkan-automaton-vm`):
  one VirtualAlloc arena imported as VkDeviceMemory on BOTH an XTX and a
  1080 Ti via VK_EXT_external_memory_host (no UUID restriction on
  HOST_ALLOCATION imports), both GPUs DMA into the same RAM at 3.4 GiB/s
  per direction. That is a measured PINNED_DMA_PIPELINE over a common
  Vulkan layer -- staged, correctly NOT labeled P2P. Corroborates our
  pipeline design and the 5070 Ti 57 GB/s pinned round-trip (faster card,
  faster link).

### Intel <-> AMD
- Same-vendor Intel P2P (2x B60, AM5, DOCUMENTED) does not transfer.
- Windows: same UUID/spec walls as NVIDIA<->AMD. BLOCKED for dedicated
  VRAM; D3D12 L0 path PLAUSIBLE (same API shape as the measured
  NVIDIA->AMD copy, different vendor pair, not yet run).
- Linux dma-buf Intel<->AMD: UNKNOWN leaning BLOCKED (xe falls back to
  system memory off-whitelist; i915 never exports VRAM; amdgpu demotes to
  GTT). No published working instance found.
- Bridge hypothesis (NVIDIA->Intel->AMD without host memory): UNKNOWN.
  Requires TWO working direct legs; zero exist today, so the triangle
  routes through pinned memory until a first direct leg is proven.

## 3. Falsifier lens (assume cross-vendor direct P2P is impossible)

Strongest version of the negative case, with the layer that enforces each
bar:
1. Handle namespaces are per-driver objects (CUDA ordinals, ze driver
   handles, HIP IPC) -- enforced at USER-MODE DRIVER + API.
2. Vulkan groups/UUID match -- enforced at LOADER + SPEC.
3. WDDM L0-only cross-adapter -- enforced at OS MEMORY MANAGER (spec).
4. `pci_p2pdma` whitelist + amdgpu GTT demote + i915 SMEM force -- enforced
   at KERNEL DRIVER.
5. No consumer host bridge in whitelist; ACS/IOMMU redirect -- enforced at
   PCIe FABRIC config + FIRMWARE.
To overturn: produce residency evidence (control R) on two discrete
different-vendor cards. One such receipt overturns bars 1-5 for that path.

## 4. Sideways lenses (adjacent fields worth mining)

- VFIO/PCI passthrough BAR exposure + Proxmox B70 16 GB BAR report:
  BAR sizing is firmware/driver-negotiated, re-check live per card.
- RDMA `nvidia-peermem`/HMM device-private pages: GPU<->NIC pattern that
  proves the kernel CAN map device memory for foreign DMA -- the missing
  piece is a GPU-as-importer, not the mapping primitive.
- `sycl::malloc_device` 1:1 host mirror (ggml 7580507): applies equally to
  AMD staging built on the wrong allocator -- use explicit pinned/host
  allocators on every leg.
- ThunderEP framing (all consumer inter-GPU transfers traverse CPU
  memory): the baseline assumption every TRUE_P2P claim must beat (N1).

## 5. AMD card guidance (purchase-relevant, DOCUMENTED unless noted)

- Same-vendor AMD P2P wants: two identical discrete RDNA cards, slot-mounted
  on CPU roots with end-to-end PCIe atomics, Linux + ROCm, no eGPU chassis.
- RDNA4 = gfx120x (7900 XTX is gfx1100/RDNA3 -- do not confuse device IDs).
- ROCm 10 unifies Windows+Linux SDK (HIP SDK retired); Windows P2P remains
  unqualified -- plan the AMD arm on Linux, same as Intel.
- ReBAR: needed for best Arc performance (Intel); for AMD, BAR sizing +
  above-4G decode govern large-VRAM exposure -- verify per card live.
