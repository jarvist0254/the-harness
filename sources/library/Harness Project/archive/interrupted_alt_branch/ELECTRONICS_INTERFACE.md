# Electronics Interface — Universal Receiver Sled

## Problem being solved

The exact PCIe receiver/eGPU PCB has not been purchased. Locking a monolithic chassis to guessed mounting holes would be poor engineering.

Therefore each GPU bay receives a **removable universal electronics sled**.

## Sled design target

Suggested maximum sled envelope:
- 170mm Y × 105mm X equivalent working area, orientation may rotate
- skeletal perimeter frame rather than solid plate
- 4 mounting slots per long side

Sled-to-chassis:
- 4 × M4 screws
- M4 heat-set inserts in chassis
- repeatable datum surfaces: one hard corner + one slotted axis so thermal/print tolerance is not overconstrained

PCB-to-sled:
- M3 or M2.5 metal standoffs
- elongated slots 3.6–4.0mm wide for M3 hardware
- slot length 35–50mm
- stainless washer under nut/head
- optional nylon washer against PCB

## Receiver connector support

The PCIe x16 mechanical socket must not be used as a cantilever support for a heavy GPU.

Provide:
- I/O bracket retention at the front bulkhead
- rear/mid card body cradle
- receiver PCB standoffs supporting the connector region
- no force from cable bundles into the socket

## Board-specific adapter

When the exact receiver board arrives:
1. Measure PCB L/W/thickness.
2. Measure every mounting-hole center and diameter.
3. Measure underside component height.
4. Measure PCIe slot height from PCB datum.
5. Measure OCuLink/SlimSAS/MCIO connector position and required bend radius.
6. Create a small board-specific adapter plate or standoff map.
7. Leave the monolithic chassis unchanged unless a true envelope conflict exists.

This is intentional modularity.

## Electrical caution

Do not infer PCIe signal compatibility from connector shape. Host bifurcation card, cable and receiver must be a matched PCIe solution that carries required lanes, reference clock/reset/sideband behavior and local slot power without unsafe backfeed.

Mining x1 USB risers are outside this design.
