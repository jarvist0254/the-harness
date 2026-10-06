# Astra / FreeCAD Handoff — JE Horizon Universal 3-GPU Pod

**Authoritative revision:** 2.0-preCAD  
**CAD target:** FreeCAD parametric master model  
**Rule:** This file follows `MASTER_BLUEPRINT.md`; if any archived/older file disagrees, the master blueprint and `DIMENSION_AUTHORITY_AND_TBDS.md` win.

## Mission

Create a production-minded parametric FreeCAD design for one **universal three-GPU pod**. It must accept three desktop GPUs within the declared envelope, three removable OCuLink receiver trays, two 120 mm intake fans and pressure plenum, separated cable raceways, external-PSU restraint hardpoints, and a standardized pod-to-pod mechanical/control interface.

The first cards are three MSI RTX 3060 Ventus 2X units, but **no permanent chassis feature may depend on that specific GPU**.

Future expansion is another identical 3-GPU pod. Do not add a fourth bay.

## Coordinate system and print orientation

### Operational orientation

Use:

- W = left/right across GPU thicknesses: approximately **254 mm**
- D = front intake toward rear GPU overhang: approximately **200 mm printed core**, cards may extend to 360 mm total card length
- H = vertical: approximately **188 mm printed body**

### Printer orientation

Rotate the monolithic core for the Ender-3 S1 Pro so the printed bounding box is:

- X <= **200 mm**
- Y <= **188 mm**
- Z <= **254 mm**

Nominal printer envelope is 220 × 220 × 270 mm. Leave bed margin for brim/adhesion and dimensional error.

## Frozen three-bay width map

Across operational W = 254 mm:

```text
left structural margin     13
Bay A maximum envelope     68
A/B clear airflow channel  12
Bay B maximum envelope     68
B/C clear airflow channel  12
Bay C maximum envelope     68
right structural margin    13
-----------------------------
TOTAL                     254
```

Bay maximum GPU envelope:

- thickness: 68 mm
- body height: 165 mm target
- card length: 360 mm maximum via deliberate rear overhang
- adjustment target down to approximately 35 mm thickness
- <=1.2 kg without metal tail support
- <=2.2 kg with metal tail support

Do not center thin cards blindly. Adjustable shoes should use unused bay width to improve intake clearance.

## Initial validation card object

MSI RTX 3060 Ventus 2X 12G OC:

- 235 L × 124 H × 42 T mm
- 675 g
- 170 W
- one 8-pin auxiliary connector

Model three of these plus three max-envelope dummy cards. The chassis must pass both configurations.

## Fans and plenum

Use **2 × ARCTIC P12 Max**, side-by-side across the 254 mm operational width.

Verified vendor drawing values:

- frame 120 × 120 × 25 mm
- mounting-hole centers: **105 × 105 mm**
- manufacturer drawing hole diameter: **4.40 mm**

Use M4 machine-screw clearance geometry tuned from a coupon. Do not use fan self-tapping screws into PETG.

Fan wall principles:

- two 120 mm frames consume 240 mm across W
- approximately 7 mm outer border each side before local ribs
- common plenum depth target **25–35 mm**
- do not split airflow directly at blade plane; equalize pressure first
- thin flow-divider vanes only after plenum equalization region
- rear/exhaust field stays substantially open

Maintain at least 12 mm clear AB/BC channel at the 68 mm max-card envelope. Cables may not intrude into that minimum throat.

## Universal GPU retention

Each bay uses:

1. receiver/PCIe slot datum,
2. independent metal I/O-bracket restraint/crossbar,
3. adjustable M4 lateral shoe with 1–2 mm EPDM/neoprene contact pad,
4. padded body support only at a verified safe shroud/backplate region,
5. optional metal tail-support rod/bar for long or heavy cards.

Never rely on:

- GPU shroud screws,
- one cooler shape,
- fan openings,
- heatpipe geometry,
- a fixed power connector location.

Power connector area must be an **open service region** compatible with top-edge/end-edge 8-pin and 12V-2x6 layouts.

## Receiver tray

Preferred receiver is ADT-Link F9Q-BK10.

Until official vendor CAD is imported, do not create fixed PCB standoffs in the monolithic chassis.

Use a removable universal tray:

- three independent receiver zones
- M3 metal standoffs
- longitudinal slots 3.6–4.0 mm wide × 20–30 mm long
- washer/nut access from underside
- >=10 mm structural web around slot ends
- tray tied to chassis using structural hardpoints

Official CAD URL is recorded in `vendor_cad/README.md`.

After importing the vendor model, record actual PCB envelope, hole centers/diameters, underside component height, PCIe slot centerline, OCuLink/power connector keepouts, redriver/heatsink Z, button/LED keepouts, and choose standoff height from measured clearance.

## Fasteners and threaded interfaces

No reusable structural screw cuts threads directly into PETG.

### M4 structural standard

Use through-bolt + flat washer + nyloc/metal nut where accessible for:

- GPU support rails/shoes
- fan wall
- PSU straps
- tail-support hardpoints
- pod docking plate
- main strain-relief anchors

