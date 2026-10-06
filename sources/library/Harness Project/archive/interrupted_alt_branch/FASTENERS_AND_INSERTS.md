# Fasteners, Inserts and Clean Assembly Standard

## Rule zero

**No repeated-service machine screw may cut its own thread into printed plastic.**

Allowed retention methods:
- brass heat-set insert
- through-bolt + washer + nyloc nut
- captive square/hex nut pocket
- screw into the component's existing metal thread
- metal standoff fixed with nut/insert

Self-tapping screws are not part of the released design.

## Standardize on two metric sizes

### M3 — electronics / PCB / cable hardware
Use for:
- receiver-board sleds
- PCB standoffs
- small cable clamps
- sensor brackets
- light covers

Preferred insert family: CNC Kitchen/Ruthex-style **M3 standard, 5.7mm long, ~4.6mm OD**.

CAD starting pocket:
- bore: 4.0mm nominal
- depth: 6.7mm minimum for blind pocket
- entry chamfer: 0.5 × 45°
- boss OD: 9–11mm minimum depending surrounding load

Purchase the inserts first and measure actual OD/length with calipers before final CAD release.

Suggested M3 screw inventory:
- M3×6: 20
- M3×8: 30
- M3×10: 30
- M3×12: 30
- M3×16: 20
- M3×20: 12
- M3 flat washers: 100
- M3 nyloc nuts: 40

Use 304 stainless socket-head cap screws or black-oxide alloy steel. Do not mix random soft zinc hardware on structural points.

### M4 — structural / carrier / fan / pod coupling
Use for:
- GPU carrier attachment to chassis
- rear cradle outriggers
- fan frame through-bolts
- PSU restraint hardware
- PodLink mechanical coupling points

Preferred insert family: CNC Kitchen/Ruthex-style **M4 standard, 8.1mm long, ~6.3mm OD**.

CAD starting pocket:
- bore: 5.6mm nominal
- depth: 9.1mm minimum for blind pocket
- entry chamfer: 0.6 × 45°
- boss OD: 13–15mm minimum; larger on load-bearing beam junctions

Suggested M4 screw inventory:
- M4×10: 20
- M4×12: 30
- M4×16: 30
- M4×20: 24
- M4×25: 16
- M4×30: 12
- M4 flat washers: 100
- M4 nyloc nuts: 60

## Fan mounting

Preferred clean method:
- 8 × M4 machine screws total for two fans
- silicone fan corner pads or thin rubber washers
- M4 through-holes in the printed fan wall
- M4 washers + nyloc nuts, or M4 heat-set inserts in reinforced bosses

Through-bolts are preferred if rear access remains available because they impose less heat-set pullout risk.

## GPU I/O bracket retention

Do not rely on the PCIe receiver socket alone.

Each GPU gets:
- one metal I/O-bracket clamp/rail
- two M3 screw points if bracket geometry permits, or one primary M3 + anti-rotation feature
- screws terminate in M3 heat-set inserts or a metal threaded strip/captive nut

Astra should model slotted 3.5–4.0mm clearance features so bracket variation can be absorbed.

## PCB / receiver-board mounting

Because the exact receiver PCB is not frozen, do not drill a fixed pattern into the monolithic body.

Use a removable universal sled:
- four longitudinal slots, 3.6–4.0mm wide
- slot length: 35–50mm
- board attaches with M3 standoffs + washers/nuts
- sled attaches to chassis with four M4 screws into heat-set inserts

If the selected board uses M2.5 holes, use M2.5 metal standoffs through the sled slots; do not enlarge the PCB hole.

## PSU retention

If the chosen ATX PSU exposes standard rear 6-32 threaded mounting holes, screws may pass through printed clearance holes into the PSU's metal threads. Do not cut a 6-32 thread into PETG.

Use four OEM-compatible PSU screws of correct length only. Add a separate nonconductive strap/stop so the PSU mass is supported by the saddle, not hanging from the four rear screws.

## Insert installation

Install inserts only after the print fully cools.
- Use a temperature-controlled soldering iron and insertion tip.
- Insert square to the surface.
- Stop slightly proud, then use a flat metal block while plastic is soft to make flush.
- Never install inserts with electronics mounted nearby.
- Pull-test sacrificial coupon before the main chassis.
