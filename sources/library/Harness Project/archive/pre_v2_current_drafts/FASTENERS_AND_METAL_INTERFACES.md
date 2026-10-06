# Fasteners and Metal Interfaces

## Non-negotiable rule

**No serviceable screw cuts threads directly into printed PA6-GF.**

There are three approved joint classes:

1. through-bolt + metal washer + metal locknut
2. machine screw into a metal heat-set insert installed after printing/annealing
3. machine screw into a separate metal carrier / threaded rail / captive metal nut

## Insert family

Reference insert family: CNC Kitchen / equivalent standard double-knurled inserts.

### M3 standard

- thread: M3
- nominal insert length: 5.7 mm
- reference outer diameter: ~4.6 mm
- reference installation hole for this exact insert family: 4.0 mm
- blind-hole depth: insert length + at least ~1 mm; validate with supplier drawing and printed coupon

Use for:

- cable-channel lids
- fan-controller bracket
- removable sensor brackets
- lightweight service covers
- receiver-deck secondary locating hardware where loads are low

### M5 standard

- thread: M5
- nominal insert length: 9.5 mm
- reference outer diameter: ~7.1 mm
- reference installation hole for this exact insert family: 6.4 mm

Use only where a heat-set interface is appropriate. **PodLink and other major structural joints should use through-bolts/captive nuts instead of relying solely on insert pull-out strength.**

### Insert-boss modeling

Do not use the supplier's minimum wall as the chassis design target. Provide robust local bosses:

- M3 insert boss OD: start 10–12 mm minimum, larger where space allows
- M5 insert boss OD: start 15–17 mm minimum
- add a radial gusset from every structural boss into a wall/rib
- local slicer modifier: 100% infill around insert zone or enough walls that the boss is effectively solid
- no boss on a thin unsupported membrane

Print an insert-hole ladder coupon in the exact dried PA6-GF, nozzle and profile before the chassis. Printed holes may shrink from CAD.

## Fans — M4 through-bolts

Reference 92 mm fans are 25 mm thick.

Use per fan:

- 4 × M4 machine screws, start at **M4 × 35 mm** and verify actual wall + washer stack
- 8 × M4 flat washers total per fan pair side as required
- 4 × M4 nyloc nuts per fan
- thin EPDM/silicone vibration washers/pads between fan and chassis

For two fans:

- 8 M4 bolts + 8 locknuts minimum
- buy 12 of each to retain spares

Astra must provide through-holes, not printed threads.

## GPU bracket rail — #6-32 UNC

Standard GPU/PCI chassis retention uses #6-32 UNC.

Use:

- 2 positions per bay if bracket allows
- up to 6 installed #6-32 screws for three GPUs
- buy at least 12
- nominal length: **1/4 in (6.35 mm)** flanged/pan head is the starting PC-chassis size; verify engagement in selected metal rail/nut

Threads live in:

- tapped aluminum/steel rail, or
- #6-32 PEM/captive nuts / rivnuts / nut strip

Never in printed plastic.

## Receiver PCB standoffs

Published HOOCCC PCB facts:

- board 138 × 46 mm
- mounting spacing reported as 95 mm / 103 mm
- complete XY hole coordinates and hole diameter are **not published in the source material we have**

Therefore:

- do not drill the final deck from a guessed drawing
- Astra models a removable aluminum receiver carrier with longitudinal/cross slots
- once boards arrive, measure hole diameter and complete coordinates with calipers
- if holes accept M3, use M3 machine screws + 6–10 mm metal standoffs + washers
- if not, revise carrier fastener; do not force M3 through the PCB

The chassis never needs reprinting for this change.

## Receiver deck to chassis

Preferred: **6 × M5 through-bolts** distributed around deck perimeter, with large washers and nyloc nuts or captive metal nut bars.

Starting hardware:

- M5 × 16 or M5 × 20 socket/button head, depending final stack
- large OD flat washers
- nyloc nuts

No printed threads.

## PSU retention

Use the exact PSU's OEM-compatible rear mounting pattern and correct screw length on a **metal retention plate**.

Chassis-to-plate joint:

- 4 × M5 through-bolts / captive nuts
- vibration pad under PSU contact rails

Do not send a long M4/M5 screw into the PSU enclosure because it happens to fit a printed bracket.

## PodLink structural joint

Each PodLink face provides:

- 2 × 6 mm steel alignment dowels
- 4 × M5 through-bolt passages
- steel washers
- M5 nyloc nuts or barrel/cross-dowels captured in a replaceable metal bridge plate

Do not use plastic snap tabs as the primary pod-to-pod structural connection.

## Recommended hardware inventory for one pod

Buy enough for one pod plus mistakes/spares:

- M3 standard heat-set inserts: 100-pack
- M5 standard heat-set inserts: 50-pack (many remain spare)
- M3 stainless machine screw assortment, 6/8/10/12/16/20 mm: 1 kit
- M4 × 35 mm stainless socket/button screws: 12
- M4 flat washers: 24
- M4 nyloc nuts: 12
- M5 stainless screw assortment including 12/16/20/25/30 mm: 1 kit
- M5 flat/fender washers: 24+
- M5 nyloc nuts: 20+
- #6-32 × 1/4 in PC/GPU screws: 12+
- 6 mm × ~30 mm steel dowel pins: 4 (2 used, 2 spare)
- M3 metal standoffs assortment: 12–20, final height selected after receiver/deck measurement

