# Harness master update

The complete recovered details are in `RECOVERED_CURRENT_COMPLETE.md`; this document provides the reconciled design and additional engineering issues exposed by the software research.

## Mechanical baseline

User-confirmed requirement: **Integrated core; GPU overhang allowed.** Repack all four independently serviceable external bays A–D into one continuous monolithic printed skeleton. Restructure the whole core around the four-card topology; do not append a fourth printed side module to the former three-bay body. Keep all printed bay-support mounts, PSU restraint and fan/plenum hardpoints within that one core. Removable covers, shoes, bolts, metal rails and electronics remain service parts. Another pod still needs a metal joining plate and a separately qualified compute transport.

Recorded printer: Ender-3 S1 Pro, nominal 220 x 220 x 270 mm. Conservative print bounding box: at most 200 x 188 x 254 mm. The recovered installed orientation is 254 W x 200 D x 188 H mm, but it is a starting orientation rather than a fixed prerequisite for Tetris packing. The solver must evaluate installed orientation and print rotation together: the same conservative print box could instead become, for example, 188 W x 200 D x 254 H or 200 W x 188 D x 254 H. Validate every selected rotation with support/brim, full carriage travel and load-direction checks. Printed pillars/rails themselves must stay within the print box; installed cards and outboard PSU may overhang.

The old three-bay width map was 3 x 68 + 2 x 12 + 2 x 13 = 254 mm. Four parallel equal bay allocations require W = 4 t + 62 mm, so a fully contained parallel 68 mm population needs 334 mm. The algebraic 48 mm limit at W=254 applies only to that specific contained parallel arrangement; it is not the new design requirement or a card-selection cap. Retain the original 35–68 mm, 165 mm height and 360 mm length target as a separate universal packing study, alongside actual compact cards. An 8 GB memory specification says nothing about cooler dimensions.

No packing study below establishes a complete chassis fit. Unknown receiver, clamp, base/roof, cable and PSU envelopes can invalidate a promising card-box arrangement. The integrated four-card layout is pre-CAD; no final fit, CAD or production STL is released.

## Integrated Tetris packing studies

Use L x h x t = 199 x 116 x 40 mm for the actual GIGABYTE GV-N5050WF2OC-8GD, and 360 x 165 x 68 mm for the original universal maximum. Bounds below include 13 mm outer margins across the stated pack-width axis and 12 mm gaps where shown. They exclude base/roof/support thickness, receivers, power/signal connectors and bends, PSU, fans/plenum and removal/tool volumes. They are GPU-only packing arithmetic, not production collision results.

| Candidate | Compact 5050 pack W x D x H, mm | Universal maximum pack W x D x H, mm | Consequence for recovered 254 x 200 x 188 core |
|---|---|---|---|
| Four parallel upright |222 x 199 x 116; W=4 t+36+26 |334 x 360 x 165 | Compact GPU-only fit; universal width extends 80 mm. Retain as comparison, not the sole design |
| **Three upright + one rolled 90 degrees about its length, above** |170 x 199 x 168; W=3 t+24+26, H=h+12+t |254 x 360 x 245 | Compact GPU-only fit leaves 84 W/1 D/20 H before unknown interfaces. Universal extends 160 D and 57 H; overhang is allowed but integrated supports remain unqualified |
| Two upright columns x two upright tiers |118 x 199 x 244; W=2 t+12+26, H=2 h+12 |174 x 360 x 342 | Height exceeds recovered core by 56/154 mm. Two 165 mm layers do not fit 188 H |
| Two flat columns x two flat tiers |270 x 199 x 92; W=2 h+12+26, H=2 t+12 |368 x 360 x 148 | Width exceeds recovered core by 16/114 mm. Turning long axis across W trades width for depth: compact 199 W x 270 D x 92 H with margins on D |
| Two lanes, two opposed cards per lane |118 x 410 x 116; D=2 L+12 |174 x 732 x 165 | Central integrated support with front/rear projection; center receivers/service space can require greater D. Large stability and access burden |
| Four upright 90-degree pinwheel, conservative square arrangement |277 x 277 x 116; square side=L+t+12+26 |466 x 466 x 165 | Orthogonal rotation alone is not a contained fit; installed overhang and support poses must be solved |

Prioritize the three-upright-plus-one-flat topology in the parametric search. Card D needs the core's own reinforced pillars/crossmembers and a qualified metal support rail where required. It must never rest on cards A–C, their shrouds/fans, or the PCIe connector. Rotate D's receiver/bracket datum 90 degrees with the card. Model independent removal of every card, including whether lower cards can exit without removing D. Its intake/exhaust direction and the clear 12 mm gap are hard constraints.

