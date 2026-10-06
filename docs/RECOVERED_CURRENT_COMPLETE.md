# Complete recovered current project documents

Verbatim text aggregation of the downloaded current files. Original contradictions are preserved. Read docs/00_STATUS_AND_PRECEDENCE.md before implementation.


---

## Source: AIRFLOW_AND_CABLE_CHANNELS.md

# Airflow, Plenum and Cable Channel Specification

## 1. Cooling objective

Feed each GPU with room-temperature intake air without forcing one GPU to ingest another GPU’s exhaust. The chassis assists the card coolers; it does not replace them.

## 2. Fan wall

Target fans: 2 × ARCTIC P12 Max, 120 × 120 × 25 mm, side-by-side.

Published fan characteristics:

- 400–3300 rpm PWM
- 81.04 CFM maximum airflow
- 4.35 mm H2O static pressure
- 12 V
- 0.29 A
- 4-pin PWM

Astra should use the manufacturer’s 120 mm mounting-hole drawing / P12 Max 2D drawing as the CAD authority.

## 3. Intake plenum

Provide a **25–35 mm deep common pressure-equalization plenum** behind the two fans before hard flow dividers begin.

Design details:

- rounded fan-to-plenum transitions
- no square dead corners if avoidable
- 3–5 mm radii at divider roots
- removable fan guard outside
- 2.4–3 mm walls in low-load plenum areas
- structural ribs around fan bosses rather than thick solid panels

## 4. GPU air channels

At the declared max card thickness of 68 mm:

- AB clear gap: >=12 mm
- BC clear gap: >=12 mm
- outer card faces should retain additional intake space to chassis wall wherever geometry allows

For the initial 42 mm 3060 cards, use adjustable shoes to bias the cards so the fan intake faces see **roughly 20–25 mm or more** of clear local intake space instead of simply centering all cards.

Do not let:

- OCuLink cables
- 8-pin PCIe cables
- 12V-2x6 cables
- cable combs
- receiver switches
- sensor wires

consume the 12 mm max-envelope minimum channel.

## 5. Cable zones

### Zone S — high-speed signal

Purpose: OCuLink cables from host breakout to three receivers.

Starting internal clear section: **28 × 16 mm common raceway minimum**, preferably divided or provided with individual clips.

Rules:

- maintain cable manufacturer bend radius
- no hard 90° kink at SFF-8611/8612 connector
- provide 25–40 mm straight/service zone immediately behind each connector before first restraint
- strain relief clamps the cable jacket, never the connector body
- route away from GPU fan blades and sharp printed edges
- route separately from high-current GPU cable bundles when practical

### Zone P — GPU power

Purpose: one or more native PSU GPU leads per bay.

Starting allocation per bay: **28 × 20 mm** clear routing corridor, with an open-top or removable-cover section near the GPU so different connector positions are accommodated.

Rules:

- no forced bend directly at 8-pin/12V-2x6 connector
- preserve connector latch access
- provide a broad top/rear “power service zone” instead of a fixed connector hole
- do not bind three GPU leads into one immovable bundle before they reach the cards
- each bay receives independent labeled strain relief: PWR-A, PWR-B, PWR-C

### Zone C — control/fans/telemetry

Starting clear section: **14 × 10 mm**.

Carries:

- two fan PWM leads
- optional fan hub lead
- USB/control cable
- temperature probes
- optional Ethernet/control link for future pod controller

Do not put GPU auxiliary power into this channel.

## 6. Raceways and covers

Use snap geometry only as a locating feature; use M3 heat-set inserts + machine screws for serviceable covers.

Preferred cover spacing:

- M3 fastener every 80–120 mm on long covers
- no more fasteners than needed to prevent buzz/rattle
- slots/windows every 30–50 mm where safe to cut material

Cable edges need >=1.5 mm radius or a grommet. No raw sharp slot edges against OCuLink jackets.

## 7. Cable labels

Both ends of every removable cable should carry permanent pod/bay labels:

- POD-1 / GPU-A / LINK-A
- POD-1 / GPU-B / LINK-B
- POD-1 / GPU-C / LINK-C
- PWR-A / PWR-B / PWR-C
- FAN-1 / FAN-2

J-Link software should use the same A/B/C bay naming where possible.

## 8. Serviceability

A card must be removable without disassembling the other two cards.

Target sequence:

1. power down host and pod,
2. disconnect AC,
3. release that bay’s power cable restraint,
4. disconnect OCuLink at the receiver only as required,
5. release GPU bracket clamp,
6. release adjustable side/tail support,
7. remove card vertically/rearward without crossing adjacent power cables.

If the CAD cannot satisfy this sequence, cable management is too tight.

## 9. Thermal instrumentation

Provide M3 insert sites for optional thermistors/probes at:

- intake plenum center
- between A/B near GPU intake height
- between B/C near GPU intake height
- receiver-board zone
- PSU-adjacent printed hardpoint

The sensors are optional; their mounts should not block airflow when unused.


---

## Source: ASTRA_FREECAD_HANDOFF.md

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


---

## Source: CAD_PARAMETERS.md

# CAD Parameter Table

Authoritative values for Astra/Blender, revision 2.0-preCAD.

| Parameter | Value |
|---|---|
| Printer build volume | 220 × 220 × 270 mm |
| Maximum one-piece print bounding box | 200 × 188 × 254 mm |
| Operational printed-body envelope after rotation | 254 W × 200 D × 188 H mm |
| GPU bay count | 3 |
| Maximum card thickness target | 68 mm |
| Minimum card thickness adjustment target | 35 mm |
| Maximum card body height target | 165 mm |
| Maximum card length target with deliberate overhang | 360 mm |
| Maximum card mass without tail support | 1.2 kg |
| Maximum card mass with metal-supported tail restraint | 2.2 kg |
| Minimum inter-card clear channel at max envelope | 12 mm |
| Width map | 13 + 68 + 12 + 68 + 12 + 68 + 13 = 254 mm |
| Fan count / size | 2 × 120 × 120 × 25 mm |
| Common intake plenum target | 25–35 mm |
| General wall | 2.4–3.0 mm |
| Structural ribs | 5–7 mm effective section |
| Major hardpoint effective section | 7–10 mm |
| Internal fillets | 3–6 mm radius target |
| OCuLink signal raceway | >=28 × 16 mm common clear section |
| GPU power service channel | >=28 × 20 mm per bay target |
| Control/PWM channel | >=14 × 10 mm |
| Expansion hardpoint pattern | 4 × M4 on 80 × 60 mm rectangle |
| Expansion blank | 42 × 30 mm |
| Production material | plain PETG |
| Spool requirement | one continuous 5 kg spool |
| Preferred print mass | <=3.0 kg |
| Hard slicer mass ceiling | <=4.0 kg including brim/support |
| Nozzle | 0.6 mm preferred |
| Layer height | ~0.28 mm starting point |

## First-population validation object

MSI RTX 3060 Ventus 2X 12G OC: 235 L × 124 H × 42 T mm, 675 g, 170 W, 1 × 8-pin.

## Receiver mount

ADT F9Q-BK10 exact fixed mounting-hole coordinates are **TBD until vendor CAD/physical board verification**. Use 3.6–4.0 mm wide × 20–30 mm universal tray slots with M3 metal standoffs in the pre-CAD model.


