# Material and Print Plan — One-Spool Requirement

**Revision:** 2.0-preCAD  
**Primary recommendation:** quality **plain PETG, one continuous 5 kg spool**

## 1. Material decision

For this specific printer and geometry, plain engineering-grade PETG is the best cost/risk balance.

Why PETG wins here:

- Ender-3 S1 Pro can print it without a heated enclosure.
- Very large one-piece prints are far less warp-prone than ABS/ASA/PC/nylon on an open machine.
- Better impact tolerance and layer adhesion for a chassis than ordinary PLA.
- Cheap enough to use a true 5 kg continuous spool.
- Does not require an abrasive-resistant nozzle the way CF/GF-filled materials do.
- Heat-set inserts work well in PETG.

Do not choose PA6-CF/PC/ASA merely because their datasheets look stronger. On an open Ender-3 S1 Pro, a 200 × 188 × 254 mm one-piece chassis raises warping, moisture, enclosure and print-failure risk. A failed 30+ hour engineering-filament print is not “stronger.”

## 2. Recommended spool

### Preferred

ZYLtech 5KG High Speed / High Flow PETG, 1.75 mm — currently listed around $79.95.

Manufacturer listing:
https://www.zyltech.com/5kg-texas-size-spool-high-speed-high-flow-petg-3d-printer-filament-1-75mm-11-lbs-made-in-usa/

### Alternate

ZYLtech 5KG regular PETG — currently $76.95 and listed in stock.

https://www.zyltech.com/5kg-texas-size-spool-petg-3d-printer-filament-1-75-mm-11-lbs/

California Filament 5kg regular PETG — current page lists $74.99, with conflicting “sold out/in stock” page state; verify checkout before relying on it.

https://californiafilament.com/products/black-petg-filament-1-75mm-5kg

## 3. One-spool rule

The production print must begin with a fresh single continuous 5 kg spool.

Do not design toward consuming the whole spool. Reserve material for:

- purge/prime
- brim
- slicer support material if unavoidable
- extrusion calibration
- runout uncertainty
- spool manufacturer weight tolerance

### Mass release criterion

Production print target: **<=3.0 kg estimated filament**.  
Hard release ceiling: **<=4.0 kg slicer estimate including support/brim** on a 5 kg spool.

This leaves at least ~20% nominal reserve at the hard ceiling. The preferred engineering target is lower because print time, thermal mass and failure cost also matter.

Do not “use the spare plastic” just because 5 kg is available.

## 4. External spool handling

A 5 kg spool should not hang from the Ender-3 S1 Pro gantry.

Use:

- independent floor/table roller or bearing spool holder rated for >=5 kg
- low-friction feed path into the Sprite direct drive
- spool axis aligned so filament does not side-load the extruder
- no tight PTFE bend
- dry spool before the production print, then feed from a dry box if ambient humidity is high

The spool holder is outside the pod CAD.

## 5. Nozzle and layer strategy

Preferred production nozzle: **0.6 mm**.

Rationale: this is a very large structural print. A 0.6 mm nozzle reduces line count and print time while allowing strong thick walls. Plain PETG does not require a hardened nozzle, though a quality wear-resistant nozzle is acceptable.

Starting slicer profile to tune with coupons:

- nozzle: 0.6 mm
- layer height: 0.28 mm nominal
- first layer: 0.24–0.28 mm after bed tune
- extrusion width: ~0.66–0.72 mm depending slicer/profile
- speed: conservative; prioritize layer bonding over headline speed
- fan: moderate PETG cooling; bridges may need more
- brim: 5 mm starting point
- supports: design to minimize/avoid them

Use the filament maker’s temperature range and tune a tower/coupon first. Do not freeze nozzle/bed temperature in CAD documentation.

## 6. Where material can be sacrificed

### Very low material priority

These regions should be shells/ribs, not solid plastic:

- broad side panels
- broad top panel
- plenum panel fields between structural ribs
- cable raceway lids
- cosmetic bezels
- receiver-tray open areas
- pod expansion blanking plate

Use 2.0–2.4 mm skins and large radiused windows where stiffness permits.

### Low/medium priority

- fan shroud away from screw bosses: 2.4 mm wall, 10–15% infill
- cable raceway body: 2.0–2.4 mm, 0–10% infill if geometry is self-supporting
- removable covers: 1.8–2.2 mm, 0–10% infill

### Never starve these zones

- GPU receiver datum rail
- receiver standoff/slot webs
- GPU lateral clamp rails
- I/O bracket restraint
- far-end tail-support sockets
- PSU strap hardpoints
- pod docking hardpoints
- lift/handle points
- fan screw bosses
- cable strain-relief anchors

Use local ribs and perimeters before blindly raising global infill.

## 7. Perimeter and local infill map

| Zone | Perimeters | Local infill | Notes |
|---|---:|---:|---|
| General shell | 4 | 12–15% gyroid/cubic | large windows preferred |
| Plenum panels | 3–4 | 10–15% | ribs at fan transitions |
| Fan boss region | 6 | 30–40% | 15 mm radius modifier around each boss |
| Receiver datum rail | 6 | 40–60% | continuous ribs to sidewalls |
| Receiver standoff slots | 6 | 50–70% | metal washer both sides where possible |
| GPU support/clamp rail | 6 | 40–60% | rounded rib network |
| PSU strap anchors | 8 | 70–100% | through-bolted; broad load-spreader geometry |
| Pod docking hardpoints | 8 | 70–100% | through-bolt/captive metal nut |
| Cable anchors | 5–6 | 30–50% | strain load only, not GPU support |
| Cable cover | 3 | 0–10% | heat-set inserts only at attachment points |

For slicers with modifier meshes, Astra should export or document the modifier regions so the user can reproduce the local-infill map.

## 8. Geometry is stronger than infill

Prefer:

- curved ribs
- box sections
- gussets
- double-shear brackets
- through-bolts with washers
- metal standoffs
- 3–6 mm internal fillets

Avoid:

- 100% infill everywhere
- long flat 4 mm plates with no ribs
- sharp inside corners
- cantilevered insert bosses with no gusset
- self-tapped structural screws

## 9. Thermal limits for prototype validation

Treat printed hardpoint temperatures conservatively during qualification. If structural PETG zones spend sustained time around 50°C or become visibly compliant, revise airflow/support location/material before production use. This is a project stop rule, not a claimed universal PETG glass-transition specification.
