# Current Electrical and Compute Architecture

## Host

- Motherboard: MSI PRO X870-P WIFI
- CPU: AMD Ryzen 7 7700
- Memory: 64 GB DDR5
- Primary accelerator family: NVIDIA CUDA
- Existing GPU: RTX 5070 Ti 16 GB
- M2_1: occupied, unchanged
- M2_2: occupied, unchanged
- M2_3: **must remain empty**

## PCIe map

```text
Ryzen 7 7700 / MSI PRO X870-P WIFI

PCI_E1 CPU PCIe 5.0 x16
  BIOS bifurcation: x4 / x4 / x4 / x4
       |      |      |      |
       |      |      |      +--> Harness position D: future RTX 3060 12GB
       |      |      +---------> Harness position C: RTX 3060 12GB
       |      +----------------> Harness position B: RTX 3060 12GB
       +-----------------------> Harness position A: RTX 3060 12GB

PCI_E4 chipset PCIe 4.0 x4
  +----------------------------> RTX 5070 Ti 16GB on lower shelf

M2_3: EMPTY (otherwise PCI_E4 falls to x2)
```

The host-to-harness x4 links must use a matched PCIe bifurcation transport. OCuLink, SlimSAS/SFF-8654, MCIO or another connector family may be used only when the host splitter, cable and remote receiver are electrically matched for PCIe and preserve required clock/reset/sideband behavior. Connector shape alone does not establish compatibility.

## Why this replaces the old active-switch design

The September 5 dossier used one PCI_E4 Gen4 x4 uplink into an active four-slot switch. The later September 29 design discovered/confirmed that PCI_E1 can be split x4/x4/x4/x4. That gives the 3060 bank four direct CPU-root x4 links instead of forcing every 3060 through a single shared x4 uplink.

The 5070 Ti is then moved to PCI_E4 x4. This is a deliberate bandwidth trade: the strongest card gets a chipset Gen4 x4 path, while the 3060 bank receives four independent CPU-side x4 groups. J-Link must benchmark real host-device throughput and schedule around this asymmetry.

## Population states

### Phase 1

- GPU0: RTX 5070 Ti 16GB
- GPU1: RTX 3060 12GB
- GPU2: RTX 3060 12GB
- GPU3: RTX 3060 12GB
- Harness D: empty
- Physical VRAM: 52GB total across four devices

### Phase 2

- GPU0: RTX 5070 Ti 16GB
- GPU1–GPU4: 4 × RTX 3060 12GB
- Physical VRAM: 64GB total across five devices

## Software operating model

Primary:

- independent resident model workers
- agent/task parallelism
- model-specific worker pinning
- overlapped preprocessing/transfer/compute
- pipeline parallel experiments

Secondary/experimental:

- PyTorch DDP
- DeepSpeed
- FSDP
- explicit model sharding

Do not advertise aggregate VRAM as unified VRAM. Any job spanning GPUs must explicitly use a framework/runtime that supports the chosen parallelism mode.
