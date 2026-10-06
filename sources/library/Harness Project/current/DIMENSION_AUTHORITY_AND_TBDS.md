# Dimension Authority, Measurement Gates, and No-Guess Register

**Project:** JE Horizon Universal 3-GPU Pod  
**Revision:** 2.0-preCAD  
**Purpose:** Tell Astra exactly which dimensions are frozen, which are vendor-controlled, and which must be measured before a production STL is released.

## 1. Frozen chassis-level design dimensions

These values are design inputs and may be modeled immediately:

| Item | Frozen value |
|---|---:|
| GPU bays | 3 exactly |
| One-piece print bounding box | <= 200 × 188 × 254 mm |
| Operational printed-body envelope | approx. 254 W × 200 D × 188 H mm |
| Bay max thickness envelope | 68 mm each |
| Bay minimum adjustment target | 35 mm |
| Card height target | <=165 mm |
| Card length target | <=360 mm with deliberate rear overhang |
| Inter-card clear airflow channel | >=12 mm at max 68 mm card thickness |
| Common intake plenum | 25–35 mm |
| Fan count | 2 × 120 × 120 × 25 mm |
| Signal raceway clear section | >=28 × 16 mm |
| GPU power service corridor | >=28 × 20 mm per bay |
| Control/PWM corridor | >=14 × 10 mm |
| Pod docking bolt pattern | 4 × M4 on 80 × 60 mm rectangle |
| Pod docking service blank | 42 × 30 mm |
| General shell thickness | 2.4–3.0 mm |
| Structural rib effective section | 5–7 mm |
| Major hardpoint effective section | 7–10 mm |
| Internal fillet target | 3–6 mm radius |

## 2. Fan geometry — vendor-controlled and verified

Selected fan family: ARCTIC P12 Max, 120 × 120 × 25 mm.

ARCTIC's published P12 Max 2D drawing gives:

- frame: 120 × 120 mm
- thickness: 25 mm
- mounting-hole center spacing: **105 × 105 mm**
- mounting-hole diameter: **4.40 mm**

CAD rule:

- model fan hardpoints at 105 × 105 mm centers,
- chassis clearance holes should be modeled for M4 machine screws with appropriate printer tolerance rather than copied as exactly 4.40 mm blindly,
- final printed M4 clearance is tuned with a coupon,
- use through-bolt + washer + nyloc nut, not fan self-tappers into PETG.

## 3. ADT-Link F9Q-BK10 receiver geometry — hard release gate

The F9Q-BK10 is the preferred receiver, but its exact PCB hole pattern must come from its official 3D CAD or a physical board.

Official product page:
https://www.adt.link/product/F9Q.html

Official vendor CAD archive advertised by ADT-Link:
https://www.adt.link/download/ADT_F9Q_BK10_3D.zip

### Pre-CAD receiver mounting method

Astra may model only a **universal slotted tray** until vendor CAD is imported:

- slot width: 3.6–4.0 mm
- slot length: 20–30 mm
- M3 brass/stainless standoffs
- M3 machine screws
- metal washers/nuts under tray
- minimum 10 mm structural web around slot ends
- underside access for nut/washer installation

Do **not** freeze fixed receiver standoff coordinates from photographs.
Do **not** drill/modify receiver PCB holes to match the chassis.

### After vendor CAD import

Astra must record in a Blender text block and this project before final STL:

- PCB overall X/Y dimensions
- PCB thickness
- all mounting-hole center coordinates from one datum
- hole diameters
- underside component maximum Z
- x16 slot centerline and datum
- OCuLink connector centerline and protrusion
- receiver power connector centerline/protrusion
- switch/button/LED keepouts
- redriver/heatsink maximum Z

Then choose the M3 standoff height from actual underside clearance. The tray may remain slotted for universality even after exact dimensions are known.

## 4. GPU mounting is intentionally card-agnostic

The first population (MSI RTX 3060 Ventus 2X) is a validation object only.

No chassis feature may require:

- a particular cooler/shroud screw,
- one specific GPU power-connector location,
- a fixed card length,
- a fixed fan count,
- one manufacturer's backplate shape.

Use these universal datums instead:

1. receiver PCIe slot/edge-connector datum,
2. standard I/O bracket plane,
3. adjustable lateral shoe,
4. padded safe-body support,
5. optional metal tail support for long/heavy cards.

Power cables leave through an open service region so top-edge, end-edge, 8-pin and 12V-2x6 layouts can all be accommodated.

## 5. Fastener authority

### Structural joints

Default: **M4 machine screw + flat washer + metal nut/nyloc** through the print.

No reusable structural joint should rely on a screw cutting threads directly into PETG.

### PCB/electronics

Default: **M3 machine screw + metal standoff + metal nut/washer**.

### Heat-set inserts

Secondary/service use only:

- M3 reference insert: ruthex RX-M3x5.7; nominal CAD pilot ~4.0 mm before coupon tuning
- M4 reference insert: ruthex RX-M4x8.1; nominal CAD pilot ~5.6 mm before coupon tuning

Every insert pilot diameter is finalized using an actual PETG coupon from the production printer/nozzle/profile.

## 6. PSU geometry — parameter, not fixed chassis datum

Reference PSU: Corsair RM1000x ATX 3.1, 160 × 150 × 86 mm.

Astra must keep PSU W/D/H and modular-cable projection as parameters. The pod uses metal straps through reinforced M4 hardpoints; no arbitrary screws enter the PSU enclosure.

Before STL release, record:

- exact PSU body dimensions,
- fan inlet location,
- exhaust clearance,
- AC inlet/switch clearance,
- modular connector keepout,
- minimum bend region for largest cable bundle.

## 7. One-spool release gate

One continuous spool is mandatory. Mid-print spool change is not allowed.

Production release requires a slicer report showing:

- model filament mass,
- support mass,
- brim/adhesion mass,
- total mass <=4.0 kg on a fresh 5 kg spool,
- preferred total <=3.0 kg,
- no hidden purge tower or support strategy that pushes above reserve.

If the model is too heavy, remove material from low-load skins/panels first. Never thin hardpoints, receiver rails, GPU support rails, PSU strap bosses, fan boss transitions, pod-dock bosses, or cable strain-relief anchors merely to hit the spool target.

## 8. Astra final pre-STL checklist

Astra must explicitly report PASS/FAIL for:

- bounding box
- fan hole geometry
- F9Q CAD imported/verified
- receiver hole/connector keepouts
- max GPU envelope collision check
- RTX 3060 validation collision check
- GPU-A/B/C independent removal path
- power cable service region
- OCuLink 25–40 mm straight service length before first clamp
- 12 mm inter-card airflow channels remain unobstructed
- PSU airflow and modular-cable clearance
- M4 through-bolt tool/nut access
- M3 standoff/nut access
- expansion plate hardpoints
- slicer total mass/spool reserve
- support volume
- print bed/brim fit

Any FAIL or unknown keeps the design at preCAD/prototype status.