For the universal 3+1 pack, 245 H exceeds the recovered 188 H installed orientation. A tall installed orientation with 254 H leaves only 9 mm beyond the GPU-only 245 H before floor/roof/receiver allowances. Its 188 W or 200 W core is narrower than the 254 W lower pack: that pack would extend 66 mm or 54 mm in total, respectively (33/27 mm per side if centered). Card overhang is authorized; printable support footprints, receiver datums, bracket restraints and load paths within the narrower core are not yet proven. An upper support contact can be below the card's top, but its location cannot be invented from an outer box. No orientation alone proves this layout fits.

The two 120 mm fan frames require 240 mm across the recovered fan wall; a 170 mm compact GPU pack can still use a 254 W core. A narrower/taller core needs a re-solved fan placement, not an automatic reuse of that fan wall. If 25 mm fan thickness and 25–35 mm plenum lie serially ahead of a 199 mm card, their GPU/fan/plenum depth is 249–259 mm, requiring 49–59 mm installed rear projection beyond 200 D before other clearances. The compact 3+1 pack's 1 mm depth and 20 mm height remainders are bottlenecks, not spare integration room. PSU body, restraint, airflow and connector reserves must be modeled explicitly.

### Next CAD packing constraints and gates

1. Keep one connected printed support skeleton within 200 x 188 x 254 mm in its selected print rotation. Search card orientation, translation, receiver/bracket poses and installed core rotation jointly; no appended bay-D print and no fixed 48 mm thickness cap.
2. Treat each card, receiver PCB/underside, connector straight zone, cable bend, safe support patch, clamp, fan sweep/plenum, PSU/air keepout and tool region as a separate solid or constraint. Unknown measured interfaces remain unresolved, never zero-volume obstacles.
3. Check installed static collisions and swept independent-removal volumes. Preserve 12 mm intake throats after every interface intrudes. Longitudinal staggering saves width only where card bodies actually cease overlapping; moving a bracket plane alone cannot remove a cooler collision.
4. Constrain every support footprint to the one core; evaluate overhang spans, center of gravity, tip stability, metal reinforcement, layer direction and PETG creep. All four cards transfer load through safe supports/brackets to reinforced rails and feet.
5. Rank feasible poses by installed footprint, access, intake/exhaust compatibility, connector bends, load spans and print mass. Card-box compactness alone is not the objective.
6. Release only after measured GPU/receiver/PSU datums, collision/removal checks, print/brim/support fit, coupons, spool report and simultaneous four-card thermal/load tests. Preserve preferred <=3 kg and hard <=4 kg total on one fresh continuous 5 kg spool. Unknown gates keep this a concept; no CAD/STL issuance from these calculations.

Cards over the original 1.2 kg target need a metal tail support; the original maximum with that support is 2.2 kg. Both targets require qualification. Four-card totals are 4.8/8.8 kg before PSU and other components; these are test loads, not certified chassis ratings.

Primary GPU load goes into padded body supports and bracket restraints, then reinforced rails/feet. Do not let the PCIe socket carry the card's mass. Every bay must allow independent removal. Avoid pressure on fans, heatpipes, components and connectors. Provide a stable footprint including any PSU or card overhang; perform a tip/stability check with the heaviest population.

## Printing and material

Baseline: plain PETG on one continuous 5 kg spool, external bearing holder, 0.6 mm nozzle, approximately 0.28 mm layers after calibration. Preferred total slicer mass <=3 kg; hard planning ceiling <=4 kg including support/brim. A multi-pack of 1 kg spools does not meet the continuous-spool requirement.

Use ribs, gussets, fillets, open windows and box sections. Remove material from broad cosmetic skins, cover fields and plenum panels first. Preserve receiver rails, GPU brackets, PSU strap anchors, fan bosses, feet, docking bosses and strain-relief anchors. Local perimeter/infill guidance is preserved in the recovered print plan. Numbers are starting profiles, not strength certification.

Printing in the recorded tall orientation needs a layer-direction load review after the part is rotated. Reinforce junctions exposed to layer separation. PETG creep means broad metal washers/spacers and modest clamp pressure. Qualification uses conservative printed-support temperature limits in the originals; change material/process if the load paths become too warm or compliant.

## Fasteners

M4 through-bolts, washers and metal nuts for primary structure; M3 metal standoffs and machine screws for boards. Secondary lids/controllers can use measured heat-set inserts. No structural self-tapping screws into PETG.

Original stocking quantities and lengths are preserved in FASTENERS_AND_HARDPOINTS. They are purchase allowances plus spares, not a final assembly count. Final CAD must produce actual stack thickness, thread engagement, nut/tool access and installed quantities. Select fan screws only after fan/guard/pad/boss/washer stack is modeled. Do not substitute arbitrary metric screws into GPU I/O brackets or PSU factory threaded holes; use the designed clamp/strap or confirm their actual thread.

## Air and cable paths

