# System Architecture — Universal 3-GPU Pod

## Existing host

- CPU: AMD Ryzen 7 7700
- Motherboard: MSI PRO X870-P WIFI
- RAM: 64GB DDR5
- Existing accelerator: RTX 5070 Ti 16GB
- M2_1 and M2_2 remain occupied.
- M2_3 must remain empty if PCI_E4 is expected to remain x4.

MSI documents PCI_E1 as CPU-connected PCIe 5.0 x16 for Ryzen 7000/9000 and supports BIOS bifurcation including x4+x4+x4+x4. MSI also documents PCI_E4 as chipset PCIe 4.0 x4, dropping to x2 if M2_3 is populated.

## Current first-pod topology

```text
Ryzen 7 7700 / MSI PRO X870-P WIFI

PCI_E1 CPU x16
  BIOS bifurcation: x4 / x4 / x4 / x4
        |      |      |      |
        |      |      |      +--> RESERVED host branch / future second-pod experiment
        |      |      +---------> Pod 1 GPU-C receiver x4
        |      +----------------> Pod 1 GPU-B receiver x4
        +-----------------------> Pod 1 GPU-A receiver x4

PCI_E4 chipset Gen4 x4
        +-----------------------> RTX 5070 Ti external/lower-shelf link

M2_3 = EMPTY
```

Only three E1 branches are consumed by Pod 1. The fourth E1 x4 branch is preserved as a future resource. Do not assume it is enough for a full second three-GPU pod; a second pod requires a deliberate new data-uplink design (additional root ports, an active PCIe switch, another host, or another qualified transport).

## Universal-card principle

The pod is mechanically card-agnostic. Electrically, each installed card must be compatible with the selected receiver/transport and host software stack.

First population:
- 3 × MSI RTX 3060 Ventus 2X 12GB
- 12GB GDDR6 each
- 170W each
- 235 × 124 × 42mm each
- 1 × 8-pin PCIe auxiliary power each

These dimensions are validation inputs, not hard chassis dimensions.

## Compute model

J-Link is the JE Horizon software fabric. It is not NVIDIA NVLink and not SEGGER J-Link/JTAG.

J-Link responsibilities:
- device discovery and persistent GPU IDs
- per-device free/used VRAM telemetry
- model residency registry
- workload placement and queueing
- topology/bandwidth benchmark cache
- process/GPU affinity
- worker health and restart policy
- optional distributed training orchestration

Primary operating mode:
- independent resident workers
- task parallelism
- model pinning
- agent parallelism
- pipeline experiments

Secondary mode after validation:
- PyTorch DDP
- DeepSpeed
- FSDP
- explicit model sharding

Aggregate VRAM is physical capacity across devices, not automatic unified VRAM.
