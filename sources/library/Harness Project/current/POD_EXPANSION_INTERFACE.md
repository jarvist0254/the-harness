# Pod Expansion Interface

## Principle

One pod = three GPU bays. Expansion means adding another pod, not enlarging the first pod.

## Mechanical dock standard

Reserve on each pod:

- flat mating datum panel
- four M4 structural holes on 80 × 60 mm rectangle
- through-bolt/captive metal nut capability
- central 42 × 30 mm removable blank for future connector panel
- two M3 heat-set insert sites for small connector/control plate

Use a metal bridge plate between pods. The bridge plate handles alignment and shear; do not depend on printed snap tabs for inter-pod structure.

## Electrical/data philosophy

The dock may later carry:

- Ethernet
- USB/control
- fan/telemetry interconnect
- synchronization/control lines
- an approved active PCIe switch/bridge interface

It must **not** be modeled as a passive PCIe splitter.

A second three-GPU pod requires one of:

1. three additional host PCIe x4 links,
2. a qualified active PCIe switch/fabric,
3. a second compute host joined to J-Link over a high-speed network,
4. another architecture deliberately validated later.

J-Link should treat each pod as a topology object (`pod_id`, `bay_id`, PCI path, measured bandwidth), allowing multiple pods without assuming one physical bus topology.

