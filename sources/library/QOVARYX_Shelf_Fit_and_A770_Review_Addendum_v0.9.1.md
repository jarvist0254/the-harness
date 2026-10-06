# QOVARYX external GPU shelf — furniture fit and A770 review addendum

**Revision:** 0.9.1 / 2026-09-05  
**Parent:** `QOVARYX_3xS80_External_GPU_Shelf_Blueprint_v0.9.md`  
**Status:** PLACEMENT AND CANDIDATE REVIEW; NOT PURCHASE OR FABRICATION RELEASE

## 1. What changed, and what did not

The owner supplied a photograph of the wooden table holding the existing PC and requested that the external accelerator assembly preferably occupy the lower/second shelf. Rotating the main case on the tabletop is an alternative the owner is considering. No furniture measurements or load rating have been supplied.

The new Amazon link resolves to the **ASRock Intel Arc A770 Phantom Gaming 16GB OC**, model **A770 PG 16GO**, ASIN **B0CDM3QK7Q**. This addendum evaluates A770 as a possible replacement for the proposed S80 workers. It does not authorize buying three A770s, adding them on top of three S80s, or increasing the external population above three.

The intended system architecture remains one host, the existing internal RTX, both installed NVMe drives unchanged, one external PCIe connection, an active switch, and one external 1000 W PSU. Selection of Intel instead of Moore Threads does not remove the active-switch/cable/power qualification gates. The parent document's switch pricing and unresolved quotations are not revised by this addendum.

No CAD or STL file is changed by this addendum. Existing S80-specific envelopes and cradles are not released for A770 installation.

## 2. What the photograph establishes

The photo shows a lower wooden shelf beneath the PC, furniture legs, and a decorative horizontal rail/apron above the front opening. That rail may reduce the insertion opening below the full interior height. Cables can potentially be routed down the rear or a side, subject to measurement.

The photograph does **not** establish clear width, depth, height, shelf load capacity, rear wall clearance, switch mounting geometry, or the required high-speed cable length. Do not derive fabrication dimensions from perspective or the sizes of incidental objects in the photograph.

## 3. Measurement worksheet — all fields required before final layout

Use millimetres; inches are acceptable if explicitly labelled. Record the smallest clearance along the whole insertion path.

| ID | Measurement | Value |
|---|---|---|
| F01 | Clear left-to-right width between the legs, at shelf surface and GPU height | NOT MEASURED |
| F02 | Usable front-to-back shelf depth, excluding inaccessible overhang and obstructions | NOT MEASURED |
| F03 | Height from shelf surface to underside of the front decorative rail | NOT MEASURED |
| F04 | Height from shelf surface to underside of tabletop behind that rail | NOT MEASURED |
| F05 | Rear clearance to wall, existing cables, and other obstructions | NOT MEASURED |
| F06 | Side-opening dimensions if assembly cannot enter through the front | NOT MEASURED |
| F07 | Actual routed distance from host adapter connector to switch input, including case exit and gentle bends | NOT MEASURED |
| F08 | Furniture shelf supported load, condition, and stability | NOT ESTABLISHED |
| F09 | Actual chosen switch outline, mounting points, port positions, and connector keepouts | NOT VERIFIED |
| F10 | Exact PSU body, modular plug projection, inlet and exhaust clearance | NOT VERIFIED |

Use string along the proposed cable path for F07. Measure connector-to-connector, not the straight-line separation of the computer and table shelf. Add only the service/bend allowance appropriate to the approved cable assembly; do not substitute an arbitrary long ribbon or an unqualified extension.

## 4. Existing design baseline and A770 dimensional changes

The parent design's provisional S80 skeleton is **420 W × 240 D × 320 H mm**. Its operational depth, including the cards and cable space, is approximately **360 mm**. These are design allowances, not measured furniture requirements or a validated switch-board outline. The parent design also contains an unverified 380 × 180 mm switch placeholder; actual hardware can force a larger frame. [U01]

