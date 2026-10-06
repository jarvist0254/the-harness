# Validation and Test Plan

## Gate 1 — CAD

Pass when:
- core fits 205 × 205 × 250mm box
- all three 3060 validation dummies fit
- universal 60mm-thick / 155mm-high dummy sweep checked
- every fastener has tool access
- every heat-set insert has installation access
- cable bend/service volumes exist
- fan blades have guard and clearance
- rear exhaust open

## Gate 2 — slicer

Pass when:
- no unsupported impossible geometry
- estimated total consumption ≤4.3kg hard limit
- preferred ≤2.8kg
- print can complete without spool swap
- print time accepted by owner
- no support structures trapped inside closed ducts

## Gate 3 — coupon

Print and test:
- M3 insert pocket
- M4 insert pocket
- board slot
- representative rib

Record actual dimensions and update parameters.

## Gate 4 — empty chassis load

Before electronics:
- install all inserts
- torque representative M3/M4 fasteners gently to consistent hand-tool torque
- mount dummy masses or sandbags approximating 3 × 2kg GPUs
- hold 24h
- inspect creep/cracks/layer separation

## Gate 5 — fans / airflow

- run fans alone for 2h
- verify no resonance/fan blade interference
- check plenum leaks
- measure approximate airflow in all four lanes
- adjust baffles if one lane starves

## Gate 6 — electronics one card

- install one receiver + one GPU
- cold boot repeatedly
- validate link width/speed
- run sustained compute
- log GPU, receiver, intake and PETG-support temperature

## Gate 7 — two cards

Repeat enumeration/thermal/load tests with two simultaneous workers.

## Gate 8 — three cards

- repeated cold boots
- all three independent workers
- simultaneous sustained load
- J-Link scheduling
- temperature map
- power-at-wall logging
- check cable/connector temperatures
- inspect chassis creep after cooldown

## Thermal stop rules

Immediate stop for:
- melting odor from printed chassis
- visible sag at receiver or GPU support
- loose heat-set insert
- browning/discoloration near power connector
- hot modular PSU cable/connector beyond expected warm touch
- PCIe errors/link drops correlated with heat

Project PETG structural investigation threshold: 45°C.
Project PETG structural stop/rework threshold: ~50°C sustained at a load-bearing printed feature.

If PETG fails thermal/creep gates, do not simply add infill. Re-evaluate airflow, move hot contact points, add metal load path, or migrate the structural core to a higher-temperature material such as PA6-GF25.
