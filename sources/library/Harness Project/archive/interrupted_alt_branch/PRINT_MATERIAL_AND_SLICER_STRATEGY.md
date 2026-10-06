# Print Material and One-Spool Strategy

## Material decision

### Primary recommendation: one 5kg spool of high-speed PETG

For this particular project, **large-spool PETG is the best cost/risk balance**.

Why:
- The Ender-3 S1 Pro can print PETG comfortably.
- A 5kg single spool satisfies the no-mid-print-spool-change requirement.
- PETG has strong layer adhesion and impact tolerance.
- It avoids the enclosure/warping risk of a near-full-bed ASA print.
- It avoids the drying, abrasive-nozzle, moisture and higher-cost burden of glass/carbon-filled nylon for a giant one-piece part.

Current reference: SUNLU Large Spool 5KG High Speed PETG 1.75mm, black. Price tracking on 2026-09-25 showed about **$50.39** on Amazon. ASIN: **B0FGPBSS1N**.

This is the production baseline unless thermal qualification proves PETG inadequate.

### Premium fallback: PA6-GF25

Polymaker/Fiberon PA6-GF25 is substantially stiffer and more heat-resistant, but it requires:
- 280–300°C nozzle
- hardened/wear-resistant nozzle
- aggressive drying around 100°C
- dry feed during printing
- greater material cost
- tighter process discipline

It is appropriate if PETG support temperatures/creep fail validation, but it is not the cost-effective first choice for this huge one-piece chassis.

### Do not use PLA/PLA-CF

PLA-class materials are rejected for the main load-bearing chassis because heat resistance and creep margin around several GPUs are inadequate for this application.

## Large spool handling

A 5kg spool must **not** hang from the Ender gantry.

Use an external floor/bench spool roller rated for at least 6kg with ball bearings and a low-friction filament path. Feed through PTFE tubing only where bend radius is generous.

Before print:
- verify spool rotates with low starting torque
- verify full Z travel does not tug filament
- verify filament cannot jump off spool flange
- confirm runout sensor path does not create excess drag

## Nozzle

For normal PETG:
- 0.6mm brass or plated-copper M6/MK-compatible nozzle is preferred for this structural print.
- Keep at least one identical spare on hand.

Why 0.6mm:
- substantially reduces print time
- produces thicker, stronger road widths
- makes 2.4/3.0/3.6mm structural wall dimensions easy to express as integer perimeter counts

The S1 Pro's stock family uses an M6 nozzle; verify exact physical nozzle against the installed hotend before purchase.

## Mass target

The main chassis must finish from one 5kg spool with reserve.

CAD/slicer release gates:
- preferred chassis mass: **≤2.8kg**
- acceptable after engineering review: **≤3.5kg**
- hard one-spool project limit: **≤4.3kg including brim/support/waste**

The 4.3kg limit leaves ~700g reserve against a nominal 5kg spool. A model exceeding this is redesigned, not printed hoping the spool is overweight.

## Where to remove material

Aggressively remove material from:
- cosmetic side panels
- plenum broad surfaces
- cable-raceway covers
- empty floor areas
- top cover/guard areas
- spaces between structural beams
- non-contact GPU-guide surfaces

Use windows, ribs and thin shells rather than solid volume.

Do not use 40–50% infill across the entire model. That wastes kilograms without placing material efficiently.

## Where to reinforce

Put plastic where load enters the part:
- M4 carrier insert bosses
- front GPU bracket bulkhead
- rear cradle rail roots
- bottom feet / shelf contact patches
- PSU saddle junctions
- fan wall corners
- vertical spine-to-base corners
- PodLink coupling bosses

## Slicer baseline for 0.6mm nozzle

Starting point only; calibrate first.

General chassis:
- layer height: 0.28mm
- line width: ~0.66–0.72mm depending calibration
- perimeters: 4 in ordinary shell regions
- top/bottom: 5–6 layers where a closed skin exists
- infill: 12–15% gyroid or cubic

Structural modifier regions:
- perimeters: 6–8
- infill: 35–45% gyroid/cubic

Insert bosses / very local anchors:
- design enough walls that the boss is largely perimeter material
- optional 60–100% local modifier within ~8–12mm of the insert pocket

Plenum/baffle:
- 3–4 perimeters
- 0–10% infill if geometry is self-supporting

Large side guards:
- 3 perimeters
- 8–12% infill
- 55–70% geometric openings preferred over infill

## Print orientation

The monolithic body should be oriented so:
- bottom structural beams sit on the build plate
- GPU load primarily compresses vertical walls rather than peeling layer interfaces
- M4 insert bosses for carriers are oriented to resist pullout through wall thickness
- long cantilevers are avoided

## Preflight coupon

Before risking kilograms of material, print a small coupon containing:
- M3 insert pocket
- M4 insert pocket
- 3.6mm PCB slot
- 4.4mm / 5.0mm / 5.6mm clearance holes
- one representative structural rib

Tune only from measured coupon results, then freeze the CAD compensation values.
