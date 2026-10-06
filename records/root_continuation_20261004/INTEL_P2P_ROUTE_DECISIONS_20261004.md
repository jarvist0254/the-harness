# Intel-first J-Link route decisions — 2026-10-04

Scope: user resumed J-Link as P0; chassis/CAD deferred. Direct Intel/Intel and Intel/NVIDIA peer transfers remain requirements. A working host-staged fallback is not acceptance of those requirements.

## Fresh local boundary

Read-only Win32_VideoController inventory at 14:21 EDT enumerated an NVIDIA RTX 5070 Ti and AMD Radeon integrated graphics, and zero Intel GPUs. Evidence: [actual inventory](intel_p2p_inventory_20261004T1820Z.json). This is Windows inventory evidence, not a claim about every backend or remotely available machine. A local Intel peer execution result is currently missing.

## Primary-source routes

1. **Intel/Intel Level Zero: concrete qualification route.** Intel's September 2025 platform guide covers Arc Pro B60 multi-GPU inference and PCIe P2P evaluation using `ze_peer`, with engine selection, payload validation, parallel pairs and collective-style tests. It describes platform routing/configuration prerequisites. Its results apply to that documented hardware and setup; they do not qualify 8 GB A-series Arc cards, this Windows host or mixed-vendor P2P. No host BIOS/IOMMU/ACS changes were made. [Intel guide, sections 1–4](https://cdrdv2-public.intel.com/863931/863931_Platform%20Evaluation%20Guide%20for%20Multi-ARC%20Solution_Rev1p0.pdf).

2. **Peer capability is directional and needs execution.** Level Zero provides `zeDeviceCanAccessPeer` and `zeDeviceGetP2PProperties` for device pairs. J-Link must preserve physical identities, query every directed pair and then validate an actual device-allocation transfer and corruption control. A positive query alone cannot certify payload correctness or physical transport. [Level Zero device API](https://oneapi-src.github.io/level-zero-spec/level-zero/latest/core/api/apis/device.html).

3. **CUDA external-memory interop is not an established mixed-vendor bridge.** NVIDIA's Vulkan and D3D12 interop documentation requires importing/mapping on the same physical device, checked by matching UUID or LUID. Passing an Intel-exported opaque handle into the documented CUDA path is not supported evidence of Intel/NVIDIA peer access. Any different route needs its own API contract and test. [NVIDIA interop guide](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/graphics-interop.html).

4. **Linux DMA-BUF/P2PDMA: investigate driver support and routing.** The kernel documents sharing exported buffers between drivers and conditions on PCIe topology. It normally blocks unsupported routing across hierarchy domains. A standard DMA-BUF handle does not itself prove that both selected GPU drivers can map a peer VRAM allocation without migration or system-memory staging. A valid proof requires exporter/importer driver support, allocation type, synchronization, topology and actual transfer evidence. [Kernel P2PDMA documentation](https://www.kernel.org/doc/html/next/driver-api/pci/p2pdma.html), [DMA-BUF synchronization](https://kernel.org/doc/html/next/driver-api/dma-buf.html).

## Acceptance labels

| Evidence obtained | Permitted result |
|---|---|
| No Intel device in a bounded enumeration | NOT_CHECKED on that host; not globally unsupported |
| Pair capability query only | CAPABILITY_ADVERTISED; no transfer PASS |
| GPU readback → CPU staging → GPU upload | HOST_STAGED_TRANSFER, with scoped correctness result |
| Both GPUs import system RAM | SHARED_HOST_BACKING_NOT_VRAM_P2P, only after actual valid import/execution |
| Peer device allocation transferred with driver/topology evidence, independent byte reference and detected corruption | Scoped DIRECT_PEER_TRANSFER_PASS for the exact directed pair |
| Language-model parity | Compute correctness for that model/run; no implied direct P2P |

Intel driver source reports/reproducers may guide tests but cannot replace a run on the selected consumer cards. A purchase recommendation remains open until the intended SKU, driver, OS and receiver/topology pass. Intel/NVIDIA and AMD/Intel alternatives are assigned to separate Qwen3.8-max jobs; their generated source remains untrusted until reviewed and tested.
