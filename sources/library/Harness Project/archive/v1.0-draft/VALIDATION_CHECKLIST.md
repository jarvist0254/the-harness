# Harness Validation Checklist

## Before CAD freeze

- [ ] Measure exact RTX 5070 Ti dimensions and connector projections.
- [ ] Measure selected ATX PSU dimensions and modular cable projection.
- [ ] Select exact E1 bifurcation adapter/cable/receiver system.
- [ ] Import or measure receiver-board mounting holes and keepouts.
- [ ] Confirm 3060 42 mm thickness against actual units when received.
- [ ] Verify lower-shelf available width/depth/height and insertion path.
- [ ] Check power-strip/branch capacity for host + external PSU under simultaneous load.

## Before full print

- [ ] Blender model stays within 220×220×270 mm printer volume.
- [ ] Four-card stack plus air channels fits 245–250 mm Z target.
- [ ] GPU overhang and 8-pin bend radius do not collide with furniture.
- [ ] Two 120 mm fan mounts and guards fit without blade obstruction.
- [ ] PSU inlet/exhaust remains open.
- [ ] Empty fourth position has removable blanking plate.
- [ ] Slicer reports acceptable material mass and print time.
- [ ] No pause/spool-change is required unless a tested filament-feed method is available.
- [ ] Small hole/insert coupon printed and verified first.

## Electrical bring-up

- [ ] BIOS PCI_E1 bifurcation set x4/x4/x4/x4.
- [ ] M2_3 confirmed empty.
- [ ] One 3060 tested on branch A.
- [ ] Repeat cold boots without PCIe enumeration errors.
- [ ] Add branch B, retest.
- [ ] Add branch C, retest.
- [ ] 5070 Ti validated on PCI_E4 x4.
- [ ] Verify all four initial GPUs in Windows/WSL/CUDA.
- [ ] Record PCI bus IDs and CUDA UUIDs.

## Thermal/power qualification

- [ ] Idle temperatures logged.
- [ ] One-card load logged.
- [ ] Three-3060 simultaneous load logged.
- [ ] 5070 + three 3060 simultaneous workload logged.
- [ ] External PSU wall draw logged.
- [ ] Host PSU/system wall draw logged.
- [ ] Printed load-bearing areas inspected for heat softening/creep.
- [ ] Fan-wall airflow bypass checked around empty slot.

## J-Link acceptance

- [ ] Device topology map persistent across three cold boots.
- [ ] H2D/D2H bandwidth measured for each GPU.
- [ ] P2P support matrix detected rather than assumed.
- [ ] Independent workers survive 8-hour soak.
- [ ] Scheduler respects VRAM reservations.
- [ ] One DDP training smoke test recorded.
- [ ] Graceful drain/stop behavior verified.
