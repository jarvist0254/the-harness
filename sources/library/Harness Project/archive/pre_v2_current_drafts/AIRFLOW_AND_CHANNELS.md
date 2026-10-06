# Airflow and Channel Blueprint

## Cooling philosophy

The GPU coolers remain primary. The pod fans do **not** replace the axial fans on the graphics cards. Their job is to guarantee that each GPU fan face receives fresh room air and that hot exhaust does not stagnate between tightly spaced cards.

For this reason the pod uses a pressure plenum feeding longitudinal card channels rather than simply putting a giant fan somewhere near the chassis.

## Fan choice

Reference: **2 × ARCTIC P9 Max, 92 × 92 × 25 mm, 12 V PWM**.

Published per-fan performance:

- up to 58.25 CFM
- up to 6.17 mmH2O static pressure
- 450–4300 RPM PWM
- 0.34 A at 12 V
- 82.5 mm mounting-hole spacing

Two 92 mm fans fit side-by-side across a ~206 mm front width (184 mm fan-frame span) and can be placed at the GPU intake elevation instead of wasting a lower 120 mm fan on the PSU bay.

Astra must model standard 92 mm fan envelopes and 82.5 mm mounting-hole square pattern. Use M4 through-bolts, not self-tapping fan screws into plastic.

## Front plenum

Starting geometry:

- fan wall at front Y
- fan frame span: 184 mm wide, centered in the 206 mm chassis
- fan thickness: 25 mm
- pressure-plenum depth behind fans: **28–35 mm**, start at 32 mm
- large corner radii / gradual transitions; avoid abrupt 90° dead pockets
- no honeycomb grill directly against the fan; if a safety grill is used, keep it open-area dominant

The plenum terminates into **three card-intake channels**, A/B/C.

## Card intake channels

The channels run roughly in +Y along the cooler fan face of each installed GPU.

Target rules:

- Bay pitch: 68 mm nominal
- current 42 mm card: ~26 mm nominal intercard channel
- max-envelope 56 mm card: ~12 mm nominal intercard channel
- **12 mm is the minimum design throat**, not the preferred operating gap
- the first-card outer intake channel must not be eliminated by a side wall
- leave the outermost opposite side substantially open for exhaust / room-air exchange

Do not create sealed ducts that contact GPU shrouds. Maintain manufacturing / vibration clearance.

## Plenum splitters

Use two smooth splitter vanes to form three outlet zones. Splitters should:

- begin downstream of the fan blades, not directly against the hub
- use rounded leading edges
- taper gradually toward each channel
- be thin shell/rib structures, not solid wedges
- be parametric because actual GPU fan-face position varies by card

Initial flow allocation for three equal cards: approximately one-third outlet area per bay. J-Link/thermal validation may later justify different vanes if the center bay runs hotter.

## Middle-card priority

The center GPU is the highest-risk thermal position because it has neighboring cards on both sides. The design must permit:

- slightly enlarged center channel if receiver spacing permits
- center-biased splitter adjustment
- temperature probe near center-bay intake
- independent fan PWM increase when center bay is hottest

## Exhaust

Do not build a closed rear box. GPU exhaust and plenum air must leave with low resistance.

Keep open:

- rear overhang region
- top around card power connectors
- opposite side of the card bank

Use guards only where needed for fingers/cables. High open-area mesh is acceptable. Decorative perforation patterns with low free area are not.

## PSU airflow

The ATX PSU uses its own fan. The chassis must provide its fan face with a full-size opening and at least ~12 mm external clearance to the shelf/furniture, preferably more.

Do not deliberately feed hot GPU exhaust into the PSU intake.

## Thermal validation targets

No published GPU temperature target is hard-coded into the print. Validation must log:

- room ambient
- Bay A/B/C GPU temperature and hotspot if available
- VRAM temperature if exposed by driver
- receiver-board temperature / touch-safe hotspot survey
- PSU exhaust temperature trend
- printed-structure surface temperature at receiver deck, fan mounts and GPU support cradles

Test conditions:

1. one GPU load
2. two simultaneous GPU loads
3. all three GPUs sustained
4. reduced fan speed
5. maximum fan speed

The center bay must not exhibit runaway temperature relative to the outer bays.

