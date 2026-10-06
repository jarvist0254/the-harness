# JE Horizon Multi-GPU Harness — Current Project Handoff

**Revision:** 1.0-draft  
**Date:** 2026-09-30  
**Scope:** Current hardware/mechanical/software architecture after reconciling the September 5 QOVARYX shelf dossier with the September 29 four-card harness discussion.

## Current decision

Build the physical harness for **four RTX 3060-class cards**, but initially populate only **three MSI GeForce RTX 3060 Ventus 2X 12G OC** cards. Leave the fourth position electrically and mechanically serviceable for a later fourth 3060.

The existing **RTX 5070 Ti 16 GB** moves physically to the lower shelf as a separate card from the four-position 3060 bank. It remains part of the host and J-Link software fabric.

### Initial accelerator population

- RTX 5070 Ti 16 GB: 1
- RTX 3060 Ventus 2X 12 GB: 3
- Empty 3060 harness position: 1
- Initial physical VRAM: **52 GB across four CUDA devices**
- Future population with fourth 3060: **64 GB across five CUDA devices**
- VRAM is not automatically pooled or presented as one 52/64 GB CUDA device.

## Current electrical topology

The later September 29 architecture supersedes the earlier single-active-switch plan:

1. **PCI_E1 (CPU, PCIe 5.0 x16)** is configured in BIOS as **x4/x4/x4/x4**.
2. The four x4 groups feed four remote, locally powered x16 receiver/riser positions in the 3060 harness through a matched, validated passive high-speed link system.
3. Initially only three of those four positions are populated.
4. **PCI_E4 (chipset, PCIe 4.0 x4)** feeds the physically relocated RTX 5070 Ti.
5. **M2_3 remains empty** because populating M2_3 reduces PCI_E4 to x2.
6. M2_1 and M2_2 remain unchanged.

MSI documents PCI_E1 bifurcation modes x16, x8+x8, x8+x4+x4, and x4+x4+x4+x4 for Ryzen 7000/9000 on the PRO X870-P WIFI.

## Power-domain decision

Keep the two PSU domains clean:

- **Host PSU:** motherboard, CPU, storage, and the RTX 5070 Ti including both slot and auxiliary power.
- **External harness PSU:** all locally powered 3060 receiver slots, all 3060 auxiliary 8-pin feeds, fan wall/plenum, and low-voltage harness control electronics.

Do not split a single GPU between the host PSU and external PSU. Do not parallel PSU DC outputs.

For the 3060 bank:

- 3 cards = 3 × 170 W = **510 W GPU board power**
- 4 cards = 4 × 170 W = **680 W GPU board power**

A quality **1000 W external PSU** therefore remains appropriate for the four-position 3060 harness with useful margin for powered receivers, fans and control electronics. The 5070 Ti remains on the existing host PSU instead of consuming that external budget.

## Mechanical direction

The current fabrication direction is a **single monolithic printed chassis** integrating:

- four 3060 card supports
- common forced-air plenum
- two 120 mm fan positions
- external PSU saddle / restraint
- cable-management and strain-relief features
- removable blanking/air-dam for the unused fourth GPU position

No 2020 aluminum structural frame is required in the current concept; the September 5 hybrid-rail design is retained only as historical reference.

The later one-piece target from the archived discussion was approximately:

- **188 mm W × 188 mm D × 245–250 mm H printed skeleton**
- Ender-3 S1 Pro nominal build volume: **220 × 220 × 270 mm**
- GPU and PSU bodies are allowed to overhang the printed skeleton where appropriate.

The alternative intermediate concept was a 210–214 mm bank width × 180–188 mm support depth × 160–180 mm height, rotated so the 210–214 mm dimension used printer Z. The 188×188×245–250 concept is the preferred monolithic baseline because it gives more room for the integrated fan wall and PSU saddle while still fitting one Ender-3 S1 Pro print volume.

## J-Link

**J-Link is JE Horizon's multi-GPU software fabric. It is not NVIDIA NVLink and not a Segger J-Link/JTAG device.**

Its intended responsibilities are:

- topology discovery
- per-GPU capability and memory inventory
- memory-aware model/shard placement
- worker health/state tracking
- pinned-host transport and peer transport when actually supported
- overlapped CUDA streams and transfers
- pipeline/task scheduling
- per-link and per-GPU benchmarking
- unified local API over heterogeneous physical links
- workload routing that understands the 5070 Ti and 3060s have different compute and PCIe paths

The primary operating mode is independent resident workers and task/pipeline parallelism. Distributed training is supported experimentally through software such as DDP/DeepSpeed/FSDP, but must be benchmarked rather than assuming memory behaves as one pool.

## Immediate engineering gates

1. Select the exact PCI_E1 x4/x4/x4/x4 host splitter and four matched remote receiver/riser assemblies.
2. Confirm those receivers provide local slot power from the external PSU without backfeeding the motherboard.
3. Measure the exact installed RTX 5070 Ti model and its lower-shelf riser/link route.
4. Measure the exact PSU body and connector projections.
5. Model the 42 mm 3060 thickness plus forced-air gaps in Blender and run a slicer material estimate before committing to a long monolithic print.
6. Print small coupons for screw holes/inserts before the full chassis.
7. Validate one 3060 through one x4 remote link before buying/building the entire link set if the link hardware is not returnable.

## Source records retained

Historical engineering records are retained in the project archive:

- `QOVARYX_3xS80_External_GPU_Shelf_Blueprint_v0.9.md`
- `QOVARYX_Shelf_Fit_and_A770_Review_Addendum_v0.9.1.md`

Those are valuable for motherboard lane mapping, external-power discipline, cold-plug sequencing, measurement worksheets and qualification methodology, but their S80/A770 device choices and hybrid aluminum frame are superseded.