---

## Source: CURRENT_ARCHITECTURE.md

# System Architecture — Universal 3-GPU Pod

## Existing host

- CPU: AMD Ryzen 7 7700
- Motherboard: MSI PRO X870-P WIFI
- RAM: 64GB DDR5
- Existing accelerator: RTX 5070 Ti 16GB
- M2_1 and M2_2 remain occupied.
- M2_3 must remain empty if PCI_E4 is expected to remain x4.

MSI documents PCI_E1 as CPU-connected PCIe 5.0 x16 for Ryzen 7000/9000 and supports BIOS bifurcation including x4+x4+x4+x4. MSI also documents PCI_E4 as chipset PCIe 4.0 x4, dropping to x2 if M2_3 is populated.

## Current first-pod topology

```text
Ryzen 7 7700 / MSI PRO X870-P WIFI

PCI_E1 CPU x16
  BIOS bifurcation: x4 / x4 / x4 / x4
        |      |      |      |
        |      |      |      +--> RESERVED host branch / future second-pod experiment
        |      |      +---------> Pod 1 GPU-C receiver x4
        |      +----------------> Pod 1 GPU-B receiver x4
        +-----------------------> Pod 1 GPU-A receiver x4

PCI_E4 chipset Gen4 x4
        +-----------------------> RTX 5070 Ti external/lower-shelf link

M2_3 = EMPTY
```

Only three E1 branches are consumed by Pod 1. The fourth E1 x4 branch is preserved as a future resource. Do not assume it is enough for a full second three-GPU pod; a second pod requires a deliberate new data-uplink design (additional root ports, an active PCIe switch, another host, or another qualified transport).

## Universal-card principle

The pod is mechanically card-agnostic. Electrically, each installed card must be compatible with the selected receiver/transport and host software stack.

First population:
- 3 × MSI RTX 3060 Ventus 2X 12GB
- 12GB GDDR6 each
- 170W each
- 235 × 124 × 42mm each
- 1 × 8-pin PCIe auxiliary power each

These dimensions are validation inputs, not hard chassis dimensions.

## Compute model

J-Link is the JE Horizon software fabric. It is not NVIDIA NVLink and not SEGGER J-Link/JTAG.

J-Link responsibilities:
- device discovery and persistent GPU IDs
- per-device free/used VRAM telemetry
- model residency registry
- workload placement and queueing
- topology/bandwidth benchmark cache
- process/GPU affinity
- worker health and restart policy
- optional distributed training orchestration

Primary operating mode:
- independent resident workers
- task parallelism
- model pinning
- agent parallelism
- pipeline experiments

Secondary mode after validation:
- PyTorch DDP
- DeepSpeed
- FSDP
- explicit model sharding

Aggregate VRAM is physical capacity across devices, not automatic unified VRAM.


---

## Source: CURRENT_MANIFEST.md

# Current Authoritative File Manifest

This manifest exists so an agent can ignore archived/interrupted drafts.

Authoritative files in `/Harness Project/current/`:

- README_FIRST.md
- HANDOFF_STATUS.md
- ASTRA_FREECAD_HANDOFF.md
- MASTER_BLUEPRINT.md
- MECHANICAL_ENVELOPE.md
- CAD_PARAMETERS.md
- DIMENSION_AUTHORITY_AND_TBDS.md
- MATERIAL_AND_PRINT_PLAN.md
- FASTENERS_AND_HARDPOINTS.md
- AIRFLOW_AND_CABLE_CHANNELS.md
- CURRENT_ARCHITECTURE.md
- POWER_AND_CABLING.md
- POD_EXPANSION_INTERFACE.md
- J_LINK_SOFTWARE_FABRIC.md
- PURCHASE_AND_BOM.md
- VALIDATION_CHECKLIST.md
- SOURCE_MANIFEST.md
- DECISIONS.md
- decisions.json
- vendor_cad/README.md

Historical drafts, superseded GPU concepts, old four-slot designs, alternate fan layouts, and interrupted design branches live under `/Harness Project/archive/` and are non-authoritative.


---

## Source: DECISIONS.md

# Frozen Decisions — Revision 2.0-preCAD

- Pod count design unit: **3 GPUs exactly**.
- Expansion: build another identical 3-GPU pod; do not enlarge Pod 1.
- Passive PCIe daisy chaining between pods: **not allowed**.
- Chassis: one continuous print.
- Mid-print spool changes: **not allowed**.
- Production material: plain quality PETG from one 5 kg spool.
- Max print bounding box: 200 × 188 × 254 mm.
- Operational printed-body envelope: ~254 W × 200 D × 188 H mm.
- Universal target: 35–68 mm card thickness, <=165 mm body height, <=360 mm length via rear overhang.
- Max-envelope inter-card air gap: >=12 mm.
- Cooling: 2 × 120 mm pressure-oriented PWM fans, common 25–35 mm plenum.
- Structural fasteners: M4 through-bolts/washers/metal nuts; no reusable structural threads directly in PETG.
- PCB/electronics: M3 machine screws + metal standoffs.
- Heat-set inserts: secondary/serviceable attachments only.
- Receiver candidate: ADT F9Q-BK10; exact board hole coordinates remain a hard CAD verification gate.
- Host adapter candidate: RIITOP PCIe 4.0 x16 -> 4 × OCuLink SFF-8612; use 3 branches for this pod.
- Host board: MSI PRO X870-P WIFI; PCI_E1 x4+x4+x4+x4 bifurcation.
- M2_3 remains empty when preserving PCI_E4 x4.
- RTX 5070 Ti remains an independent worker on PCI_E4 extension.
- First pod population: 3 × MSI RTX 3060 Ventus 2X 12GB, but chassis is not 3060-specific.
- J-Link = JE Horizon software fabric, not NVLink/JTAG.
- Aggregate VRAM is not represented as unified memory.


---

## Source: DIMENSION_AUTHORITY_AND_TBDS.md

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


---

## Source: FASTENERS_AND_HARDPOINTS.md

# Fasteners, Inserts, Standoffs and Hardpoints

**Design rule:** no reusable structural thread cut directly into printed plastic.

## 1. Standard thread system

Use two thread families only unless verified hardware requires otherwise:

- **M4** — structural chassis, fan, PSU restraint, pod docking, GPU support
- **M3** — PCB/electronics, cable combs, small covers, sensor/control mounts

This keeps tools and spares simple.

## 2. Primary structural fasteners — M4

Recommended stock for one pod plus spares:

| Item | Buy qty | Expected use |
|---|---:|---|
| M4 × 10 socket-head machine screws | 20 | covers/short metal clamp interfaces |
| M4 × 12 socket-head machine screws | 30 | structural brackets/adjusters |
| M4 × 16 socket-head machine screws | 30 | thicker clamp stacks |
| M4 × 20 socket-head machine screws | 20 | tail support / docking plates |
| M4 × 30 socket-head machine screws | 12 | fan/guard stacks depending final thickness |
| M4 × 35 socket-head machine screws | 12 | fan + isolator + chassis + nut option |
| M4 flat washers | 100 | every plastic-facing structural joint |
| M4 nyloc nuts | 60 | primary through-bolts |
| M4 standard hex nuts | 30 | captive-nut pockets where nyloc is unsuitable |
| M4 knurled/thumb nuts/screws | 6 | optional tool-light GPU clamp adjustment |

