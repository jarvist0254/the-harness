# Four-Position Monolithic Harness — Mechanical Baseline

## Exact candidate card envelope

Current purchase candidate: MSI GeForce RTX 3060 Ventus 2X 12G OC.

Manufacturer specifications:

- 235 mm length
- 124 mm height
- 42 mm thickness
- 675 g card mass
- 170 W board power
- 1 × 8-pin auxiliary power

The Newegg candidate is the **Ventus 2X**, not the longer Ventus 3X.

## Printer constraint

Ender-3 S1 Pro nominal build volume:

- 220 mm X
- 220 mm Y
- 270 mm Z

Current intent: one continuous chassis print rather than a bolted multi-part frame. GPU and PSU bodies may extend outside the printed chassis envelope; the printed body provides the bank structure, air plenum, restraints, guides and PSU saddle.

## Preferred monolithic envelope

Use as the Blender starting bounding box:

- **188 mm X**
- **188 mm Y**
- **248 mm Z nominal**
- allowed Z tuning range: 245–250 mm

This fits the nominal printer volume with approximately:

- 32 mm X margin
- 32 mm Y margin
- 20–25 mm Z margin

Do not consume all margins with decorative walls; reserve bed margin for brim/adhesion and slicer tolerances.

## Four-card stack geometry

Use the 42 mm card thickness as the hard datum.

Suggested starting stack:

- card thickness: 42 mm
- forced-air channel between adjacent cards: **16 mm nominal**
- card-to-card pitch: **58 mm nominal**
- four cards + three 16 mm channels: **216 mm**

A 248 mm chassis height leaves roughly 32 mm total for top/bottom structural margins, guides and plenum transitions. Treat 15–18 mm as the adjustable air-gap range; 18 mm everywhere may become tight once wall thickness and retainers are included.

The empty fourth position in Phase 1 gets a removable printed blank/air dam so the fan wall does not dump pressure through the empty bay.

## Length and overhang

The 3060 is 235 mm long while the baseline chassis depth is 188 mm. Therefore the GPU body will overhang approximately **47 mm** before adding cable/connector service clearance. This is intentional.

Provide:

- rigid support close to the I/O bracket/PCIe receiver
- a second support under a verified safe shroud/backplate contact patch
- no support pressure on exposed PCB components or fan blades
- cable strain relief independent of the PCIe edge connector

Operational shelf depth must include GPU overhang plus power-cable bend radius.

## Fan wall / plenum

Baseline:

- two 120 mm fans stacked vertically
- common intake plenum feeding all card channels
- rear/side exhaust kept substantially open
- fan wall integrated into chassis rather than separate printed bracket

Two 120 mm fans naturally occupy about 240 mm in the long axis, matching the 245–250 mm chassis Z target. Use ribs around fan screw bosses instead of thickening the entire wall.

## PSU saddle

External PSU remains a separate enclosed ATX PSU. The printed chassis may integrate its saddle/locators but must not replace or open the PSU enclosure.

Final PSU geometry is TBD until exact PSU SKU is selected/measured. Keep the saddle parametric in Blender for:

- width
- body depth
- body height
- fan intake clearance
- AC inlet/switch clearance
- modular connector/cable projection

The PSU may overhang the printed skeleton if fully supported and restrained.

## Material-efficiency rules for Blender

Goal: structural stiffness without turning the whole object into a solid block.

Use:

- thin skins in low-load areas
- ribs/gussets around GPU rail junctions, fan bosses and PSU saddles
- large lightening windows between load paths
- locally thickened screw/insert bosses
- generous radii at inside corners
- no unnecessary solid floor under open-air electronics
- no long unsupported thin cantilevers

Starting modeling dimensions, not final slicer settings:

- general wall: 3–4 mm
- high-load ribs/gussets: 5–7 mm effective section
- boss OD sized around chosen insert/through-bolt system
- minimum clearance around fan blades/cables: model explicitly, do not assume

Run Blender volume and slicer mass estimates before finalizing. The old ~12 lb material estimate is not accepted as a requirement; the objective is to remove unnecessary plastic while retaining stiffness.
