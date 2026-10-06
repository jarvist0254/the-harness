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