304 stainless is fine for the chassis environment; high-strength alloy is also acceptable. Use washers anywhere a screw/nut bears on PETG.

## 3. Heat-set inserts

Heat-set inserts are for serviceable attachment, not the highest structural loads.

### M3

Preferred family: ruthex RX-M3x5.7 or dimensionally equivalent.

Reference dimensions:

- internal thread: M3
- insert length: 5.7 mm
- outer diameter: ~4.6 mm
- published recommended printed hole for this family: ~4.0 mm

Buy: 100-pack.

Use for:

- cable raceway lids
- control/sensor brackets
- small service panels
- optional receiver-tray accessories

### M4

Preferred family: ruthex RX-M4x8.1 or dimensionally equivalent.

Reference dimensions:

- internal thread: M4
- insert length: 8.1 mm
- outer diameter: ~6.3 mm
- published recommended printed hole for this family: ~5.6 mm

Buy: 50-pack.

Use for:

- removable non-primary brace interfaces
- service panels subjected to more load than M3
- adjustable secondary card shoes when a through-bolt is geometrically impossible

**Important:** tune insert holes with the actual insert + printer + PETG coupon. The CAD nominal is not the final printer-compensated hole.

## 4. PCB / receiver mounting

Preferred receiver: ADT F9Q-BK10.

### What is verified

- PCIe 4.0 x4 OCuLink receiver to x16 mechanical slot
- 50 cm cable in the F9Q-BK10 package description
- redriver-equipped
- vendor publishes downloadable 3D CAD

### What is deliberately NOT guessed

The exact board mounting-hole coordinates and hole diameters are not released in this package because the vendor CAD archive has not yet been imported into the model.

### Universal tray hardware

Astra should design the receiver tray around:

- M3 × 6 machine screws: 24
- M3 × 8 machine screws: 24
- M3 flat washers: 60
- M3 nyloc/hex nuts: 30
- M3 brass/stainless standoffs, 6 mm and 10 mm: 12 each

The tray uses 3.6–4.0 mm wide longitudinal slots. Metal standoff + washer + nut clamps through the tray. No screw should rely on an M3 thread cut directly into PETG.

When vendor CAD is imported, choose the standoff height that clears underside components and preserves PCIe connector alignment. If receiver holes are not M3-compatible, revise the adapter hardware — **never enlarge the PCB holes by assumption**.

## 5. Fan mounting

Fan: 120 × 120 × 25 mm class, current target ARCTIC P12 Max.

Use machine screws, not self-tapping fan screws.

Preferred stack:

```text
M4 screw head
metal fan guard (optional)
fan frame
1–2 mm elastomer washer/pad
printed fan-wall boss
M4 flat washer
M4 nyloc nut
```

Select M4 × 30 or M4 × 35 after final guard/pad/boss thickness is modeled.

Astra must import/check the selected fan’s manufacturer 2D drawing before fixing hole coordinates. Do not infer from a decorative fan model.

## 6. GPU restraints

### I/O bracket restraint

Do not depend on a specific GPU manufacturer shroud hole. Clamp the standard metal I/O bracket region or a separate metal crossbar.

Recommended chassis fastener: M4 through-bolt + washer + nyloc nut.

### Adjustable side shoes

- M4 × 12/16 through-bolt in elongated slot
- metal washer both faces
- nyloc nut or captive metal nut
- 1–2 mm EPDM/neoprene pad on GPU contact face

### Tail support

Long/heavy GPU tail support should use a **metal vertical rod/flat bar** captured by the printed chassis rather than a long printed cantilever.

Starting concept:

- 2 × M4 or M5 stainless threaded rods / aluminum flat bars
- adjustable padded cradle
- M4/M5 washers + nyloc nuts
- receiver-side and tail-side load paths tied into chassis ribs

Exact tail-support metal dimensions are a CAD iteration item, not frozen.

## 7. PSU restraint

Do not drill/screw arbitrary points into the PSU enclosure.

Use:

- two 15–25 mm wide stainless perforated straps or purpose-made metal straps
- 1–2 mm EPDM/neoprene isolation strip
- 4 × M4 through-bolts per strap pair as geometry requires
- large washers
- nyloc nuts

The printed chassis supplies reinforced strap slots/hardpoints. The metal strap carries clamp tension.

## 8. Pod docking hardpoints

Fixed standard for future compatibility:

- four M4 holes on 80 × 60 mm rectangle
- through-bolted preferred
- at least 16 mm OD equivalent load-spreader/boss region around each hole
- two ribs from each dock boss into the nearest main rail
- metal joining plate between pods, not PETG tongue-to-PETG tongue

## 9. Tightening philosophy

PETG creeps under sustained clamp load. Do not over-torque and crush printed features. Use broad washers, metal spacers where a fixed gap is required, and nyloc nuts to retain preload without excessive torque.

Any joint that defines PCIe connector alignment should bottom on a metal standoff/spacer, not compress plastic until alignment “looks right.”


---

## Source: HANDOFF_STATUS.md

# Handoff Status — Astra Ready for Parametric CAD

**Revision:** 2.0-preCAD

This folder is the current authoritative JE Horizon Universal 3-GPU Pod package.

## Frozen product concept

- Exactly three GPU bays per pod.
- GPU model is not fixed; three RTX 3060 Ventus 2X cards are the first test population only.
- Expansion means another three-GPU pod, joined mechanically/control-wise and later by a separately validated compute fabric.
- One continuous monolithic print.
- One continuous 5 kg PETG spool; no mid-print spool change.
- Structural load-bearing threads are metal: M4 through-bolts/nuts by default, M3 metal standoffs for PCBs.
- Heat-set inserts are reserved for secondary/service attachments.
- Two 120 mm pressure fans feed a 25–35 mm common plenum and three GPU bays.
- Signal, GPU power, and control wiring use separate serviceable raceways.

## Astra may start now

Astra can begin the parametric `.blend` using:

1. `ASTRA_HANDOFF_PROMPT.md`
2. `MASTER_BLUEPRINT.md`
3. `CAD_PARAMETERS.md`
4. `MATERIAL_AND_PRINT_PLAN.md`
5. `FASTENERS_AND_HARDPOINTS.md`
6. `AIRFLOW_AND_CABLE_CHANNELS.md`
7. `DIMENSION_AUTHORITY_AND_TBDS.md`

## Do not call the model production-ready yet

Final STL remains blocked on the F9Q-BK10 receiver CAD/physical measurements, exact PSU/service clearances, insert-hole coupon results, and slicer mass/support verification.

The correct engineering response to a missing hardware dimension is a parameter/TBD or slotted interface — never an invented number.


---

## Source: J_LINK_SOFTWARE_FABRIC.md

# J-Link — JE Horizon Multi-GPU Software Fabric

J-Link is the software/orchestration layer for one or more GPU pods. It is **not** NVLink and not a JTAG/J-Link debug probe.

## Physical naming

Each GPU receives a stable topology label:

- `POD1-A`
- `POD1-B`
- `POD1-C`

Future pod:

- `POD2-A`
- `POD2-B`
- `POD2-C`

The software maps these physical bay labels to GPU UUID/PCI bus ID at boot and warns if topology changes.

