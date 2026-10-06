# Fasteners, Inserts, Standoffs and Hardpoints

**Design rule:** no reusable structural thread cut directly into printed plastic.

## 1. Standard thread system

Use two thread families only unless verified hardware requires otherwise:

- **M4** — structural chassis, fan, PSU restraint, pod docking, GPU support
- **M3** — PCB/electronics, cable combs, small covers, sensor/control mounts

This keeps tools and spares simple.

## 2. Primary structural fasteners — M4

Recommended stock for one pod plus spares:

| Item | Buy qty | Expected use |
|---|---:|---|
| M4 × 10 socket-head machine screws | 20 | covers/short metal clamp interfaces |
| M4 × 12 socket-head machine screws | 30 | structural brackets/adjusters |
| M4 × 16 socket-head machine screws | 30 | thicker clamp stacks |
| M4 × 20 socket-head machine screws | 20 | tail support / docking plates |
| M4 × 30 socket-head machine screws | 12 | fan/guard stacks depending final thickness |
| M4 × 35 socket-head machine screws | 12 | fan + isolator + chassis + nut option |
| M4 flat washers | 100 | every plastic-facing structural joint |
| M4 nyloc nuts | 60 | primary through-bolts |
| M4 standard hex nuts | 30 | captive-nut pockets where nyloc is unsuitable |
| M4 knurled/thumb nuts/screws | 6 | optional tool-light GPU clamp adjustment |

304 stainless is fine for the chassis environment; high-strength alloy is also acceptable. Use washers anywhere a screw/nut bears on PETG.

## 3. Heat-set inserts

Heat-set inserts are for serviceable attachment, not the highest structural loads.

### M3

Preferred family: ruthex RX-M3x5.7 or dimensionally equivalent.

Reference dimensions:

- internal thread: M3
- insert length: 5.7 mm
- outer diameter: ~4.6 mm
- published recommended printed hole for this family: ~4.0 mm

Buy: 100-pack.

Use for:

- cable raceway lids
- control/sensor brackets
- small service panels
- optional receiver-tray accessories

### M4

Preferred family: ruthex RX-M4x8.1 or dimensionally equivalent.

Reference dimensions:

- internal thread: M4
- insert length: 8.1 mm
- outer diameter: ~6.3 mm
- published recommended printed hole for this family: ~5.6 mm

Buy: 50-pack.

Use for:

- removable non-primary brace interfaces
- service panels subjected to more load than M3
- adjustable secondary card shoes when a through-bolt is geometrically impossible

**Important:** tune insert holes with the actual insert + printer + PETG coupon. The CAD nominal is not the final printer-compensated hole.

## 4. PCB / receiver mounting

Preferred receiver: ADT F9Q-BK10.

### What is verified

- PCIe 4.0 x4 OCuLink receiver to x16 mechanical slot
- 50 cm cable in the F9Q-BK10 package description
- redriver-equipped
- vendor publishes downloadable 3D CAD

### What is deliberately NOT guessed

The exact board mounting-hole coordinates and hole diameters are not released in this package because the vendor CAD archive has not yet been imported into the model.

### Universal tray hardware

Astra should design the receiver tray around:

- M3 × 6 machine screws: 24
- M3 × 8 machine screws: 24
- M3 flat washers: 60
- M3 nyloc/hex nuts: 30
- M3 brass/stainless standoffs, 6 mm and 10 mm: 12 each

The tray uses 3.6–4.0 mm wide longitudinal slots. Metal standoff + washer + nut clamps through the tray. No screw should rely on an M3 thread cut directly into PETG.

When vendor CAD is imported, choose the standoff height that clears underside components and preserves PCIe connector alignment. If receiver holes are not M3-compatible, revise the adapter hardware — **never enlarge the PCB holes by assumption**.

## 5. Fan mounting

Fan: 120 × 120 × 25 mm class, current target ARCTIC P12 Max.

Use machine screws, not self-tapping fan screws.

Preferred stack:

```text
M4 screw head
metal fan guard (optional)
fan frame
1–2 mm elastomer washer/pad
printed fan-wall boss
M4 flat washer
M4 nyloc nut
```

Select M4 × 30 or M4 × 35 after final guard/pad/boss thickness is modeled.

Astra must import/check the selected fan’s manufacturer 2D drawing before fixing hole coordinates. Do not infer from a decorative fan model.

## 6. GPU restraints

### I/O bracket restraint

Do not depend on a specific GPU manufacturer shroud hole. Clamp the standard metal I/O bracket region or a separate metal crossbar.

Recommended chassis fastener: M4 through-bolt + washer + nyloc nut.

### Adjustable side shoes

- M4 × 12/16 through-bolt in elongated slot
- metal washer both faces
- nyloc nut or captive metal nut
- 1–2 mm EPDM/neoprene pad on GPU contact face

### Tail support

Long/heavy GPU tail support should use a **metal vertical rod/flat bar** captured by the printed chassis rather than a long printed cantilever.

Starting concept:

- 2 × M4 or M5 stainless threaded rods / aluminum flat bars
- adjustable padded cradle
- M4/M5 washers + nyloc nuts
- receiver-side and tail-side load paths tied into chassis ribs

Exact tail-support metal dimensions are a CAD iteration item, not frozen.

## 7. PSU restraint

Do not drill/screw arbitrary points into the PSU enclosure.

Use:

- two 15–25 mm wide stainless perforated straps or purpose-made metal straps
- 1–2 mm EPDM/neoprene isolation strip
- 4 × M4 through-bolts per strap pair as geometry requires
- large washers
- nyloc nuts

The printed chassis supplies reinforced strap slots/hardpoints. The metal strap carries clamp tension.

## 8. Pod docking hardpoints

Fixed standard for future compatibility:

- four M4 holes on 80 × 60 mm rectangle
- through-bolted preferred
- at least 16 mm OD equivalent load-spreader/boss region around each hole
- two ribs from each dock boss into the nearest main rail
- metal joining plate between pods, not PETG tongue-to-PETG tongue

## 9. Tightening philosophy

PETG creeps under sustained clamp load. Do not over-torque and crush printed features. Use broad washers, metal spacers where a fixed gap is required, and nyloc nuts to retain preload without excessive torque.

Any joint that defines PCIe connector alignment should bottom on a metal standoff/spacer, not compress plastic until alignment “looks right.”
