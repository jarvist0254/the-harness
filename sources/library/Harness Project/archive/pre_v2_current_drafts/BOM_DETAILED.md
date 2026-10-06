# Detailed BOM — Universal Three-GPU Pod

**Price observation date:** 2026-09-30. Prices are volatile; verify at checkout.  
**Amazon preference:** commodity hardware should be consolidated on Amazon when an equivalent reputable listing is available. PCIe transport and engineering filament are allowed to come from specialist vendors because quality matters more than one-cart convenience.

## A. Compute population — already chosen

| Qty | Item | Observed price | Extended | Notes / link |
|---:|---|---:|---:|---|
| 3 | MSI RTX 3060 Ventus 2X OC 12GB refurb | ~$359.99 ea | ~$1,079.97 | Initial population only; chassis remains universal. User-provided Newegg listing: https://www.newegg.com/msi-rtx-3060/p/1FT-0009-00B46 |

## B. PCIe transport — current reference chain

| Qty | Item | Observed price | Extended | Notes / link |
|---:|---|---:|---:|---|
| 1 | RIITOP PCIe 4.0 x16 → 4 × OCuLink SFF-8612 host adapter | $46.99–$48.99 | ~$49 | Requires BIOS x4+x4+x4+x4. Pod uses 3 ports. https://www.riitop.com/products/riitop-pcie-to-oculink-adapter-4-port-pcie-4-0-x16-to-sff-8612-sff-8611-female-full-speed-64gbps-4port-for-egpupci-e-x4x4x4x4-bifurcation-required |
| 3 | HOOCCC OCuLink GPU Dock kit, x16 physical/x4 electrical, 50cm full-pin cable + bracket | $73.99 ea | $221.97 | PCB 138×46mm. Mount spacing published 95/103mm. https://www.newegg.com/p/1DN-045E-00002 |

**PCIe transport subtotal:** about **$271** before tax/shipping.

Premium receiver alternative if signal-integrity/fit testing rejects HOOCCC: ADT-Link / other documented PCIe 4.0 x4 receiver with vendor CAD. Do not redesign the printed body; replace the metal carrier.

## C. Print material / printer preparation

| Qty | Item | Observed price | Extended | Notes / link |
|---:|---|---:|---:|---|
| 1 | Polymaker Fiberon PA6-GF25, 1.75mm, 3kg | $119.99–$120 | ~$120 | B&H lists 3kg FG02002 at $119.99; MAKEiT lists $120. https://www.bhphotovideo.com/c/product/1894635-REG/polymaker_fg02002_fiberon_pa6_gf25_glass_fiber.html ; https://www.makeit-3d.com/store |
| 1 | 0.6mm abrasion-resistant/hardened nozzle for Sprite/S1 Pro | ~$10–$20 budget | ~$15 | Exact nozzle must explicitly fit the installed S1 Pro/Sprite hotend. Do not buy generic Volcano/MK8 by appearance. |
| 1 | SUNLU FilaDryer E2 or equivalent 3kg / 100°C-capable dryer | $249.99 current SUNLU starting price | ~$250 | Supports up to one 3kg spool and 35–110°C. https://store.sunlu.com/products/sunlu-filadryer-e2-up-to-110-professional-drying-and-annealing-born-for-engineering-3d-printing-filaments |

If the user already has a verified 100°C drying method plus a dry feed path for a 3kg spool, the E2 can be omitted. Cheap 70°C boxes are not equivalent for the PA6-GF manufacturer's 100°C pre-dry recommendation.

## D. Cooling

| Qty | Item | Observed price | Extended | Notes / link |
|---:|---|---:|---:|---|
| 2 | ARCTIC P9 Max 92mm PWM | MSRP about €13.99 / market varies | budget ~$30 | 58.25 CFM and 6.17mmH2O each. https://www.arctic.de/en/P9-Max-Black/ACFAN00300A |
| 1 | ARCTIC Case Fan Hub, SATA powered | MSRP ~$10.99 | ~$11–$20 | Clean PWM distribution; 86.3×55.6×14.3mm. https://www.arctic.de/en/Case-Fan-Hub |
| 2 | 92mm wire finger guards | ~$5 ea budget | ~$10 | Prefer open wire guard over restrictive printed grill. Amazon commodity item acceptable. |

## E. PSU

**Target:** quality 1000W fully modular PSU with enough approved PCIe cabling for three independent bays.

Reference cable-map candidate: EVGA SuperNOVA 1000 GT 220-GT-1000-X1. EVGA manual documents five VGA modular outputs and 8 total 6+2 connectors across supplied VGA cables. Current reputable availability is inconsistent; do not overpay merely to preserve this SKU.

