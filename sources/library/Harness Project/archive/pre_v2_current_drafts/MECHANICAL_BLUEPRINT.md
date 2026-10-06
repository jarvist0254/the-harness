# Mechanical Blueprint — Universal Three-GPU Pod

## Coordinate system

- **X:** left-to-right across the three GPU slot planes
- **Y:** front fan/plenum toward GPU rear overhang
- **Z:** bottom feet upward

Starting printed envelope: **206 X × 186 Y × 262 Z mm**.

This is the outer design envelope for Astra, not a solid body. Use open-frame construction with ribs, windows and ducts.

## Cross-section / stack concept

### X axis — three card bays

Target slot-plane pitch: **68 mm**.

Nominal centers (starting values, parametric):

- Bay A: X ≈ 35 mm
- Bay B: X ≈ 103 mm
- Bay C: X ≈ 171 mm

These values leave approximately 7 mm structural margin on each side of a symmetric 56 mm body envelope. Real coolers are not symmetric about the PCIe slot plane, so the receiver carrier must permit several millimetres of X adjustment before final lock-down.

At 56 mm card thickness:

- adjacent nominal clearance ≈12 mm

At the first 42 mm card thickness:

- adjacent nominal clearance ≈26 mm

The design must preserve the **fan-side intake path** for every card. Do not center a card merely for visual symmetry if that moves its cooler fan face against a wall.

## Y axis — support and intentional overhang

Printed depth target: **186 mm**.

Cards may be longer than the chassis. This is deliberate.

Required supports:

1. metal I/O bracket rail at the bracket datum
2. receiver x16 slot / metal receiver deck
3. adjustable mid-card lower support at a verified shroud/backplate-safe contact patch
4. optional tail-support bridge for long/heavy cards

Do not support:

- exposed PCB components
- fan blades
- heatsink fins
- power connectors
- thin decorative plastic that can flex into a fan

### Length envelope

- base pod: accommodate cards through at least 270 mm without a tail extension
- extended: up to 340 mm using the removable tail-support bridge anchored to the existing chassis

A long GPU may protrude >150 mm beyond the printed Y envelope. Tail support must prevent a heavy card from turning the receiver connector into a cantilever.

## Z axis — PSU + receiver deck + GPU

The pod is vertically stratified.

Starting concept:

- Z 0–12 mm: feet / inlet clearance / structural floor ribs, mostly open
- Z ~12–98 mm: ATX PSU saddle zone (exact depends on selected PSU; reference ATX PSU height 86 mm)
- Z ~98–110 mm: isolation / airflow / metal-deck support zone
- Z ~110 mm: metal receiver deck plane
- Z ~110–262 mm: GPU body region / bracket / top cable clearance

A 155 mm-tall GPU may extend a few millimetres beyond a printed top rail if necessary; the print is a support chassis, not a cosmetic full enclosure.

## Receiver deck

Use a removable **1.5–2.0 mm aluminum deck plate** spanning the receiver area. Starting plate envelope ~190 × 155 mm, final size after PSU and wall clearance are settled.

Functions:

- carries the three receiver boards on standoffs
- spreads GPU connector load
- allows receiver mounting-hole revisions without reprinting the chassis
- shields the printed structure from concentrated standoff loads
- provides a clean cable tie / P-clamp substrate

The plate bolts to the printed body with M5 through-bolts or M5 metal-thread interfaces. PCB standoffs attach to the plate, not to printed plastic.

## GPU I/O bracket rail

Use a removable aluminum/steel rail, e.g. ~20 × 20 × 2 mm angle or purpose-cut flat/formed bracket.

- use standard #6-32 UNC GPU bracket screws
- provide two screw positions per bay when the GPU bracket supports them
- use tapped metal, PEM/captive nuts, rivnuts, or replaceable metal nut strip
- do not form #6-32 threads in the printed chassis

The rail bolts into the chassis through metal-threaded interfaces / through-bolts.

## PSU saddle

The PSU remains fully enclosed. Never open or structurally modify it.

Chassis provides:

- supported base rails
- positive fore/aft stops
- vibration isolation pads
- access to AC inlet, switch and modular cable panel
- full fan inlet opening
- removable metal rear/retention plate matched to the exact PSU

Do not use long generic screws into PSU holes. Use only correct manufacturer-compatible screw length and pattern once PSU is selected.

## Tail bridge

The tail bridge is an accessory, not part of the principal load-bearing body. It may be a short printed/metal assembly attached to predesigned M5 interfaces.

Requirements:

- longitudinal adjustment for 235–340 mm cards
- vertical adjustment for different backplate heights
- padded contact block
- no clamp force on heatsink fins or PCB components
- removable without disturbing receiver boards

## Material-removal geometry

Use windows rather than thick slabs.

Good places to remove plastic:

- center of large side faces
- under receiver deck except ribs / mounting towers
- PSU saddle floor outside contact rails
- decorative top surfaces
- cable-channel backs where the chassis wall already supplies one side
- plenum walls away from fasteners

Keep plastic at:

- fan frame junctions
- GPU bracket-rail mounts
- receiver-deck mounts
- feet
- PSU stop/saddle junctions
- PodLink docking hardpoints
- tail-bridge hardpoints
- all inside corners that transfer load; use radiused gussets

