# System Blueprint — Universal 3-GPU Pod

## Host baseline

- CPU: AMD Ryzen 7 7700
- Motherboard: MSI PRO X870-P WIFI
- RAM: 64 GB DDR5
- Existing GPU: RTX 5070 Ti 16 GB
- M2_1: occupied
- M2_2: occupied
- M2_3: must remain empty if PCI_E4 is required at x4
- OS/workflow: Windows + WSL2 / local AI stack
- GPU software fabric: **J-Link** (JE Horizon software scheduler/fabric; not NVLink/JTAG)

## Pod philosophy

A pod is a three-GPU physical and power unit. The first pod receives three RTX 3060 12 GB cards, but all mechanical work uses the universal GPU envelope rather than those exact dimensions.

The pod has three logical bay identifiers:

- Bay A
- Bay B
- Bay C

Bay IDs are permanently embossed into the chassis, receiver deck and cable channels. Card model is metadata, not geometry.

## PCIe topology for Pod 1

Motherboard PCI_E1 supports CPU-side x4+x4+x4+x4 bifurcation. The current host adapter is a four-port OCuLink bifurcation card. Pod 1 consumes three of those four branches; the fourth branch remains unused/reserved.

```text
Ryzen 7 7700
  |
  +-- PCI_E1 PCIe 5.0 x16
       BIOS bifurcation x4 / x4 / x4 / x4
       |
       +-- OCuLink A --> Pod 1 / Bay A / x16 mechanical receiver, x4 electrical
       +-- OCuLink B --> Pod 1 / Bay B / x16 mechanical receiver, x4 electrical
       +-- OCuLink C --> Pod 1 / Bay C / x16 mechanical receiver, x4 electrical
       +-- OCuLink D --> RESERVED; no assumption that it powers another full pod

PCI_E4 PCIe 4.0 x4 remains available for the existing 5070 Ti relocation/extension concept.
M2_3 stays empty if preserving PCI_E4 x4.
```

The RIITOP four-port host adapter is the current cost-conscious reference because it explicitly requires x4+x4+x4+x4 bifurcation. It is not part of the printed pod.

## Receiver reference

Current reference receiver: HOOCCC OCuLink GPU Dock kit.

Published attributes:

- PCIe 4.0 x4 input over SFF-8612 OCuLink
- x16 physical slot, x4 electrical
- 50 cm full-pin OCuLink cable included in kit
- PCB 138 × 46 mm
- published mounting spacing 95 mm / 103 mm
- one selected power input: 24-pin ATX **or** 6-pin PCIe **or** 12 V DC input
- 12 V to 3.3 V conversion on board
- no hot-plug assumption

The chassis must not rely on the current receiver forever. Each receiver sits on a removable metal carrier so a later receiver can be adapted by replacing/drilling the metal carrier rather than reprinting the chassis.

## First GPU population

Three MSI RTX 3060 Ventus 2X OC 12GB cards:

- 235 mm length
- 124 mm height
- 42 mm thickness
- 675 g
- 170 W board power
- one 8-pin auxiliary connector

This population is **not** a chassis constraint.

## Future GPU envelope

A future card is mechanically eligible if all three installed cards meet:

- body thickness ≤56 mm each
- height ≤155 mm
- length ≤340 mm with tail-support option
- card mass and center-of-gravity supported by bracket rail + mid-card support + optional tail bridge
- power budget fits the pod PSU and cable map
- receiver / driver / PCIe x4 operation is acceptable for the intended workload

## J-Link implications

J-Link must discover each GPU independently and record:

- pod ID
- bay ID
- PCIe BDF / device ID
- GPU model
- VRAM
- negotiated PCIe generation and width
- idle/load temperature
- power limit and observed board power where supported
- benchmarked host-to-device throughput
- assigned worker/model

Multiple pods are not represented as unified VRAM. J-Link may schedule task parallelism, pipeline parallelism and explicitly configured distributed training, but it must preserve topology awareness.