## Inventory record per GPU

Store:

- pod_id / bay_id
- PCI bus ID
- GPU UUID
- vendor/model
- VRAM total/free
- CUDA/runtime support
- negotiated PCIe generation/width
- measured H2D and D2H bandwidth
- temperature
- power
- utilization
- supported precision/memory modes

## Scheduling priorities

1. Keep models resident when practical.
2. Prefer independent tasks/agents over unnecessary synchronized multi-GPU jobs.
3. Place transfer-sensitive work on the best measured host link.
4. Keep training/evaluation/inference workers separately pinnable.
5. Treat every additional pod as another topology object, not as an assumed shared-memory extension.

## First-host topology

Pod 1 uses three CPU-root x4 branches from PCI_E1 bifurcation. The existing RTX 5070 Ti uses the separate chipset PCI_E4 x4 path. The scheduler should benchmark rather than assume equal effective bandwidth/latency.

## Multi-GPU training

Allowed after electrical/link validation:

- DDP
- DeepSpeed
- FSDP
- explicit model/pipeline sharding

Aggregate VRAM is a capacity inventory, not automatically one address space.

## Pod expansion

A second pod may later connect through:

- additional host PCIe lanes,
- an active PCIe switch/fabric,
- a second host joined over high-speed Ethernet,
- another qualified transport.

J-Link should abstract worker placement so the mechanical pod design does not hard-code the future transport.


---

## Source: MASTER_BLUEPRINT.md

# JE Horizon Universal 3-GPU Pod — Master Blueprint

**Document ID:** JEH-HW-3GPU-POD  
**Revision:** 2.0-preCAD  
**Date:** 2026-09-30  
**Units:** millimetres unless noted

## 1. Mission

Build a clean, single-piece, printed external GPU harness that holds **three GPUs**, their three external PCIe receiver docks, forced-air plenum, cable routing infrastructure, control mounting, and an integrated external-PSU restraint system. The chassis is universal within a declared fit envelope rather than tied to the RTX 3060 Ventus 2X that will populate revision 1.

The first three GPUs are a validation population, not a dimensional master.

## 2. System boundary

The pod contains:

- 3 GPU mechanical bays: A, B, C
- 3 x4 OCuLink receiver/dock positions
- one front intake fan wall, 2 × 120 mm
- common intake plenum and three controlled GPU airflow lanes
- high-speed signal raceway
- GPU-power raceway
- control/PWM/telemetry raceway
- strain-relief hardpoints
- removable receiver service panel / tray interface
- PSU saddle hardpoints integrated into the one-piece print
- standardized pod-to-pod mechanical/control expansion panel

The PSU itself and GPUs are not printed components. They may extend beyond the print bounding box after assembly.

## 3. Printer and coordinate system

Printer: Creality Ender-3 S1 Pro. Nominal build volume 220 × 220 × 270 mm.

### Print orientation

Use one-piece print bounding box:

- Print X = 200 mm maximum
- Print Y = 188 mm maximum
- Print Z = 254 mm maximum

Astra should model a 5 mm virtual keepout around the 200 × 188 bed footprint for brim/skirt and edge tolerances. Do not let support/brim exceed the physical bed.

### Operational orientation

Rotate the finished object so that:

- Pod width W ≈ 254 mm
- Pod depth D ≈ 200 mm
- Pod printed-body height H ≈ 188 mm

The GPUs project rearward as required. The PSU is restrained beneath/outboard of the printed body using integral hardpoints and metal straps; its physical overhang does not need to lie within the printer build volume.

## 4. Three-bay GPU geometry

### 4.1 Max-envelope bay layout

Use 254 mm total operational width as the datum.

At the maximum supported card thickness:

```text
left structural margin     13
Bay A max envelope         68
air channel A-B            12
Bay B max envelope         68
air channel B-C            12
Bay C max envelope         68
right structural margin    13
-----------------------------
TOTAL                     254
```

Nominal bay envelope ranges along W:

- Bay A: 13–81
- Channel AB: 81–93
- Bay B: 93–161
- Channel BC: 161–173
- Bay C: 173–241
- right structure: 241–254

These are **maximum-envelope zones**, not fixed card clamp positions. Each bay requires an adjustable lateral shoe/clamp so a 35–42 mm card does not float inside a 68 mm cavity.

### 4.2 Adjustable card positioning

Each bay uses:

1. fixed receiver/PCIe datum near the front-bottom reference,
2. adjustable side shoe with elongated M4 slot,
3. padded card-body support at a verified non-component contact patch,
4. metal I/O-bracket restraint or independent bracket clamp,
5. optional far-end support for cards >280 mm or >1.2 kg.

No clamp may press on fan blades, exposed PCB components, heatpipes, vapor chambers, electrical connectors, or fragile plastic shroud decoration.

### 4.3 Universal card fit target

- Thickness: 35–68 mm
- Height from receiver datum: <=165 mm target
- Length: <=360 mm with rear overhang and far-end support
- Mass: <=1.2 kg without tail support; <=2.2 kg with tail support

For cards outside this range, revise the pod or use a different support insert. Do not force-fit.

### 4.4 First validation population

MSI GeForce RTX 3060 Ventus 2X 12G OC:

- 235 × 124 × 42 mm
- 675 g
- 170 W
- one 8-pin auxiliary connector

Three of these leave substantial airflow margin inside the universal 68 mm bay envelope.

## 5. Receiver-dock architecture

Preferred receiver candidate: **ADT-Link F9Q-BK10**, PCIe 4.0 x4 OCuLink to mechanical PCIe x16, 50 cm cable, redriver-equipped.

ADT publishes vendor 3D CAD. The product page also explicitly states OCuLink is not hot-swappable.

### 5.1 Do not guess board holes

The final receiver-board screw pattern is a release gate. The direct CAD archive URL is recorded in `vendor_cad/README.md` and `PURCHASE_AND_BOM.md`.

Until imported:

- model the receiver as a clearance envelope,
- place it on a **universal slotted tray**, not fixed guessed posts,
- use metal M3 standoffs through slots with washers/nuts,
- finalize standoff coordinates only after CAD/physical verification.

### 5.2 Universal receiver tray

Starting tray geometry:

- three independent receiver zones, one per GPU
- longitudinal M3 clearance slots: 3.6–4.0 mm wide × 20–30 mm long
- at least 10 mm of plastic/web around slot ends
- large washer under the plastic to distribute clamp load
- preferred standoff: M3 brass or stainless, 6–10 mm tall after PCB underside clearance is measured
- through-bolt/nut under tray preferred over threading plastic

If the receiver board uses holes too small for M3 or nonstandard mounting, create a thin aluminum adapter plate or a dedicated printed insert. Do not drill the PCB.

## 6. Airflow system

### 6.1 Fan wall

Use 2 × ARCTIC P12 Max or equivalent pressure-oriented 120 × 120 × 25 mm PWM fans.

Place fans side-by-side across the 254 mm pod width. Two 120 mm frames consume 240 mm, leaving approximately 7 mm structural border per outer side.

The fan wall is a structural frame, not a solid plate:

- large circular fan openings
- ribs radiating from fan screw bosses into side rails
- removable metal fan guards on exposed side
- soft 1–2 mm elastomer washers/pads at fan corners if required

