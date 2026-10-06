# Airflow and Channel Design

## Cooling objective

Provide cool room air to the intake faces of all three GPU coolers without forcing each card to ingest the exhaust of the preceding card.

## Fan wall

Reference fan: ARCTIC P12 Max or equivalent 120 × 120 × 25mm high-static-pressure PWM fan.

Design for **two 120mm fans stacked vertically** on the front face.

Fan geometry:
- fan body: 120 × 120 × 25mm
- mounting-hole pattern: use the selected fan manufacturer's drawing; common 120mm PC fans use ~105mm hole spacing.
- mount with machine screws/isolators/metal threads, not self-tapping fan screws into the printed wall.

The dual-fan vertical arrangement fits the printer Z envelope better than two fans side-by-side.

## Pressure plenum

The fan throat is narrower than the three-card bank. Use an expanding plenum.

Starting geometry:
- fan plane at Y = 0
- plenum depth: 35–50mm
- inlet throat width: ~120mm
- outlet width: approximately the active GPU-bank width
- outlet height: cover the useful vertical span of the GPU fan intakes
- expansion walls should use smooth curvature or ≤15° local diffuser angle where practical to reduce separation

Do not fill the plenum with thick material. Air pressure is low; stiffness comes from ribs.

Plenum wall:
- 1.8–2.4mm shell
- ribs every 35–50mm
- thicker only at fan bosses and structural junctions

## Air lanes

Model four airflow lanes across X:
1. outer-left lane
2. A/B inter-card lane
3. B/C inter-card lane
4. outer-right lane

Minimum lane target at the GPU fan-intake region:
- absolute minimum: 12mm
- design minimum: 15mm
- preferred: 18–25mm

The outer lanes can use open side windows and do not need full printed ducts.

## Flow straighteners / baffles

At the plenum outlet, use thin vanes that guide air into the four lanes.

Starting vane geometry:
- thickness: 1.6–2.0mm
- length in Y: 35–60mm
- rounded leading edges
- no sharp 90° flow turns
- terminate before the GPU's own axial fans so the vane does not become an intake obstruction

Vanes are low-load parts: use shell thickness, not high infill.

## Exhaust

The rear of the pod must stay open.

Do not print a closed rear wall behind the GPU heatsinks. Provide:
- unrestricted rear discharge
- cable paths above/below the main exhaust stream
- at least 25mm free space from the rear edge of the printed core to a wall/furniture obstruction; more if GPU bodies extend substantially behind the core

## Thermal sensors

Reserve clip/insert locations for at least four thermistors or digital sensors:
- intake air
- center inter-card lane
- warmest receiver board/sled
- structural PETG near the hottest GPU support

During qualification, investigate if PETG structural locations exceed 45°C and stop/rework if they approach 50°C under sustained load. This is a conservative project limit to control creep risk, not a claimed PETG decomposition limit.
