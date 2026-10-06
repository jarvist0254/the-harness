# Integrated four-card core

`integrated_core.py` jointly lays out A–C upright and D rolled above them, then builds one connected FreeCAD support core. GPU overhang is allowed. D uses the same continuous core's posts and beams; it is not an appended fourth module.

The current revision-4 compact card boxes are hypothetical 199 × 116 × 40 mm envelopes. Their saved BRep is one valid solid, 188 × 200 × 150 mm. The 360 × 165 × 68 mm large-envelope fixture also has one valid solid, 188 × 200 × 199 mm. Conservative print poses are 200 × 188 × 150 mm and 200 × 188 × 199 mm. Both fixtures have zero positive-volume body interference with the core and the two nominal metal rails. Neither establishes purchased-card fit.

Four 10 mm posts sit in the two 12 mm gaps between A–C, with 1 mm nominal body clearance on each side. Front and rear posts end at the underside of D's integral metal-rail support, below D's body. The GPU poses and nominal clipped shoes are preserved. Print height follows the actual beam top; it is not artificially clamped to the printer height. GPU overhang is explicitly excluded from the printed envelope.

Inspect [the current preview](../records/cad_draft_20261004/integrated_tetris_revision4_actual_brep.png), generated from actual saved revision-4 FreeCAD shapes. Editable FCStd files and STEP exports are in `compact_revision4` and `universal_revision4`. Each native gate checked 16 post/card, 8 metal/card and 4 full-core/card intersections. Source-specific evidence is in `native_build_revision4_runs.json`, `preview_export_revision4_receipt.json`, and `../records/root_continuation_20261004/cad_revision4_promotion.json`. The saved previews and source from earlier revisions are retained: revision 2/3 large cards each intersected A/C posts by 33,000 mm³. Their old PNG is historical, not the current layout.

The planner refuses negative/zero primitive sizes, beams intruding through the lower bodies, cards missing either nominal front/rear support footprint, and cards completely outside their integral shoe footprint. Nominal body overlap does not identify a safe GPU contact patch or establish load capacity. Actual BRep validation also checks one solid, real bounding dimensions and positive-volume card interference.

```powershell
python -B -m unittest discover -s cad/tests -v
```

To build, use the existing local FreeCAD command-line executable with a Python wrapper that imports `build` and `default_config`, supplies an explicit fresh output directory, and records source hashes and state. `build()` refuses a populated output directory. A FreeCAD process exit code alone is insufficient: this application can print a Python exception and still exit zero. Require a fresh valid state file and inspect the actual geometry.

Receiver datums, safe support contacts, D load paths, GPU mass/overhang moments, PSU mounting, cable bends, fan plenum, intake/removal sweeps, print bridging/supports, brim, slicer mass, PETG load coupons and thermal tests remain unqualified. The simple crossbeams require a verified print/support strategy. No production STL is released.