Two 120 mm pressure fans and a 25–35 mm common plenum remain an unqualified candidate for four bays. Recorded P12 Max envelope: 120 x 120 x 25 mm, hole centers 105 x 105 mm. Preserve open rear exhaust and each card's intake direction. Provide four bay intake paths and at least 12 mm clear separation on the actual neighboring intake faces; label channels from the chosen topology rather than assuming a linear AB/BC/CD row. Requalify distribution and simultaneous four-card thermals; free-air CFM is not chassis airflow. Adding a fan does not itself prove the revised plenum fits or cools correctly.

Separate signal, GPU power and control corridors. Starting minima: signal 28 x16 mm, power 28 x 20 mm per bay, control 14 x 10 mm. Add bay-D receiver/retention, power path, signal lead, service access and strain relief; enlarge shared trunks for four actual cable bundles. Provide connector straight/service zones and vendor bend radii, accessible latches and removable covers. No cables in fan sweep or minimum air channels. Label POD1-A/B/C/D, GPU-A/B/C/D, LINK-A/B/C/D and PWR-A/B/C/D consistently with persistent device IDs.

## PCIe architecture

E1 x16 splits into four CPU-root x4 branches: all four for receivers A–D, with none reserved. Use a matched bifurcation host adapter, four qualified external links and four independently powered mechanical-x16 receivers. Candidate transport remains RIITOP quad OCuLink + ADT F9Q-BK10. Gen4 x4 is the target; an x16-shaped socket is not x16 electrical bandwidth. The separate 5070 Ti needs a mechanically/electrically qualified E4 riser/support route and measured bandwidth. M2_3 shares the E4 lane resource. Current discovery reports the NVIDIA card at x16 before redistribution; do not claim this proposed E4 relocation is already installed or retains that bandwidth.

At PCIe Gen4, x4 signaling payload after 128/130 encoding is about 7.88 GB/s per direction before transaction/software overhead (16 GT/s x 4 x 128/130 / 8). This is a calculated ceiling, not a transfer benchmark. A GPU-to-host-to-GPU copy uses both endpoint links, host memory and driver synchronization; measured transfer can be lower. Chipset devices also share upstream resources. J-Link must keep topology in the placement model.

Final receiver PCB mounts stay slotted until official CAD or caliper measurement supplies hole centers, underside components, connector heights and slot datum. Both published CAD links failed during this collection. Do not treat the archived filename as evidence that CAD was actually downloaded.

## Power sizing using the requested headroom

Let Pload = sum of selected GPU maximum board powers + local fans/control + non-overlapping receiver/conversion losses. GPU board power generally already includes PCIe-slot contribution: do not add another 75 W per card on top without identifying a separate load. For a separate pod PSU, do not include host CPU load if the host has its own PSU.

Two common meanings of 20% headroom:

- 20% above calculated load: rating >=1.20 x Pload.
- Keep 20% of rating unused: rating >=Pload/0.80 =1.25 x Pload.

Planning examples only; 8 GB does not determine board power:

| Four-card illustrative board power +40 W overhead | Pload | Rating >=1.20 x load | Rating >=load/0.80 |
|---|---:|---:|---:|
| 4 x 130 W | 560 W | 672 W | 700 W |
| 4 x 170 W | 720 W | 864 W | 900 W |
| 4 x 300 W | 1,240 W | 1,488 W | 1,550 W |

These are calculations, not a PSU or GPU purchase recommendation. Exact board limits, four receiver inputs, native cable inventory, transients and derating determine selection. Host CPU/display-card load belongs to the separate host power domain unless that architecture is explicitly revised. Do not double-count fan/receiver overhead already included in Pload.

Use native cables approved for the exact PSU; never mix modular cable pinouts. Map receiver power and GPU auxiliary power separately. Keep independent PSU DC outputs separate. Qualify startup/shutdown sequencing with host off during cable changes; OCuLink hot plug is not assumed. No energized rewiring.

## Expansion and production release

Recorded docking interface: four M4 fasteners on an 80 x 60 mm rectangle, reinforced bosses and a metal plate. A control link is not a PCIe data uplink. All four E1 branches are now consumed; a second pod needs extra root-port capacity, a qualified active switch or another host/network transport.

Production STL requires: exact components; four-card interference and independent removal; four link/receiver enumeration and separate display-route qualification; power/connector map; nut/tool access; stability/load review; printed coupons; bed/brim/support fit; slicer mass; simultaneous four-card airflow/thermal tests. No production STL is included because these inputs are unknown. The recovered Astra handoff describes three bays; apply this four-bay amendment before any new parametric concept model.

Use the integrated release sequence in `03_EXPERIMENT_RUNBOOK.md` to connect these mechanical gates to actual four-card computation and failure controls. Fit coupons must reproduce receiver hole/slot/underside datums, D's rotated receiver, safe card support contacts and fastener/tool clearances. Test PETG pillar/rail coupons under sustained load at the planned support temperature, with measured deflection and layer separation criteria fixed in advance. Calculate tipping/overhang moments using actual card and PSU masses, then verify each card's independent removal sweep. A GPU-box packing result cannot release the core while those interfaces are null.



