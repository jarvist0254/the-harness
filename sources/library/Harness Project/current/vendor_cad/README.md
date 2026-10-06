# Vendor CAD and Drawing Authority

Do not reconstruct critical hardware dimensions from photographs. Use the following vendor-controlled files/pages.

## ADT-Link F9Q-BK10 receiver

Official product page:
https://www.adt.link/product/F9Q.html

Official 3D CAD archive advertised by ADT-Link:
https://www.adt.link/download/ADT_F9Q_BK10_3D.zip

Verified product-level facts from the manufacturer page:

- OCuLink / PCIe x16 mechanical receiver
- PCIe 4.0 x4, claimed 64 Gbit/s signaling
- 50 cm cable in F9Q-BK10 package description
- redriver-equipped
- OCuLink is not hot-swappable

**Required Astra action:** import vendor CAD before freezing PCB hole coordinates, slot centerline, connector protrusion, button/LED keepouts, and standoff height.

If the archive cannot be imported directly, purchase/measure one physical receiver and record the dimension set in `DIMENSION_AUTHORITY_AND_TBDS.md`. Do not infer board-hole coordinates from web photos.

## ARCTIC P12 Max fan

Official support/documentation:
https://support.arctic.de/en/p12-max/docs

Official P12 Max 2D drawing reports:

- 120 × 120 mm frame
- 25 mm thickness
- 105 × 105 mm mounting-hole centers
- 4.40 mm mounting-hole diameter

Chassis uses M4 machine screws with tuned printed clearance, washers, and nyloc nuts. Do not use fan self-tapping screws as structural threads in PETG.

## MSI RTX 3060 Ventus 2X validation card

This card is the first-population validation object, not the universal chassis datum.

Manufacturer envelope already recorded in the project:

- 235 mm length
- 124 mm height
- 42 mm thickness
- 675 g
- 170 W
- 1 × 8-pin auxiliary power

Astra must also validate the 68 × 165 × 360 mm generic maximum card envelope.