### 6.2 Plenum depth

Target 25–35 mm common intake plenum between fan discharge plane and first flow-divider edge. Do not split immediately at the fan blade plane; allow pressure to equalize first.

### 6.3 GPU airflow lanes

Create five longitudinal flow opportunities rather than only two narrow gaps:

- outer-left lane along Bay A outside face
- A-B inter-card channel
- controlled central paths through/under receiver region where not blocked
- B-C inter-card channel
- outer-right lane along Bay C outside face

At max 68 mm card thickness, retain **12 mm absolute minimum clear inter-card channel**. For thinner cards, adjustable shoes should increase the effective channel width rather than centering cards randomly.

For the 42 mm first-population cards, target roughly 20–25 mm minimum clear gaps after clamp/receiver/cable intrusion; use the surplus width to favor intake-side clearance.

### 6.4 Exhaust

Keep rear and card-edge exhaust substantially open. No cosmetic rear panel across the GPU exhaust field. Use narrow protective rails, not a wall.

## 7. Structural strategy — where plastic matters

The chassis should behave like a ribbed monocoque, not a solid brick.

### High-load zones

Reinforce:

- GPU receiver datum rail
- I/O bracket restraint rail
- far-end GPU support hardpoints
- PSU strap/saddle hardpoints
- pod docking hardpoints
- fan screw bosses and fan-wall-to-sidewall transitions
- handles/lift points if added
- cable strain-relief anchors for heavy 12V-2x6/PCIe bundles

Use 5–7 mm local ribs/gussets, generous fillets, and increased perimeter count/local infill.

### Low-load zones where material should be removed

Aggressively lighten:

- broad side-wall centers
- plenum panel centers away from fan bosses
- receiver tray areas not under standoffs
- cable-cover panels
- cosmetic top/bottom panels
- any floor area not on a direct load path

Use rounded triangular/hexagonal windows with 8–12 mm perimeter webs around cutouts. Avoid sharp internal corners.

### No full solid floor

The floor should be a ladder/spine structure:

- two longitudinal load rails
- crossmembers at receiver and GPU support locations
- open windows between crossmembers
- separate narrow cable raceway walls

This reduces filament, lets heat escape, and prevents the pod from becoming a heat-soaked tray.

## 8. PSU mounting

A standard ATX PSU is approximately 150 mm wide × 86 mm tall; exact depth varies. The candidate Corsair RM1000x is 160 × 150 × 86 mm.

The PSU may hang beneath or partly rearward of the printed body using the pod's integral saddle hardpoints. Do **not** screw into the PSU enclosure except with manufacturer-provided case mounting holes and approved screw depth. Preferred restraint:

- two metal straps or a metal cradle plate,
- 1–2 mm neoprene/EPDM isolation pads,
- M4 through-bolts through reinforced chassis hardpoints,
- captive nuts/nyloc nuts,
- unobstructed PSU fan intake and exhaust,
- unobstructed AC switch/inlet and modular cable panel.

Astra should parameterize PSU width/depth/height and cable-projection keepout rather than bake in one PSU model.

## 9. Pod expansion interface

Each pod remains a three-GPU mechanical unit.

Provide a blank expansion/service panel on one side/rear with:

- 4 × M4 structural through-bolt hardpoints on an **80 × 60 mm rectangular pattern**
- central 42 × 30 mm pass-through/blanking zone
- 2 × M3 insert locations for a future connector plate
- mating flat datum surface so two pods can be bridged by a metal joining plate

This interface is for mechanical alignment, control/network cabling, and future **active** expansion hardware. It does not passively distribute PCIe lanes.

## 10. Cable architecture

Three independent routing classes:

1. **Signal:** OCuLink/high-speed PCIe
2. **Power:** GPU and receiver PSU leads
3. **Control:** PWM, USB, telemetry, optional Ethernet

Do not bundle signal and high-current power in the same tight raceway.

Detailed dimensions are in `AIRFLOW_AND_CABLE_CHANNELS.md`.

## 11. Fastener philosophy

No structural screw should cut its own reusable thread directly into printed PETG.

- structural load: M4 through-bolt + washer + nyloc/captive metal nut
- removable secondary panel: M3/M4 brass heat-set insert
- PCB: M3 metal standoff + machine screw + metal nut/washer as required
- fans: M4 machine screws through fan and chassis, with nut/insert; no fan self-tappers into plastic

Exact bill of fasteners is in `FASTENERS_AND_HARDPOINTS.md`.

## 12. Electrical topology

For the current host, MSI documents PCI_E1 CPU lanes as supporting x4+x4+x4+x4 bifurcation on Ryzen 7000/9000. The preferred host adapter is a RIITOP PCIe 4.0 x16 to four OCuLink SFF-8612 ports. Only three ports are used for this pod.

RTX 5070 Ti is independently extended from PCI_E4 Gen4 x4. M2_3 must stay empty because MSI documents that installing M2_3 reduces PCI_E4 to x2.

The extra fourth OCuLink port on the host card is not automatically a second-pod expansion solution; a second three-GPU pod requires additional validated lanes/active switching/another host path.

## 13. Astra deliverables

Astra should produce:

- native `.blend`
- parameter table inside Blender text block or external JSON
- STEP/STL only after fit gate
- section views showing airflow and cable lanes
- exploded view showing inserts, through-bolts, standoffs and PSU straps
- receiver tray with placeholder CAD clearly marked until vendor CAD imported
- three GPU envelope objects set to 68 × 165 × 360 mm maximum
- three RTX 3060 validation objects set to 42 × 124 × 235 mm
- interference check with max envelope
- slicer-oriented model aligned to 200 × 188 × 254 maximum
- estimated printed volume and mass before release

## 14. Release gates

Do not release a production STL until all are true:

- [ ] F9Q-BK10 CAD imported or purchased board measured
- [ ] exact receiver hole/keepout pattern verified
- [ ] exact PSU measured and cable bend keepouts modeled
- [ ] 3060 validation cards fit without collision
- [ ] max-envelope card interference check passes
- [ ] 120 mm fan drawing imported/verified
- [ ] all heat-set insert holes tuned with a print coupon
- [ ] slicer mass is below selected spool usable mass with >=15% reserve
- [ ] no support material exceeds spool reserve
- [ ] airflow channels remain clear after actual cable routing
- [ ] full print plus brim fits the Ender-3 S1 Pro bed


---

## Source: MATERIAL_AND_PRINT_PLAN.md

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


---

## Source: MECHANICAL_ENVELOPE.md

# Mechanical Envelope — Authoritative Universal 3-GPU Pod

**Revision:** 2.0-preCAD  
**Authority:** subordinate to `MASTER_BLUEPRINT.md` and `DIMENSION_AUTHORITY_AND_TBDS.md`

## Printer constraint

Creality Ender-3 S1 Pro nominal build volume: 220 × 220 × 270 mm.

The **one-piece printed core** shall fit inside:

- Print X <= 200 mm
- Print Y <= 188 mm
- Print Z <= 254 mm

This preserves margin for brim/adhesion and avoids using the printer's nominal limits as hard geometry.

## Operational orientation after print

Rotate the finished core so:

- operational width W ≈ 254 mm
- printed-core depth D ≈ 200 mm
- printed-body height H ≈ 188 mm

