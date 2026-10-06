# Print Engineering Specification

## Material

**Primary:** Polymaker Fiberon PA6-GF25, 1.75 mm, 3 kg spool.

Manufacturer-published guidance used by this project:

- nozzle: 280–300 °C
- bed: approximately 40–50 °C
- hardened / wear-resistant nozzle required
- fan off
- dry at 100 °C for ~10 h before printing
- maintain dry conditions during printing
- post-print annealing is recommended by manufacturer for peak properties

The exact final profile must be tuned with coupons on the user's S1 Pro. This document does not override the filament label/TDS.

## Nozzle

Default: **0.6 mm hardened steel** (or higher-wear-quality equivalent) compatible with the Sprite/S1 Pro hotend.

Why 0.6 mm:

- lower fiber-clog risk than a small nozzle
- faster for a very large structural print
- thick, predictable walls
- less toolpath count for the same section thickness

## Layer / extrusion starting point

Starting profile for Astra/slicer testing, not final G-code:

- layer height: 0.28–0.32 mm; start 0.30 mm
- line width: ~0.62–0.68 mm depending slicer/nozzle calibration
- cooling fan: off per material guidance, except any bridge-specific exception must be proven by coupon
- avoid high acceleration that shakes a 250+ mm tall engineering print
- brim: use only enough to make the footprint safe; include brim mass in one-spool budget

## One-spool mass gate

Hard requirement:

- single 3 kg spool
- no mid-print spool change
- preferred model + supports + brim ≤ **2.20 kg**
- hard release ceiling ≤ **2.45 kg**

If >2.45 kg:

1. remove cosmetic skins
2. enlarge lightening windows
3. convert flat walls to ribs + shell
4. reduce low-load infill
5. eliminate duplicate cable-channel walls
6. hollow oversized bosses outside the local solid insert zone
7. reduce plenum wall thickness where pressure loads are low
8. do **not** thin PodLink, receiver-deck mounts, GPU rail mounts, feet, or PSU saddle junctions first

## Strength strategy: walls and ribs before infill

Do not make the chassis strong by setting 50% infill everywhere. The efficient design is stiff shells, section depth, radiused ribs and local modifiers.

### Zone A — low-load shells / ducts

Examples: plenum skins, cable-channel lids, cosmetic guards.

- wall target: ~2.4 mm (about 4 × 0.6-mm-class perimeters, slicer-dependent)
- infill: 0–12%
- use ribs where panel drum/flex is observed

### Zone B — general frame walls

- wall target: 3.0–3.6 mm
- 5–6 perimeters
- infill: ~15–25% gyroid/cubic
- generous corner radii

### Zone C — GPU rail / receiver-deck / PSU saddle junctions

- 6–8 perimeters
- local infill: 35–50%
- triangular/radiused gussets
- avoid abrupt section changes

### Zone D — inserts / through-bolt hardpoints

- boss dimensions from fastener document
- local modifier: **100% infill** within the boss / load-spread region
- 6–8+ surrounding walls where possible
- washer land must be flat and thick enough not to crush

### Zone E — feet and PodLink

- 8+ perimeters
- 50–70% local infill or effectively solid ribbed section
- through-bolt load spread over large washer / metal plate

## Material sacrifice map

**Aggressively remove material from:**

- broad side panels
- center of PSU bay floor
- regions directly under the aluminum receiver deck that are not support ribs
- decorative roof
- rear wall (keep open for exhaust)
- duplicate wall behind a cable channel
- plenum surfaces far from fan screw bosses

**Do not sacrifice:**

- four corners of the base
- foot towers
- receiver-deck mount towers
- GPU bracket rail anchors
- card-support cradle roots
- fan boss rings
- PSU saddle stops
- PodLink interface
- tail-support interface

## Geometric anti-warp strategy

Large GF-nylon print rules for the CAD:

- avoid giant continuous flat floors; use rails + webs
- use rounded corners instead of sharp rectangular stress concentrators
- include expansion-friendly windows in long walls
- keep major wall thickness reasonably uniform
- avoid massive solid blocks next to thin skins
- orient ribs so contraction does not pull one corner off the bed

## Supports

Design the chassis to minimize slicer-generated support. Every kilogram of support is wasted one-spool budget.

Astra should favor:

- 45° self-supporting chamfers
- teardrop/diamond cable holes rather than horizontal circles where appropriate
- underside ribs with printable draft
- captive-nut pockets accessible after printing, not sealed mid-print

## Insert installation and annealing order

Preferred sequence:

1. print coupons
2. full chassis print
3. dimensional inspection
4. post-print anneal only after shrink/warp compensation has been validated on coupons
5. allow full cool-down
6. heat-set brass inserts
7. install metal plates/hardware

Do not anneal with PCBs, fans, PSU, cable ties, rubber feet or inserts already installed unless the component vendor explicitly permits it.

## Dryer / anneal fit note

SUNLU E2 published internal envelope is large enough on paper for roughly 206 × 186 × 262 mm chassis **if the chassis is rotated** (262 into the long chamber dimension, 206 into ~255 mm, 186 into ~192 mm). This is a tight fit. Astra should keep the true outer envelope at or below the stated design dimensions and avoid protruding cosmetic tabs that destroy this fit.

