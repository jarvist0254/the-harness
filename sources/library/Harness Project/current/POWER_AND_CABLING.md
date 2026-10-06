# Cable Management and Power Architecture

## Design philosophy

Power and high-speed data are routed deliberately and separately. The pod should look like a purpose-built accelerator appliance, not an open mining rig.

## Three cable zones

### Zone D — PCIe/data
Route the three high-speed transport cables in one protected corridor.

Requirements:
- largest bend radius allowed by the cable vendor
- no sharp printed clips pressing into cable jacket
- no cable weight carried by the board connector
- 25–40mm service loop near each receiver
- individual A/B/C labels at both ends
- data corridor separated from GPU auxiliary-power bundle where practical

### Zone P — high-current GPU/receiver power
Route GPU power in a separate rear/top raceway.

Requirements:
- one clearly identified GPU feed per installed card when PSU cable inventory permits
- no SATA-to-PCIe adapters
- no unknown modular PSU cables
- no conductor splices buried in printed channels
- power connector latch must remain accessible
- 35–50mm bend/service volume at GPU connector

### Zone C — control/fans/sensors
Low-current fan, tach, thermistor and optional controller wiring gets its own narrow raceway.

Use removable covers fixed with M3 inserts.

## Raceway geometry

Recommended starting internal cross-sections:
- PCIe/data trunk: 28 × 18mm minimum, enlarge for actual selected cable bundle
- GPU power trunk: 38 × 24mm minimum
- control trunk: 18 × 12mm

Use large-radius 45° transitions, not hard 90° elbows.

Cable tie points:
- integral 4–5mm-wide slots sized for reusable hook-and-loop ties
- spacing 50–80mm
- no nylon zip ties directly crushing high-speed cable

## Strain relief

Every cable leaving the pod needs a chassis anchor before its electrical connector.

The anchor takes pull load; the connector does not.

Use:
- P-clamp with M3 screw into insert
- rubber-lined clamp
- hook-and-loop through printed slot

## External PSU

Reference class: quality 1000W fully modular ATX PSU.

Current Corsair RM1000e reference:
- 1000W continuous
- ATX 3.1
- 140 × 150 × 86mm
- multiple native PCIe power leads
- fully modular

For three RTX 3060 170W cards:
- GPU board-power arithmetic: 510W
- plus receiver/slot power conversion and fans/control
- 1000W offers comfortable headroom

Future higher-power cards require a new power calculation. Do not assume the same 1000W PSU supports any arbitrary three GPUs.

## Power domains

The pod PSU powers the three pod GPUs and their locally powered receiver hardware.

The existing host PSU powers the host and the RTX 5070 Ti unless that architecture is deliberately revised.

Do not parallel 12V outputs between independent ATX PSUs.

## Power sequence during qualification

Power on:
1. Host fully shut down.
2. Inspect all data/power connections.
3. Start external pod PSU and fans/receivers.
4. Verify expected pod power state.
5. Start host.
6. Enumerate devices.
7. Run J-Link health check.
8. Start workloads.

Power off:
1. Drain/cancel workloads.
2. Stop J-Link workers.
3. Shut down host fully.
4. Switch off external pod PSU.
5. Disconnect AC before changing GPU/data/power cabling.

No hot-plug assumption is made.
