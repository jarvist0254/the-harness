# Power and PCIe Blueprint

## PCIe host

Reference host: MSI PRO X870-P WIFI + Ryzen 7 7700.

MSI documents:

- PCI_E1: CPU x16 and supports x4+x4+x4+x4 bifurcation with Ryzen 7000/9000
- PCI_E4: chipset PCIe 4.0 x4
- M2_3 shares PCI_E4 resources; preserve M2_3 empty when PCI_E4 x4 is needed

Reference Pod 1 host adapter: RIITOP PCIe 4.0 x16 to 4 × OCuLink SFF-8612, which requires motherboard x4+x4+x4+x4 bifurcation. Pod 1 uses three ports.

## Receiver power rule

Reference HOOCCC receiver permits **one** power source among:

- 24-pin ATX
- 6-pin PCIe
- 12 V DC 10 A

Do not connect multiple receiver power inputs simultaneously.

For the clean first build, 6-pin receiver feed is the mechanical reference because it avoids three 24-pin bundles. Final release depends on the exact PSU cable map.

## External pod PSU

Target: quality **1000 W ATX** PSU with adequate native PCIe cable inventory, protections and modular cabling.

Reference/cable-friendly older candidate: EVGA SuperNOVA 1000 GT (220-GT-1000-X1). Its manual documents five VGA modular positions and a supplied cable set totaling two single-connector plus three dual-connector PCIe cables. Availability/pricing is inconsistent in 2026, so this is a cable-map reference rather than a mandatory purchase if a better current model is selected.

The PSU is a swappable module. Astra must keep its saddle parametric.

## First-population power budget

Three RTX 3060 Ventus 2X cards:

- 3 × 170 W = **510 W** GPU board-power maximum by manufacturer rating
- receiver boards/fans/control add load on top
- a quality 1000 W PSU leaves large operating margin

Do not add another 75 W per card to the 170 W board rating; slot power is part of board power.

## Universal pod electrical release envelope

Mechanical fit does not imply electrical permission.

Baseline design target:

- preferred sustained three-GPU aggregate: **≤750 W GPU board power** (e.g. 3 × 250 W)
- leave margin for receiver electronics, fans, startup behavior and PSU efficiency/thermal conditions
- if future cards push materially beyond this, requalify PSU and cables rather than assuming the 1000 W label is sufficient

A three-card combination may be mechanically valid but electrically rejected.

## Cable topology for current 3060s

Each bay needs:

- locally powered receiver slot
- GPU auxiliary 8-pin feed

A neat per-bay cable concept is one dedicated PSU VGA cable/run servicing that bay only **if the selected PSU manufacturer permits the cable's combined load and connector arrangement**. Do not assume every dual-headed PCIe cable may safely feed both the receiver and GPU.

If vendor approval/spec is unclear, use separate approved PSU cable runs. Never use SATA-to-PCIe GPU adapters.

## Grounding / dual chassis

Host and pod share PCIe signal grounds through the approved cable system. Do not cut grounds to “isolate” systems.

Do not parallel output rails from separate PSUs.

If the 5070 Ti uses the host PSU while physically outside the case, keep its slot/auxiliary-power architecture consistent with the approved extension hardware; do not casually split one GPU across unrelated PSU domains.

## Startup sequence — qualification phase

1. host fully shut down
2. inspect receiver/data/GPU power connections
3. energize pod PSU / receiver boards / fans
4. verify receiver status LEDs where available
5. start host
6. confirm all three devices enumerate at expected lane width/gen
7. launch J-Link only after health checks

Shutdown:

1. drain/cancel J-Link jobs
2. shut down host fully
3. turn off pod PSU
4. disconnect AC before hardware changes

No hot-plugging in the prototype release.

## Pod power interface

Expansion pods each receive their own PSU. PodLink mechanical connectors **do not carry GPU DC power or AC mains** between pods in revision 1.1.

This makes pods electrically modular and prevents one giant shared custom power bus from becoming a failure point.