Long GPUs deliberately overhang rearward beyond the 200 mm printed core.

## Three universal GPU bays

Across W = 254 mm:

```text
13 structure
68 Bay A max envelope
12 minimum A/B airflow channel
68 Bay B max envelope
12 minimum B/C airflow channel
68 Bay C max envelope
13 structure
= 254 mm
```

Each bay targets:

- thickness: 35–68 mm adjustable
- body height: <=165 mm
- card length: <=360 mm with rear overhang
- card mass: <=1.2 kg without metal tail support
- card mass: <=2.2 kg with metal tail support

The first test population is 42 mm thick, but card clamps/supports must be adjustable. The chassis is not centered or hard-shaped around the RTX 3060.

## GPU datums and support

Use only universal datums:

1. receiver PCIe slot datum,
2. GPU metal I/O bracket plane,
3. adjustable lateral shoe,
4. padded safe body support,
5. optional metal far-end support.

Do not key the chassis to GPU shroud screws, fan locations, backplate decoration, or one auxiliary-power location.

Card power uses an open top/rear service zone suitable for 8-pin and 12V-2x6 layouts.

## Fan wall

Two ARCTIC P12 Max 120 × 120 × 25 mm fans mount **side-by-side across operational width**.

- two frames = 240 mm
- outer border ≈7 mm each side before local ribs
- hole center spacing = 105 × 105 mm from vendor drawing
- vendor fan hole diameter = 4.40 mm; chassis M4 clearance tuned by coupon

Fan wall is a ribbed frame with large open fan throats, not a solid plate.

## Plenum

Common intake plenum target: 25–35 mm from fan discharge plane to first hard divider.

Use rounded transitions and thin splitters after a short pressure-equalization volume. Maintain the 12 mm inter-card throats after every cable, clamp, and receiver feature is modeled.

## Rear / exhaust

Rear stays substantially open. Do not close GPU exhaust with a cosmetic wall.

Operational shelf depth must include:

- card rear overhang,
- auxiliary-power connector protrusion,
- cable bend radius,
- service clearance.

## Structural skeleton

Use a ribbed monocoque / ladder frame:

- 2.4–3.0 mm low-load skins
- 5–7 mm effective structural ribs/gussets
- 7–10 mm major hardpoint sections
- 3–6 mm inside fillets
- large radiused lightening windows
- no full solid floor

Primary load paths:

- receiver datum rail
- GPU I/O bracket rail
- lateral shoe rails
- tail-support sockets
- fan-wall junctions
- PSU strap hardpoints
- pod docking hardpoints
- heavy cable strain-relief anchors

## PSU relationship

PSU remains a separate intact ATX enclosure. Current reference envelope: Corsair RM1000x ATX 3.1, 160 × 150 × 86 mm.

Keep PSU W/D/H and cable projection parametric. Use metal restraint straps/cradle pieces and M4 through-bolted chassis hardpoints with EPDM/neoprene isolation. Never make the PSU mass depend on printed threads.


---

## Source: POD_EXPANSION_INTERFACE.md

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



---

## Source: POWER_AND_CABLING.md

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


---

## Source: PURCHASE_AND_BOM.md

# Current BOM — Universal 3-GPU Pod

**Price snapshot:** 2026-09-30. Prices move; verify at checkout.

## A. GPUs — first population

### 3 × MSI GeForce RTX 3060 Ventus 2X 12G OC refurbished
- Qty: 3
- Current target listing: Newegg marketplace / QYTech
- Target price: $359.99 each
- Extended: **$1,079.97** before tax
- Manufacturer dimensions: 235 × 124 × 42mm
- Board power: 170W each
- Aux: one 8-pin each

Link: https://www.newegg.com/msi-rtx-3060/p/1FT-0009-00B46

## B. Main print material — BUY

### SUNLU Large Spool 5KG High Speed PETG, 1.75mm, black
- Qty: 1
- One physical 5kg spool; chosen specifically to avoid mid-print spool change
- Recent Amazon price snapshot: about **$50.39**
- ASIN: B0FGPBSS1N
- Amazon: https://www.amazon.com/dp/B0FGPBSS1N

Budget: $50–60.

## C. Spool support — BUY

### Heavy-duty external spool roller/holder
Requirements:
- rated for ≥6kg
- ball-bearing rollers
- wide enough for SUNLU 5kg spool
- sits on bench/floor, never on Ender gantry

Amazon search: https://www.amazon.com/s?k=5kg+filament+spool+holder+bearing
Budget: **$20–35**.

## D. Nozzle — BUY

### 0.6mm M6/MK-compatible brass or plated-copper nozzle for Ender-3 S1 Pro
Qty: 2 identical nozzles (one installed, one spare)

Amazon search: https://www.amazon.com/s?k=Ender+3+S1+Pro+0.6mm+M6+nozzle
Budget: **$8–15**.

Use brass/plated copper for standard PETG. Hardened steel is only needed if moving to abrasive fiber-filled filament.

## E. Heat-set inserts — BUY

Preferred known-quality source: CNC Kitchen.

### M3 × 5.7mm standard inserts
- Qty package: 100
- Reference price: ~$10.90
- https://cnckitchenus.store/

### M4 × 8.1mm standard inserts
- Qty package: 50
- Reference price: ~$11.50
- https://cnckitchenus.store/

Amazon substitute search:
https://www.amazon.com/s?k=M3+M4+heat+set+inserts+3d+printing

Do not finalize insert pockets until the actual purchased insert is measured.

## F. Stainless machine screws / washers / nyloc nuts — BUY

Preferred: 304 stainless socket-head cap screws.

M3 assortment needs at least:
- M3×6 / 8 / 10 / 12 / 16 / 20
- 100 washers
- 40 nyloc nuts

M4 assortment needs at least:
- M4×10 / 12 / 16 / 20 / 25 / 30
- 100 washers
- 60 nyloc nuts

Amazon searches:
- https://www.amazon.com/s?k=M3+304+stainless+socket+head+cap+screw+assortment
- https://www.amazon.com/s?k=M4+304+stainless+socket+head+cap+screw+assortment

Combined budget: **$25–40**.

## G. Cooling — BUY

### ARCTIC P12 Max 120mm PWM
- Qty: 2 (buying 5-pack may be cheaper and gives spares)
- 120 × 120 × 25mm
- up to ~3300 RPM
- manufacturer airflow ~81 CFM each
- manufacturer static pressure ~4.35mmH2O
- MSRP reference ~US$15.99 single

Manufacturer page: https://www.arctic.de/us/P12-Max/ACFAN00280A
Amazon search: https://www.amazon.com/s?k=ARCTIC+P12+Max

Budget for two/pack: **$25–40**.

Also buy:
- 2 × 120mm metal finger guards
- 8 × thin silicone/rubber fan isolation washers or corner pads

Budget: **$10–15**.

## H. External PSU — CURRENT REFERENCE, purchase after receiver power map is frozen

### Corsair RM1000e ATX 3.1, 1000W
- 140 × 150 × 86mm reference dimensions
- fully modular
- current Corsair reference around $179.99
- multiple native PCIe power leads

Manufacturer: https://www.corsair.com/us/en/search?q=RM1000e
Amazon search: https://www.amazon.com/s?k=Corsair+RM1000e+1000W+ATX+3.1

