# Mechanical Envelope — Authoritative Universal 3-GPU Pod

**Revision:** 2.0-preCAD  
**Authority:** subordinate to `MASTER_BLUEPRINT.md` and `DIMENSION_AUTHORITY_AND_TBDS.md`

## Printer constraint

Creality Ender-3 S1 Pro nominal build volume: 220 × 220 × 270 mm.

The **one-piece printed core** shall fit inside:

- Print X <= 200 mm
- Print Y <= 188 mm
- Print Z <= 254 mm

This preserves margin for brim/adhesion and avoids using the printer's nominal limits as hard geometry.

## Operational orientation after print

Rotate the finished core so:

- operational width W ≈ 254 mm
- printed-core depth D ≈ 200 mm
- printed-body height H ≈ 188 mm

Long GPUs deliberately overhang rearward beyond the 200 mm printed core.

## Three universal GPU bays

Across W = 254 mm:

```text
13 structure
68 Bay A max envelope
12 minimum A/B airflow channel
68 Bay B max envelope
12 minimum B/C airflow channel
68 Bay C max envelope
13 structure
= 254 mm
```

Each bay targets:

- thickness: 35–68 mm adjustable
- body height: <=165 mm
- card length: <=360 mm with rear overhang
- card mass: <=1.2 kg without metal tail support
- card mass: <=2.2 kg with metal tail support

The first test population is 42 mm thick, but card clamps/supports must be adjustable. The chassis is not centered or hard-shaped around the RTX 3060.

## GPU datums and support

Use only universal datums:

1. receiver PCIe slot datum,
2. GPU metal I/O bracket plane,
3. adjustable lateral shoe,
4. padded safe body support,
5. optional metal far-end support.

Do not key the chassis to GPU shroud screws, fan locations, backplate decoration, or one auxiliary-power location.

Card power uses an open top/rear service zone suitable for 8-pin and 12V-2x6 layouts.

## Fan wall

Two ARCTIC P12 Max 120 × 120 × 25 mm fans mount **side-by-side across operational width**.

- two frames = 240 mm
- outer border ≈7 mm each side before local ribs
- hole center spacing = 105 × 105 mm from vendor drawing
- vendor fan hole diameter = 4.40 mm; chassis M4 clearance tuned by coupon

Fan wall is a ribbed frame with large open fan throats, not a solid plate.

## Plenum

Common intake plenum target: 25–35 mm from fan discharge plane to first hard divider.

Use rounded transitions and thin splitters after a short pressure-equalization volume. Maintain the 12 mm inter-card throats after every cable, clamp, and receiver feature is modeled.

## Rear / exhaust

Rear stays substantially open. Do not close GPU exhaust with a cosmetic wall.

Operational shelf depth must include:

- card rear overhang,
- auxiliary-power connector protrusion,
- cable bend radius,
- service clearance.

## Structural skeleton

Use a ribbed monocoque / ladder frame:

- 2.4–3.0 mm low-load skins
- 5–7 mm effective structural ribs/gussets
- 7–10 mm major hardpoint sections
- 3–6 mm inside fillets
- large radiused lightening windows
- no full solid floor

Primary load paths:

- receiver datum rail
- GPU I/O bracket rail
- lateral shoe rails
- tail-support sockets
- fan-wall junctions
- PSU strap hardpoints
- pod docking hardpoints
- heavy cable strain-relief anchors

## PSU relationship

PSU remains a separate intact ATX enclosure. Current reference envelope: Corsair RM1000x ATX 3.1, 160 × 150 × 86 mm.

Keep PSU W/D/H and cable projection parametric. Use metal restraint straps/cradle pieces and M4 through-bolted chassis hardpoints with EPDM/neoprene isolation. Never make the PSU mass depend on printed threads.
