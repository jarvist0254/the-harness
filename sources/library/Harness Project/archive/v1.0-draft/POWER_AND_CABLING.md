# Power and Cabling Plan

## Separate PSU domains

### Host PSU domain

The existing host PSU continues to power:

- motherboard
- Ryzen CPU
- RAM/storage
- RTX 5070 Ti slot power through its PCIe path
- RTX 5070 Ti auxiliary power

Even though the 5070 Ti is physically relocated to the lower shelf, do not move only part of its power to the external PSU.

### External harness PSU domain

The external 1000 W PSU powers:

- all locally powered remote PCIe receiver slots for the 3060 bank
- RTX 3060 auxiliary power cables
- two 120 mm plenum fans
- low-voltage control/telemetry hardware if used

## GPU board-power budget

RTX 3060 Ventus 2X OC manufacturer board power: 170 W.

- 3 × 3060 = 510 W
- 4 × 3060 = 680 W

A quality 1000 W unit leaves substantial headroom for four cards plus powered receivers/fans. Keep one native GPU cable run per 3060 where the exact PSU cable inventory permits it. Do not mix modular cables between PSU models.

## Receiver-slot power

The external 3060 receiver/riser hardware must be designed for local slot power. Required properties:

- PCIe x16 mechanical slot
- only x4 data lanes are required from each CPU bifurcation branch
- proper local 12 V/3.3 V slot-power implementation
- documented clock/reset/presence behavior
- no backfeeding of host power
- proper grounding between linked chassis

Avoid mining-style USB x1 risers for this project.

## 5070 Ti link

The 5070 Ti lower-shelf extension should preserve the host PSU power domain. Use a quality PCIe extension/receiver arrangement appropriate for PCI_E4 x4 operation. Exact card model dimensions and power connector routing are still to be measured.

## Start/stop behavior

Until the full topology is proven:

**Power on**
1. Host fully off.
2. Inspect all high-speed and power connections.
3. Turn on external 3060 harness PSU and fans.
4. Verify receiver/fan power.
5. Start host.
6. Enumerate GPUs and run health check before starting J-Link workers.

**Power off**
1. Stop new J-Link work.
2. Drain/cancel jobs and save state.
3. Shut down host fully.
4. Turn off external harness PSU.
5. Disconnect AC before changing cards/cables.

No hot-plugging during prototype qualification.