Budget: **$160–190**.

**HOLD:** do not purchase solely from wattage. Final choice must match the exact receiver-board power inputs plus three GPU auxiliary feeds using approved native cables.

## I. PCIe bifurcation transport — DESIGN HOLD

Required function:
- PCI_E1 x16 host card supporting four x4 branches; only three used for Pod 1
- matched high-speed PCIe cables
- 3 × locally powered x16-mechanical receiver boards
- Gen4 x4 operation per installed GPU target

Budget placeholder: **$200–400** until exact validated hardware is chosen.

Do not buy generic x1 mining risers.

## J. Cable-management consumables — BUY

- reusable 10–12mm hook-and-loop cable ties, 30 pack
- rubber-lined P-clamps sized 6/8/10/12mm mixed pack
- adhesive labels or heat-shrink labels A/B/C
- braided sleeve only where it does not increase bend stiffness excessively

Amazon search:
https://www.amazon.com/s?k=reusable+velcro+cable+ties+p+clamp+assortment

Budget: **$20–30**.

## K. Optional 5kg dry-feed enclosure

Not required to CAD the pod, but useful for a multi-day PETG print in humid conditions.

Simplest route:
- large gasketed tote/bucket sized for 5kg spool
- internal axle or roller
- PTFE bulkhead fitting
- desiccant

Budget: **$25–50**.

## Non-GPU first-pod budget

Excluding uncertain PCIe transport:
- filament: ~$50
- spool roller: ~$25
- nozzle: ~$10
- inserts: ~$23
- screws/nuts: ~$35
- cooling/guards: ~$40
- cable management: ~$25
- PSU: ~$180

Approximate subtotal: **$388**, plus the PCIe transport and three GPUs.


---

## Source: README_FIRST.md

# JE Horizon Universal 3-GPU Pod — START HERE

**Revision:** 2.0-preCAD authoritative handoff  
**Date:** 2026-09-30  
**Target CAD workflow:** Astra + FreeCAD

## What this project is

A **universal three-GPU external harness pod** built as one continuous FDM print on a Creality Ender-3 S1 Pro. The first population is three MSI RTX 3060 Ventus 2X 12GB cards, but those cards are validation hardware only; the chassis is designed around a broader adjustable GPU envelope.

Expansion means building another identical three-GPU pod. Do **not** enlarge this pod to four cards.

## Non-negotiables

- Exactly 3 GPU bays.
- One monolithic printed core.
- No mid-print spool change.
- One continuous 5 kg PETG spool.
- Preferred slicer total <=3.0 kg; hard ceiling <=4.0 kg including brim/support.
- No reusable structural screw threads cut directly into PETG.
- M4 through-bolts/washers/metal nuts are the default structural joint.
- M3 metal standoffs/machine screws are the default PCB/electronics joint.
- Heat-set inserts are for secondary/service interfaces, not the primary load path where a through-bolt is possible.
- Two 120 mm ARCTIC P12 Max fans feed a 25–35 mm common plenum.
- Signal, GPU power, and control wiring have separate serviceable raceways.
- Rear GPU exhaust remains substantially open.
- Receiver-board hole coordinates must come from official CAD or physical measurement, never web-photo guessing.
- Pod-to-pod expansion is mechanical/control plus a separately validated compute fabric; no passive PCIe daisy-chain.

## Authoritative geometry

### Print orientation

One-piece print bounding box:

- X <= 200 mm
- Y <= 188 mm
- Z <= 254 mm

Printer nominal volume: 220 × 220 × 270 mm.

### Operating orientation after rotation

Approximate printed-body envelope:

- W = 254 mm across the three GPU bays
- D = 200 mm printed depth; long cards overhang rearward
- H = 188 mm

Bay width map:

```text
13 structure
68 Bay A max
12 A/B clear airflow
68 Bay B max
12 B/C clear airflow
68 Bay C max
13 structure
= 254 mm
```

Universal GPU target per bay:

- thickness: 35–68 mm adjustable
- height: <=165 mm
- length: <=360 mm via rear overhang
- <=1.2 kg without metal tail support
- <=2.2 kg with metal tail support

## Fan authority

ARCTIC P12 Max vendor drawing:

- frame: 120 × 120 × 25 mm
- mounting-hole center spacing: 105 × 105 mm
- vendor hole diameter: 4.40 mm

The chassis uses tuned M4 machine-screw clearance, washers, and metal nuts; no fan self-tappers into PETG.

## Read these in this order

1. **`HANDOFF_STATUS.md`** — current state and what Astra may begin immediately.
2. **`ASTRA_FREECAD_HANDOFF.md`** — direct FreeCAD engineering prompt.
3. **`MASTER_BLUEPRINT.md`** — overall mechanical/product blueprint.
4. **`MECHANICAL_ENVELOPE.md`** — authoritative print/operating envelope and three-bay geometry.
5. **`CAD_PARAMETERS.md`** — compact parameter table.
6. **`DIMENSION_AUTHORITY_AND_TBDS.md`** — hard dimensions vs vendor/measurement gates; prevents invented precision.
7. **`MATERIAL_AND_PRINT_PLAN.md`** — PETG decision, one-spool mass limits, material-removal and local-infill strategy.
8. **`FASTENERS_AND_HARDPOINTS.md`** — M3/M4 screw quantities, washers, nylocs, inserts, standoffs, PSU/GPU restraints.
9. **`AIRFLOW_AND_CABLE_CHANNELS.md`** — plenum, airflow throats, signal/power/control channels, service loops and labels.
10. **`CURRENT_ARCHITECTURE.md`** — host PCIe topology and first GPU population.
11. **`POWER_AND_CABLING.md`** — PSU domains, cable rules, sequencing and universal-power caveats.
12. **`POD_EXPANSION_INTERFACE.md`** — future second-pod interface without pretending passive PCIe expansion exists.
13. **`J_LINK_SOFTWARE_FABRIC.md`** — software topology/scheduling abstraction for one or more pods.
14. **`PURCHASE_AND_BOM.md`** — current component candidates, quantities, sources and shopping notes.
15. **`VALIDATION_CHECKLIST.md`** — gates before production STL and unattended operation.
16. **`SOURCE_MANIFEST.md`** — public/vendor sources supporting the design.
17. **`vendor_cad/README.md`** — official ADT-Link and ARCTIC drawing/CAD references.

## Precedence rule

If two documents disagree:

1. `README_FIRST.md`
2. `DIMENSION_AUTHORITY_AND_TBDS.md`
3. `MASTER_BLUEPRINT.md`
4. `ASTRA_FREECAD_HANDOFF.md`
5. the remaining files

Anything under `/Harness Project/archive/` is historical context only and must not override `current/`.

## Material decision

Use **plain quality PETG**, not PLA, for the first production chassis. The current preferred continuous spool is **ZYLtech 5KG High Speed High Flow PETG**. It is currently listed by ZYLtech at $79.95. The regular 5 kg PETG is $76.95, so the high-flow grade is the preferred small-premium choice for the large 0.6 mm-nozzle print.

Why not jump directly to ASA/PC/nylon/filled composites: this is a near-full-envelope monolithic print on an open Ender-3 S1 Pro. Warp/process/drying/abrasion risk matters more than winning a datasheet-strength contest. PETG is the cost/risk baseline; if thermal qualification fails, re-engineer material/process rather than silently changing filament.