Heat-set M4 inserts are secondary where a through-bolt is geometrically impossible.

### M3 electronics standard

Use machine screws + metal standoffs/nuts for receiver PCBs. Use M3 heat-set inserts for cable covers, sensor brackets, small service panels and similar secondary interfaces.

Insert references:

- M3 RX-M3x5.7 family: nominal ~4.0 mm pilot before coupon tuning
- M4 RX-M4x8.1 family: nominal ~5.6 mm pilot before coupon tuning

Every pilot is tuned with a PETG coupon before final model release.

## Cable architecture

Keep three routing classes separate:

### Signal raceway

- OCuLink/high-speed data
- >=28 × 16 mm clear common section
- 25–40 mm straight/service zone behind each OCuLink connector before first restraint
- >=1.5 mm radiused contact edges
- strain relief clamps jacket, never connector body

### GPU power service corridors

- target >=28 × 20 mm clear per bay
- independent A/B/C cable retention
- removable/open-top near GPU
- preserve latch and bend access for differing connector positions

### Control/PWM/telemetry

- >=14 × 10 mm
- fan PWM, USB/control, sensors, optional pod-control network
- no GPU auxiliary power in this route

Raceway covers use M3 inserts + machine screws. Snap features may locate covers but are not the only retention method.

## Material and mass strategy

Production material: **one continuous 5 kg spool of plain quality PETG**.

Reason: best cost/process-risk balance for this near-full-envelope one-piece print on an open Ender-3 S1 Pro. Do not jump to ASA/PC/PA-CF/GF unless PETG thermal validation fails.

Production geometry target:

- preferred slicer total <=3.0 kg
- hard release ceiling <=4.0 kg including supports/brim
- mid-print spool change forbidden

### Remove material aggressively from

- broad side-wall centers
- cosmetic panels
- plenum fields away from ribs/bosses
- cable covers
- open receiver-tray areas
- floor areas between load rails/crossmembers

Use large radiused windows and ladder/spine construction rather than a solid floor.

### Reinforce locally

- receiver datum rails
- receiver slot/standoff webs
- I/O bracket rail
- adjustable GPU support rails
- tail-support sockets
- PSU strap anchors
- pod-dock hardpoints
- fan screw bosses and fan-wall transitions
- heavy cable strain-relief anchors

Starting wall/rib values:

- general wall: 2.4–3.0 mm
- structural ribs/gussets: 5–7 mm effective section
- major hardpoint section: 7–10 mm
- inside fillets: 3–6 mm radius

Local slicer map:

- shell: 4 perimeters, 12–15% gyroid/cubic
- receiver/card rails: 6 perimeters, 40–60%
- fan bosses: 6 perimeters, 30–40%
- receiver slot webs: 6 perimeters, 50–70%
- PSU/dock anchors: 8 perimeters, 70–100% local
- cable covers: 3 perimeters, 0–10%

Use geometry/perimeters before global infill.

## PSU interface

Reference envelope currently: Corsair RM1000x ATX 3.1, 160 × 150 × 86 mm.

Keep PSU geometry parametric. It remains in its intact metal enclosure and is restrained with metal straps/cradle pieces through reinforced M4 hardpoints plus EPDM/neoprene isolation. Do not suspend PSU mass from printed screw threads or drill arbitrary PSU housing locations.

Preserve:

- fan inlet
- exhaust
- AC inlet/switch
- modular cable face
- cable bend/service volume

## Pod expansion interface

One pod = three GPUs forever.

Reserve:

- flat mating datum
- 4 × M4 structural holes on 80 × 60 mm rectangle
- central 42 × 30 mm removable service blank
- 2 × M3 insert points for future connector/control plate

Pods join structurally through a metal bridge plate. This interface may later carry network/control or an approved active compute fabric. It is **not** a passive PCIe lane splitter.

## FreeCAD modeling requirements

Create a Spreadsheet or Parameter object containing every frozen dimension. Use expressions so bay width, shell/rib thickness, plenum depth, PSU envelope, support positions and service clearances are editable.

Recommended output structure:

- `Core_Chassis`
- `Fan_Wall_Plenum`
- `Receiver_Tray_A/B/C`
- `GPU_Shoe_A/B/C`
- `Tail_Support_Interface_A/B/C`
- `Cable_Covers`
- `PSU_Strap_Interface`
- `Pod_Dock_Interface`
- `Dummy_GPU_Max`
- `Dummy_GPU_3060`
- `Dummy_Fan_P12Max`
- `Dummy_Receiver_F9Q`

Deliver:

1. master `.FCStd`
2. STEP assembly export
3. section view: airflow/plenum
4. section view: signal/power/control raceways
5. exploded view with fasteners/standoffs
6. print orientation view
7. interference report for max-envelope and 3060 population
8. reported model volume and estimated PETG mass
9. unresolved-dimension list

Do not issue a final production STL until `VALIDATION_CHECKLIST.md` and `DIMENSION_AUTHORITY_AND_TBDS.md` gates are closed.
