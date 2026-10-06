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