## Astra release rule

Astra may start the parametric FreeCAD model now. Astra must **not** call a production STL final until the F9Q-BK10 receiver CAD/physical measurements, insert coupon, PSU/service clearances, max-envelope interference checks, airflow/cable checks, and slicer mass/support report are complete.


---

## Source: SOURCE_MANIFEST.md

# Source Manifest — Checked 2026-09-30

## MSI motherboard

MSI lane sharing/bifurcation article:
https://us.msi.com/blog/pcie-lane-bifurcation-and-bandwidth-sharing-on-msi-x870e-x870-motherboards

Supports:
- PCI_E1 x4+x4+x4+x4 bifurcation on Ryzen 7000/9000
- PCI_E4 Gen4 x4
- PCI_E4 shares with M2_3 and drops when M2_3 populated

## Creality

Ender-3 S1 Pro official:
https://www.creality.com/products/creality-ender-3-s1-pro-fdm-3d-printer

Ender comparison / build volume:
https://store.creality.com/ca/blogs/all/ender-series-3d-printers-parameter-comparison

Supports:
- 220 × 220 × 270 mm nominal build volume
- 300°C-class hotend capability

## RIITOP

Quad OCuLink host adapter:
https://www.riitop.com/products/riitop-pcie-to-oculink-adapter-4-port-pcie-4-0-x16-to-sff-8612-sff-8611-female-full-speed-64gbps-4port-for-egpupci-e-x4x4x4x4-bifurcation-required

Supports:
- PCIe 4.0 x16 card
- four SFF-8612 ports
- requires x4+x4+x4+x4 motherboard bifurcation

## ADT-Link

F9Q-BK10:
https://www.adt.link/product/F9Q.html

Supports:
- PCIe 4.0 x4 OCuLink to x16 mechanical GPU dock
- 50 cm cable
- redriver
- no hot swap
- ATX/SFX external PSU support
- vendor CAD URL

## ARCTIC

P12 Max:
https://www.arctic.de/us/P12-Max/ACFAN00280A

Supports:
- 120 × 120 × 25 mm
- 400–3300 rpm
- 81.04 CFM
- 4.35 mmH2O
- 12 V, 0.29 A

## Corsair

RM1000x CP-9020271-NA:
https://www.corsair.com/us/en/p/psu/cp-9020271-na/rmx-series-rm1000x-fully-modular-power-supply-cp-9020271-na

Supports:
- 1000 W
- ATX 3.1
- 160 × 150 × 86 mm
- four separate PCIe 8-pin 6+2 cables
- one native 12V-2x6 cable

## Ruthex

M3:
https://www.ruthex.de/en/collections/gewindeeinsatze/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7-messing-gewindebuchsen

M4:
https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m4-50-stuck-rx-m4x8-1-messing-gewindebuchsen

## PETG

ZYLtech 5 kg regular:
https://www.zyltech.com/5kg-texas-size-spool-petg-3d-printer-filament-1-75-mm-11-lbs/

ZYLtech 5 kg high-flow:
https://www.zyltech.com/5kg-texas-size-spool-high-speed-high-flow-petg-3d-printer-filament-1-75mm-11-lbs-made-in-usa/

California Filament 5 kg:
https://californiafilament.com/products/black-petg-filament-1-75mm-5kg



---

## Source: VALIDATION_CHECKLIST.md

# Validation and Test Plan

## Gate 1 — CAD

Pass when:
- core fits 205 × 205 × 250mm box
- all three 3060 validation dummies fit
- universal 60mm-thick / 155mm-high dummy sweep checked
- every fastener has tool access
- every heat-set insert has installation access
- cable bend/service volumes exist
- fan blades have guard and clearance
- rear exhaust open

## Gate 2 — slicer

Pass when:
- no unsupported impossible geometry
- estimated total consumption ≤4.3kg hard limit
- preferred ≤2.8kg
- print can complete without spool swap
- print time accepted by owner
- no support structures trapped inside closed ducts

## Gate 3 — coupon

Print and test:
- M3 insert pocket
- M4 insert pocket
- board slot
- representative rib

Record actual dimensions and update parameters.

## Gate 4 — empty chassis load

Before electronics:
- install all inserts
- torque representative M3/M4 fasteners gently to consistent hand-tool torque
- mount dummy masses or sandbags approximating 3 × 2kg GPUs
- hold 24h
- inspect creep/cracks/layer separation

## Gate 5 — fans / airflow

- run fans alone for 2h
- verify no resonance/fan blade interference
- check plenum leaks
- measure approximate airflow in all four lanes
- adjust baffles if one lane starves

## Gate 6 — electronics one card

- install one receiver + one GPU
- cold boot repeatedly
- validate link width/speed
- run sustained compute
- log GPU, receiver, intake and PETG-support temperature

## Gate 7 — two cards

Repeat enumeration/thermal/load tests with two simultaneous workers.

## Gate 8 — three cards

- repeated cold boots
- all three independent workers
- simultaneous sustained load
- J-Link scheduling
- temperature map
- power-at-wall logging
- check cable/connector temperatures
- inspect chassis creep after cooldown

## Thermal stop rules

Immediate stop for:
- melting odor from printed chassis
- visible sag at receiver or GPU support
- loose heat-set insert
- browning/discoloration near power connector
- hot modular PSU cable/connector beyond expected warm touch
- PCIe errors/link drops correlated with heat

Project PETG structural investigation threshold: 45°C.
Project PETG structural stop/rework threshold: ~50°C sustained at a load-bearing printed feature.

If PETG fails thermal/creep gates, do not simply add infill. Re-evaluate airflow, move hot contact points, add metal load path, or migrate the structural core to a higher-temperature material such as PA6-GF25.


---

## Source: decisions.json

{
  "revision": "2.0-draft",
  "frozen": [
    "Exactly three GPU positions per pod",
    "Universal adjustable GPU carriers; not RTX-3060-specific",
    "One monolithic printed core on Ender-3 S1 Pro",
    "No mid-print spool change",
    "Primary material is one 5kg PETG spool unless validation fails",
    "No machine screws self-threaded into printed plastic",
    "M3 inserts/standoffs for electronics; M4 inserts/through-bolts for structure",
    "Two 120mm front fans feeding expanding plenum and four air lanes",
    "Open rear exhaust",
    "Exact PCIe receiver PCB hole map remains parametric until hardware is purchased",
    "Expansion is another 3-GPU pod, not a larger pod",
    "PodLink does not passively daisy-chain PCIe lanes"
  ],
  "superseded": [
    "four-position pod",
    "fixed 42mm RTX 3060 bay geometry",
    "empty fourth bay / air dam",
    "S80 worker plan",
    "A770 worker plan",
    "active shared x4 switch as preferred first topology"
  ],
  "open_items": [
    "exact PCI_E1 x16-to-x4/x4/x4/x4 transport card",
    "exact three receiver boards/cables",
    "final PSU after receiver input requirements are known",
    "measured heat-set insert dimensions from purchased hardware",
    "final slicer mass and print time",
    "exact RTX 5070 Ti external link hardware"
  ]
}


---

## Source: vendor_cad/README.md

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
