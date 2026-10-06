# Airflow, Plenum and Cable Channel Specification

## 1. Cooling objective

Feed each GPU with room-temperature intake air without forcing one GPU to ingest another GPU’s exhaust. The chassis assists the card coolers; it does not replace them.

## 2. Fan wall

Target fans: 2 × ARCTIC P12 Max, 120 × 120 × 25 mm, side-by-side.

Published fan characteristics:

- 400–3300 rpm PWM
- 81.04 CFM maximum airflow
- 4.35 mm H2O static pressure
- 12 V
- 0.29 A
- 4-pin PWM

Astra should use the manufacturer’s 120 mm mounting-hole drawing / P12 Max 2D drawing as the CAD authority.

## 3. Intake plenum

Provide a **25–35 mm deep common pressure-equalization plenum** behind the two fans before hard flow dividers begin.

Design details:

- rounded fan-to-plenum transitions
- no square dead corners if avoidable
- 3–5 mm radii at divider roots
- removable fan guard outside
- 2.4–3 mm walls in low-load plenum areas
- structural ribs around fan bosses rather than thick solid panels

## 4. GPU air channels

At the declared max card thickness of 68 mm:

- AB clear gap: >=12 mm
- BC clear gap: >=12 mm
- outer card faces should retain additional intake space to chassis wall wherever geometry allows

For the initial 42 mm 3060 cards, use adjustable shoes to bias the cards so the fan intake faces see **roughly 20–25 mm or more** of clear local intake space instead of simply centering all cards.

Do not let:

- OCuLink cables
- 8-pin PCIe cables
- 12V-2x6 cables
- cable combs
- receiver switches
- sensor wires

consume the 12 mm max-envelope minimum channel.

## 5. Cable zones

### Zone S — high-speed signal

Purpose: OCuLink cables from host breakout to three receivers.

Starting internal clear section: **28 × 16 mm common raceway minimum**, preferably divided or provided with individual clips.

Rules:

- maintain cable manufacturer bend radius
- no hard 90° kink at SFF-8611/8612 connector
- provide 25–40 mm straight/service zone immediately behind each connector before first restraint
- strain relief clamps the cable jacket, never the connector body
- route away from GPU fan blades and sharp printed edges
- route separately from high-current GPU cable bundles when practical

### Zone P — GPU power

Purpose: one or more native PSU GPU leads per bay.

Starting allocation per bay: **28 × 20 mm** clear routing corridor, with an open-top or removable-cover section near the GPU so different connector positions are accommodated.

Rules:

- no forced bend directly at 8-pin/12V-2x6 connector
- preserve connector latch access
- provide a broad top/rear “power service zone” instead of a fixed connector hole
- do not bind three GPU leads into one immovable bundle before they reach the cards
- each bay receives independent labeled strain relief: PWR-A, PWR-B, PWR-C

### Zone C — control/fans/telemetry

Starting clear section: **14 × 10 mm**.

Carries:

- two fan PWM leads
- optional fan hub lead
- USB/control cable
- temperature probes
- optional Ethernet/control link for future pod controller

Do not put GPU auxiliary power into this channel.

## 6. Raceways and covers

Use snap geometry only as a locating feature; use M3 heat-set inserts + machine screws for serviceable covers.

Preferred cover spacing:

- M3 fastener every 80–120 mm on long covers
- no more fasteners than needed to prevent buzz/rattle
- slots/windows every 30–50 mm where safe to cut material

Cable edges need >=1.5 mm radius or a grommet. No raw sharp slot edges against OCuLink jackets.

## 7. Cable labels

Both ends of every removable cable should carry permanent pod/bay labels:

- POD-1 / GPU-A / LINK-A
- POD-1 / GPU-B / LINK-B
- POD-1 / GPU-C / LINK-C
- PWR-A / PWR-B / PWR-C
- FAN-1 / FAN-2

J-Link software should use the same A/B/C bay naming where possible.

## 8. Serviceability

A card must be removable without disassembling the other two cards.

Target sequence:

1. power down host and pod,
2. disconnect AC,
3. release that bay’s power cable restraint,
4. disconnect OCuLink at the receiver only as required,
5. release GPU bracket clamp,
6. release adjustable side/tail support,
7. remove card vertically/rearward without crossing adjacent power cables.

If the CAD cannot satisfy this sequence, cable management is too tight.

## 9. Thermal instrumentation

Provide M3 insert sites for optional thermistors/probes at:

- intake plenum center
- between A/B near GPU intake height
- between B/C near GPU intake height
- receiver-board zone
- PSU-adjacent printed hardpoint

The sensors are optional; their mounts should not block airflow when unused.
