# PodLink — Future Multi-Harness Expansion Standard

## Principle

Expansion means adding another complete three-GPU pod.

A pod is not stretched to four, five or six cards.

## What PodLink is

PodLink is a **mechanical + low-voltage control + software identity standard** between harnesses. It is not a passive PCIe daisy-chain.

## Mechanical coupling

Reserve four standardized M4 coupling points on each pod side:
- two upper
- two lower
- symmetric left/right

Add two non-threaded alignment sockets per side for 6mm dowel pins or printed/metal alignment keys.

The second pod may sit adjacent or stack only after furniture/load/airflow validation.

Coupling fasteners:
- M4 machine screws into M4 heat-set inserts or through-bolts
- no self-tapping screws

## Electrical independence

Each pod gets:
- its own ATX PSU
- its own fused/protected manufacturer AC input
- its own fan/control supply
- its own PCIe/data uplink(s)

Never daisy-chain high-current 12V GPU power from Pod 1 into Pod 2.

## Low-voltage control link

Reserve a small rear service panel for future:
- USB-C service/control connection, or
- Ethernet/USB controller connection, or
- isolated low-voltage telemetry bus

Do not commit a pinout yet. The panel is a replaceable insert so the control electronics can evolve.

## J-Link software identity

Each pod should eventually report:
- pod_id
- installed GPU IDs
- temperatures
- fan RPM/duty
- PSU/power telemetry if available
- receiver/link state
- fault state

J-Link sees multiple pods as resource groups and schedules workloads accordingly.

## PCIe expansion reality

The first host has finite PCIe lanes. The existing x16 root port can expose four x4 branches. Pod 1 consumes three of them.

A second full three-GPU pod therefore requires a new deliberate host-link architecture, such as:
- qualified active PCIe switch fabric
- other CPU/root-complex lanes on a future platform
- another host participating in J-Link over Ethernet
- other validated high-speed expansion

Do not claim that mechanically connecting pods creates additional PCIe lanes.
