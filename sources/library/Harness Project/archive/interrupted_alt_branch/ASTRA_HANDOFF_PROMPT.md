# Astra CAD Handoff Prompt

You are the CAD/mechanical design engineer for the **JE Horizon Universal 3-GPU Pod revision 2.0-preCAD**.

Read every file in this folder before modeling, especially `MASTER_BLUEPRINT.md`, `CAD_PARAMETERS.json`, `MATERIAL_AND_PRINT_PLAN.md`, `FASTENERS_AND_HARDPOINTS.md`, and `AIRFLOW_AND_CABLE_CHANNELS.md`.

## Goal

Create a parametric Blender design for a **single-piece 3D-printed chassis** that supports exactly three external GPUs, three OCuLink receiver docks, two 120 mm intake fans/common plenum, clean separated cable raceways, and integrated hardpoints for an external ATX PSU restraint. The first GPUs are three MSI RTX 3060 Ventus 2X cards, but the chassis must remain universal within the specified max envelope.

Do not redesign it as a four-GPU pod. Future expansion happens by adding another identical three-GPU pod.

## Absolute constraints

1. Ender-3 S1 Pro nominal build volume = 220 × 220 × 270 mm.
2. One-piece print bounding box must stay <= **200 × 188 × 254 mm** before brim/support.
3. Model in the operational orientation as approximately **254 W × 200 D × 188 H mm**, then supply a print orientation that fits the above bounding box.
4. Exactly 3 GPU bays.
5. Max GPU envelope per bay: **68 mm thickness × 165 mm height × 360 mm length**, with length allowed to overhang rear.
6. Max-envelope inter-card clear airflow gap = **12 mm minimum**. Never put a cable raceway in that 12 mm.
7. Initial validation GPU envelope = 42 × 124 × 235 mm.
8. 2 × 120 × 120 × 25 mm fans side-by-side across pod width.
9. Common fan plenum depth target = 25–35 mm.
10. No structural screw threads directly into PETG.
11. Structural attachments use M4 through-bolts/metal nuts/washers; PCB/electronics use M3 metal standoffs; heat-set inserts are secondary/service attachments only.
12. PSU stays in its intact metal housing and is restrained with metal straps via reinforced chassis hardpoints.
13. OCuLink receiver candidate = ADT F9Q-BK10. Import its official vendor 3D CAD before finalizing board holes. Until then use an envelope + slotted universal tray.
14. Do not invent F9Q mounting-hole coordinates.
15. Do not make OCuLink hot-swappable.
16. Do not use mining USB x1 risers or passive PCIe splitters.

## Bay geometry

Across operational width 254 mm, begin with:

- left structure: 13
- Bay A maximum envelope: 68
- A/B channel: 12
- Bay B maximum envelope: 68
- B/C channel: 12
- Bay C maximum envelope: 68
- right structure: 13

Make card clamps/shoes adjustable so thinner cards gain airflow instead of floating in a 68 mm cavity.

## Mechanical language

Use a ribbed monocoque:

- 2.4–3.0 mm general walls
- 5–7 mm effective structural ribs/gussets
- generous 3–6 mm internal fillets
- large lightening windows away from load paths
- ladder/spine floor instead of solid floor
- locally thick M4 hardpoints
- no decorative solid mass

Primary load paths:

- receiver datum rail
- GPU bracket rail
- adjustable card supports
- far-end support sockets
- PSU strap hardpoints
- fan-wall transitions
- pod dock hardpoints

## Fasteners

Use the fastener matrix in `FASTENERS_AND_HARDPOINTS.md`.

Fan mounting must accept M4 × 30/35 machine screws with washer/nut after final stack is known. Do not model fan self-tapping screw threads.

M3 heat-set reference: RX-M3x5.7, nominal 4.0 mm printed insert hole before printer tuning.  
M4 heat-set reference: RX-M4x8.1, nominal 5.6 mm printed insert hole before tuning.

Structural M4 hardpoints should be through holes or captive-nut geometry whenever possible.

## Receiver tray

Create three receiver zones. Each should support a universal slotted M3-standoff mounting approach. Use slots approximately 3.6–4.0 mm wide × 20–30 mm long until vendor CAD is imported. Provide underside nut/washer access.

ADT official CAD URL is in `vendor_cad/README.md`.

## Cable management

Model separate channels:

- Signal: >=28 × 16 mm common OCuLink raceway
- Power: target >=28 × 20 mm per GPU in service region
- Control: >=14 × 10 mm

Keep 25–40 mm straight/service distance after each OCuLink connector before the first clamp. All raceway edges touching cable get >=1.5 mm radius. Use M3-insert service covers, not snap-only lids.

Provide permanent embossed/recessed labels: GPU-A/B/C, LINK-A/B/C, PWR-A/B/C, FAN-1/2.

## PSU

Parameterize PSU dimensions. Current reference Corsair RM1000x = 160 × 150 × 86 mm. The PSU may physically overhang beneath/rear of the printed body. The **printed chassis is still one piece**; the PSU is attached after printing using metal straps and M4 hardpoints.

Preserve PSU fan intake, exhaust, AC switch/inlet and modular cable panel clearance.

## Expansion panel

Standardize:

- 4 × M4 hardpoints on 80 × 60 mm pattern
- central removable 42 × 30 mm blank
- 2 × M3 insert points for future connector plate
- flat mating datum for metal bridge plate

Do not design a passive PCIe daisy-chain. This interface is mechanical/control/future-active-fabric only.

## Print optimization

The production material is one continuous 5 kg spool of plain PETG. Preferred print mass <=3.0 kg, hard ceiling <=4.0 kg including brim/support.

Design for 0.6 mm nozzle / ~0.28 mm layer. Minimize support by orientation, chamfers and self-supporting ribs.

Provide named modifier meshes or a clear diagram for local infill:

- shell 12–15%
- receiver rail/card rail 40–60%
- fan bosses 30–40%
- PSU/dock structural anchors 70–100%
- cable covers 0–10%

Do not use global 50–100% infill as a substitute for structural geometry.

## Deliverables

Produce:

1. `JEH_3GPU_POD_v2.blend`
2. parametric dimensions in named Blender custom properties or a text block
3. max-envelope GPU placeholders and RTX3060 validation placeholders
4. F9Q receiver placeholder, later replaced by imported official CAD
5. exploded assembly view
6. airflow section view
7. cable-routing section view
8. hardpoint/fastener section view
9. print-orientation view
10. reported bounding box
11. mesh volume
12. estimated PETG mass using 1.27 g/cm^3 as a planning density only; slicer mass remains authoritative
13. list of unresolved dimensions and assumptions

Do not produce a “final” STL until the release gates in `VALIDATION_CHECKLIST.md` are closed.

