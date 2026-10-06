# Cable Management Blueprint

## Design objective

The finished pod should look and service like a purpose-built appliance, not a mining frame. Every bay has deterministic cable paths. A GPU or receiver can be replaced without cutting a bundle of zip ties or removing another card.

## Cable classes

Keep separate physical spines for:

1. **high-speed data** — OCuLink
2. **high-current power** — GPU auxiliary + receiver power
3. **low-current control** — fan PWM, tach, sensors
4. **AC mains** — terminates at the enclosed PSU only; never routed through printed low-voltage ducts

## Signal spine

Place OCuLink routing on one side of the chassis.

Requirements:

- three separate labeled lanes A/B/C
- open C-channel with removable clip/insert-fastened lid; no sealed tunnel
- starting internal lane envelope ~18 × 12 mm minimum per cable section; adjust after measuring actual connector/jacket
- rounded cable exits, radius ≥3 mm on printed edges
- no sharp 90° fold
- design a **≥30 mm bend-radius keepout as a provisional minimum** until the exact purchased cable vendor specifies otherwise
- provide strain-relief clamp within ~50 mm of receiver connector; clamp jacket, not connector shell
- cable has service slack but cannot droop into GPU fans

The included reference receiver kit uses 50 cm full-pin OCuLink cables. Full-pin/sideband support is required for this reference chain.

## Power spine

Locate on the opposite side where practical.

Starting shared power corridor:

- ~45 × 30 mm open channel / basket
- removable retention bars every ~70–90 mm
- retention bars use M3 heat-set inserts, not zip ties threaded through structural holes
- allow both legacy 6+2/8-pin GPU cables and modern 12V-2x6 cable envelopes
- provide at least ~45 mm free connector/bend service zone above/around a GPU power socket as a chassis allowance; card/cable manufacturer's larger requirement takes precedence

Do not hard-model three identical 8-pin connectors merely because the first cards use them.

## Data/power separation

- target ≥25 mm separation between long parallel OCuLink and high-current GPU power runs where geometry allows
- if they must cross, cross approximately at 90°
- do not bundle OCuLink tightly against PSU AC inlet wiring or the PSU modular-panel bundle

## Fan/control spine

Small separate channel, roughly 12 × 8 mm starting internal size, for:

- two fan leads
- PWM/tach lead
- temperature probes
- future microcontroller/telemetry lead

Do not mix a loose temperature-probe wire into a GPU fan opening.

## Retention hardware

Preferred:

- reusable hook-and-loop straps
- metal/plastic P-clamps bolted to receiver deck
- printed clip bars bolted into M3 heat-set inserts
- braided sleeving only where it does not prevent service

Avoid:

- one-time zip ties as primary service retention
- adhesive-only anchors near hot components
- clamps that crush high-speed cable jackets

## Labeling

Emboss on chassis:

- POD ID area
- BAY A / B / C
- DATA
- POWER
- FAN/CTRL

Use matching removable cable labels at **both ends** of every OCuLink and GPU power cable.

Recommended logical notation:

- P1-A-DATA
- P1-A-RX-PWR
- P1-A-GPU-PWR-1
- P1-B-...

## PSU service loop

The modular-panel side must remain accessible without removing GPUs. Provide enough cable service loop to unplug a modular lead without bending the receiver PCB or pulling on a GPU connector.

## OCuLink host bundle

At the host, provide an external strain-relief comb/anchor so the motherboard adapter does not carry the weight of three 50 cm cables. The host adapter is a PCB edge card and should not be used as a cable hanger.

