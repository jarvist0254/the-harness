# PodLink Expansion Standard

## Goal

When more than three external GPUs are desired, build a second identical three-GPU pod. Do not stretch the first chassis to four/five/six bays.

PodLink standardizes how pods sit together, cable together and identify themselves. It is **not** a passive PCIe daisy chain.

## Mechanical interface

Provide matching docking hardpoints on both sides of every pod.

Revision 1.1 reference interface per side:

- 2 × 6 mm alignment-dowel bores / metal-bushed seats
- 4 × M5 through-bolt channels
- flat datum lands for a removable metal bridge plate
- cable-bridge mounting points
- no plastic snap latch as primary structure

Astra may optimize the exact bolt rectangle, but once chosen it becomes a controlled dimension used by every future pod.

Recommended starting bolt rectangle: approximately 120 mm vertical × 100 mm fore/aft, adjusted to avoid internal PSU/receiver/fan structures.

## Electrical boundary

Each pod has:

- its own PSU
- its own three receiver boards
- its own fans/fan control
- its own pod ID / telemetry
- an independent qualified PCIe path to a host or PCIe switch

PodLink carries no AC mains and no shared high-current GPU rail.

## Data expansion options

The software architecture must allow more than one physical topology:

1. unused CPU-root lanes / another bifurcation-capable host slot
2. a qualified active PCIe switch/backplane
3. a second host computer joined to J-Link over high-speed Ethernet
4. future fabric hardware

Do not force Astra to solve data-lane expansion mechanically. The printed PodLink only ensures physical repeatability and cable routing.

## J-Link identity

Every pod should have a visible/embossed ID area and optional controller-mount footprint.

Example:

- P1:A, P1:B, P1:C
- P2:A, P2:B, P2:C

J-Link should make scheduling decisions from topology, not card order alone.

## Cable bridge

When pods are side by side, a removable upper/rear bridge can carry:

- network/telemetry/control
- labeled OCuLink or other data cables that independently return to host/switch

The bridge is not allowed to turn into an inaccessible cable bundle. Use open channels with clip-on lids and bend-radius control.

