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