Current alternative to evaluate at checkout: Super Flower Leadex VII XG 1000W / current ATX 3.1 class 1000W PSU, provided its exact native cable inventory can satisfy receiver + GPU feeds without unsafe adapters.

Budget line: **$140–$200**.

**Do not buy the PSU until cable-count verification is completed for the exact SKU.** Wattage alone is not enough.

## F. Metal structure / interfaces

Amazon is appropriate for these commodity parts if dimensions/material match.

| Qty | Part | Budget | Specification |
|---:|---|---:|---|
| 1 | Aluminum sheet/deck | $20–$35 | 1.5–2.0mm thick, at least ~200×200mm; cut to ~190×155 after fit |
| 1 | Aluminum angle for GPU I/O rail | $10–$20 | ~20×20×2mm, ≥250mm length; cut to chassis width |
| 1 | Aluminum/steel PSU retention plate stock | $10–$20 | ~1.5–2mm sheet/angle; drill to exact PSU |
| 1 | Optional tail-support stock/rod | $10–$20 | 6mm rod or small aluminum section depending Astra design |
| 4 | 6mm steel dowel pins | ~$8–$12 | ~30mm length starting size for PodLink alignment |
| 1 | EPDM/neoprene sheet/pads | ~$10 | 1–2mm for PSU/fan/card-contact isolation |

## G. Threaded inserts / screws

Reference supplier with known dimensions rather than no-name mixed insert geometry:

- CNC Kitchen M3×5.7, 100 pcs: **$10.90**
- CNC Kitchen M5×9.5, 50 pcs: **$11.50**
- or their M3/M4/M5 standard/short sets
- https://cnckitchenus.store/

Amazon equivalent is acceptable only if its published OD/length/hole dimensions are used to update the CAD. Do not swap insert geometry after the chassis is modeled.

Hardware quantities to purchase:

| Item | Purchase qty | Expected use |
|---|---:|---:|
| M3 heat-set insert, standard | 100 | ~20–35 used; remainder spares |
| M5 heat-set insert, standard | 50 | light/medium service interfaces; structural coupling prefers through-bolts |
| M3 stainless screw assortment | 1 kit | 6–20mm lengths, receiver accessories/cable lids/controller |
| M4×35 stainless bolts | 12 | 8 fans + spares |
| M4 flat washers | 24 | fan joints |
| M4 nyloc nuts | 12 | fans |
| M5 assorted stainless bolts | 1 kit | 12/16/20/25/30mm preferred |
| M5 washers/fender washers | 24+ | receiver deck / PSU plate / PodLink |
| M5 nyloc nuts | 20+ | structural through-joints |
| #6-32×1/4in PC screws | 12+ | GPU brackets / metal rail |
| M3 metal standoff assortment | 12–20 | receiver PCB after hole measurement |

Budget: **$50–$80** total for a decent stainless assortment + known inserts.

## H. Cable management

| Qty | Item | Budget | Notes |
|---:|---|---:|---|
| 1 pack | reusable hook-and-loop cable straps | $8–$12 | 6–8in mixed |
| 1 pack | metal/rubber P-clamps | $10–$15 | multiple diameters for power/data; bolt to metal deck |
| 1 roll | PET braided sleeve / split loom | $10–$15 | use on power/control, not where it makes OCuLink bend too tightly |
| 1 pack | heat-shrink cable labels or printable labels | $10 | label both cable ends |
| 1 | rubber edge trim / grommet strip | $8–$12 | for metal deck/rail cut edges |

## I. Rough non-GPU project budget

Excluding the three GPUs and assuming a ~$170 PSU:

- PCIe transport: ~$271
- filament: ~$120
- dryer: ~$250 (omit if already covered)
- nozzle: ~$15
- fans/controller/guards: ~$50
- PSU: ~$170
- metal: ~$60
- inserts/fasteners: ~$65
- cable management: ~$45

**Approx. with dryer: ~$1,046**  
**Approx. without new dryer: ~$796**

These are engineering-budget numbers, not guaranteed checkout totals.

## Amazon consolidation strategy

Buy from Amazon when equivalent and dimensions are verified:

- M3/M4/M5 stainless fastener kits
- washers/nyloc nuts
- #6-32 PC screws
- 6mm dowel pins
- aluminum sheet/angle
- EPDM pads
- hook-and-loop/P-clamps/sleeving/edge trim
- fan guards
- possibly ARCTIC fans/hub

Keep specialist sourcing for:

- GPUs (chosen Newegg deal)
- RIITOP/OCuLink transport if Amazon listing is not clearly the same revision
- HOOCCC receiver kits
- PA6-GF25 3kg spool if Amazon does not have the exact 3kg SKU
- engineering dryer if another seller is materially cheaper/reputable