| Card | Manufacturer body envelope: length × height × thickness | Memory | Auxiliary power |
|---|---|---|---|
| MTT S80 | 285 × 112 × 49 mm | 16 GB GDDR6 | Retain the parent's OEM-harness verification requirement |
| ASRock A770 PG 16GO | 305 × 131 × 56 mm; 2.8-slot | 16 GB GDDR6 | Two PCIe 8-pin connectors |

Sources: [S01], [S02].

The ASRock is therefore **20 mm longer, 19 mm taller, and 7 mm thicker**. These are calculated differences, not a measured rack fit. Increase GPU envelope checks, support adjustment range, cable keepouts and anti-sag restraint accordingly. Its listed net mass is 1.146 kg; include all installed hardware and the PSU when determining total shelf load. [S01]

Do not treat the 240 mm support-frame depth as the whole assembly depth. Permitted GPU overhang still occupies physical space and must remain clear of furniture, cables and accidental impact.

At the parent's provisional 101.6 mm slot pitch, a simple thickness subtraction leaves 45.6 mm between idealized A770 body envelopes. This is only a geometry check: actual cooler projections, the first/last-card clearances, cable routes and airflow must still be checked. Do not change physical slot pitch independently of the selected backplane.

## 5. Preferred lower-shelf arrangement

**First layout to evaluate:** three upright, parallel cards side by side, not three cards piled flat above one another. Keep the backplane mounted horizontally and correctly supported beneath their connectors. Retain adjustable body cradles and a metal I/O-bracket restraint. Use the printed modules as mounts/locators, with the parent's metal structural rails and braces.

Keep the PSU underneath only if F03/F04 permit the assembled height plus ventilation and service access. If the front opening is too short, evaluate moving the PSU beside the GPU/backplane bay. This reduces stacked height but increases width; it does not create a narrower backplane or remove its connector clearances.

Do not assume three separate cards can be rearranged arbitrarily when plugged directly into an integrated switch board. Relocating individual cards would introduce additional risers and a separate compatibility review.

### Furniture placement and airflow

- Clear the lower shelf of papers, packaging and loose parts before installing electronics.
- Keep the assembly on supported feet/tray; mount every PCB on its specified standoffs. Do not place bare PCBs directly on the furniture.
- Route a deliberate stream of cool room air through the card gaps and discharge warmed air away from the PC's intake. Select fan positions after measuring the openings; a decorative rail can obstruct an apparently open front.
- Keep PSU intake, exhaust, GPU fans and switch cooling unobstructed. Reserve connector bend and latch access, not just enough room for the bare card.
- The permitted GPU overhang must not create a tipping or impact hazard. The PSU should remain fully supported.
- Provide cable strain relief on both the host and shelf, not on the GPU/socket or high-speed connector.
- Validate temperatures of the cards, switch, printed supports, intake air and nearby furniture under intended simultaneous load. No thermal or furniture-load qualification is claimed from the photo.

## 6. Main-case orientation

The default remains an upright tower. Rotating it on the tabletop may shorten or simplify the rear cable route, provided all feet remain supported and its vents and existing cables remain clear. Check the footprint before moving it.

Laying the case on its side is a separate placement change requiring identification of the case, ventilation layout and cooler. Do not use the glass panel as the load-bearing base. There is no need to lay the main PC down merely to evaluate the lower-shelf arrangement.

## 7. Why the A770 is worth qualifying

The important distinction is a documented software route, not a larger per-card memory pool. Intel's current PyTorch prerequisite documentation explicitly lists Arc A-Series with Windows 11 and WSL2 Ubuntu 24.04/26.04. It describes Windows host drivers plus Intel user-mode compute runtime inside WSL; a Linux kernel GPU driver is not installed inside WSL for this path. [S03]

Upstream llama.cpp lists A770 among verified SYCL devices and documents Windows/Linux operation, device selection, and multi-card layer splitting. That supports testing A770 inference; it is not validation of this exact Ryzen/RTX/switch/three-card combination. [S04]

The first trial should use a separate environment or inference service, preserving the working NVIDIA/CUDA application and its current model default. Verify Intel enumeration, VRAM, intended model output, training backward pass if needed, actual performance and restart behavior. Only then assess a three-Intel-card deployment and the switched link.

Keep NVIDIA and Intel as separately addressable capacity initially. Do not promise seamless CUDA+XPU distributed training, a unified 64 GB allocation, universal CUDA-kernel compatibility, or throughput inferred from vendor FLOPS. No A770-versus-S80 training benchmark was performed for this addendum.

## 8. Power and purchase state

The owner's **1000 W external PSU target remains unchanged**. Intel quotes 225 W TBP for its A770 Limited Edition; that is not independent verification of this ASRock OC card's configured power limit. Record the actual ASRock stock/maximum limits and cable requirements before finalizing the three-card budget. [S05]

Three reference 225 W boards total 675 W by arithmetic. Do not treat that illustrative total as a measured ASRock shelf draw. Allow separately for the switch, fans and conversion/control electronics. GPU board power already includes its slot contribution; do not add another 75 W per card on top.

This ASRock requires six GPU-side 8-pin connections across three cards, plus separate appropriate backplane feeds. PSU-side modular pinouts and safe cable loading must be checked for the exact PSU. Do not reuse an S80-specific adapter for the Intel cards. [S01]

The live Amazon response identified the card but did not provide a dependable checkout price. **No current A770 price or new complete-project total is asserted.** Record exact seller, condition, warranty, returns, delivered price and quantity availability before comparing against the historical S80 offer.

## 9. Release sequence for the next AI or engineer

1. Obtain the furniture and routed-cable measurements from Section 3.
2. Confirm whether the owner chooses A770 instead of S80; external card count stays three unless explicitly changed.
3. Close one-card host/runtime qualification before bulk GPU purchase.
4. Confirm the actual switch/cable combination, upstream x4 support, firmware, local slot power and return terms. A770 does not remove this cost or compatibility gate.
5. Import actual card, PSU and switch dimensions into the CAD; check insertion path, operating envelope and all service/airflow keepouts.
6. Choose PSU-below or PSU-beside using measured clearances; revise cut list and mechanical supports, not the electrical architecture, unless necessary and approved.
7. Print interface coupons/prototypes, dry-fit unpowered, then load-test and qualify thermals progressively.
8. Issue a new consolidated blueprint and CAD revision only after these measurements and decisions; retain parent history and state what was actually tested.

## References

[U01] Existing conversation attachment: `QOVARYX_3xS80_External_GPU_Shelf_Blueprint_v0.9.md`, Sections 1, 2, 4, 7 and 8. This is a prior design record, not independent hardware validation.

[U02] Owner's current photograph of the PC on a wooden table, lower shelf visible. No dimensions or furniture rating supplied.

[S01] ASRock — exact A770 PG 16GO specifications:  
https://pg.asrock.com/Graphics-Card/Intel/Intel%20Arc%20A770%20Phantom%20Gaming%2016GB%20OC/

[S02] Moore Threads — S80 manufacturer specifications:  
https://en.mthreads.com/product/S80

[S03] Intel — PyTorch prerequisites, reviewed 2026-09-05; page dated 2026-08-21:  
https://www.intel.com/content/www/us/en/developer/articles/tool/pytorch-prerequisites-for-intel-gpu/2-14.html

[S04] Upstream llama.cpp — SYCL backend documentation (moving master; pin a tested commit before deployment):  
https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md

[S05] Intel — A770/A750 Limited Edition board power and connector explanation:  
https://www.intel.com/content/www/us/en/support/articles/000092523/graphics.html

[S06] Owner's link and resolved Amazon product identity, not a price guarantee:  
https://a.co/d/007Eq3cl  
https://www.amazon.com/dp/B0CDM3QK7Q
