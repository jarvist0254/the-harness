# Status, authority and conflicts

## Collection scope

The complete Library folder `/Harness Project` was enumerated recursively. Every file in that returned folder inventory was downloaded, including current docs, old drafts, alternate branches and ZIP handoffs. Separate title/content searches added the python-gpu-maximize overview, older shelf copies, the cluster-shell spec and the adaptive compute note. Source originals are preserved under `sources/library`; the inventory and checksums are in `records`.

This is all material resolved as relevant to the harness, J-Link and PyRe predecessor during this retrieval. Library search is ranked retrieval; it cannot certify that every relevant sentence across unrelated files was found. Unrelated school, marketing and personal documents were not copied.

Latest retrieved project modification: 2026-09-30 15:03 UTC. New research: 2026-10-04; cross-vendor P2P verdict and plan 2026-10-05 03:21 UTC (docs/10). The initial package assembly used Linux without E: access. This Windows-side continuation inspected E:\the_harness and the bounded PyRe/python_gpu source paths described in 04_PYRE_INTEGRATION. The recovered source copies remain unchanged.

## Authority

1. User's current instructions: four external cards, planning around 8 GB per card, vendor-flexible design and thorough J-Link/PyRe exploration with available smoke tests. Recorded engineering consequence for "vendor-flexible design": for pooled capacity, four same-vendor cards strictly dominate any mixed-vendor population, because a mixed population can only ever use the host-staged path while a same-vendor population also gets that vendor's own P2P subject to a directed probe (§2.2). "Vendor-flexible" remains valid for task-pool placement, not for peer capacity. Retain the recorded one continuous print/spool, metal fasteners and integrated PSU/fan-plenum requirements. Existing RTX 5070 Ti is treated as a separate host/display card; no new purchases are recorded.
2. `10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md` (2026-10-05) — authoritative for cross-vendor P2P, peer access, collective-library support and transport-family viability. It extends 02, 05 and 09 and supersedes no document.
3. This 2026-10-04 update register, for the unresolved choices listed below.
4. Original current-folder precedence: README_FIRST, DIMENSION_AUTHORITY_AND_TBDS, MASTER_BLUEPRINT, ASTRA_FREECAD_HANDOFF, then other current files.
5. Archived branches: context only.

Never silently turn a planned geometry or assumed power number into a verified physical measurement.

## Four-card amendment — 2026-10-04

The current user instruction supersedes recovered exactly-three/no-four rules. Target bays A–D and use all four E1 CPU x4 branches; no branch remains reserved. All four branches being consumed is a bandwidth/mechanical statement; the four separate root ports are the NOT_SUPPORTED case for peer access (§2.2). Archived documents retain their original decisions as recovery evidence.

User confirmed one integrated core with GPU overhang allowed: restructure the entire core, with no appended fourth module. Four parallel 68 mm allowances would require 334 mm width; the 48 mm limit applies only to a contained single-row arrangement and is not a new card-selection cap. Tetris studies compare parallel, rolled, tiered, opposed and orthogonal arrangements plus alternative installed orientations of the same print envelope. Prioritize three upright cards with the fourth rolled flat above, on the core's own supports; actual interfaces/load paths remain unmeasured. See 01_HARNESS_MASTER.

Four nominal 8 GB cards provide 32 GB physical inventory. The separate nominal 16 GB 5070 Ti brings inventory to 48 GB if it participates, without creating one transparent allocation. Planner examples use hypothetical MiB samples and subtract modeled overhead independently.

Current host discovery: MSI PRO X870-P WIFI (MS-7E47), Ryzen 7 7700, NVIDIA RTX 5070 Ti and AMD Radeon integrated graphics. AMD shared-memory capacity is not another purchased discrete card. BIOS bifurcation, external receivers and four physical links remain unmeasured.

## Decisions reconciled

| Topic | Recovered conflict | Current disposition |
|---|---|---|
| First cards | v2 names 3 RTX 3060 Ventus 2X; conversation later considers 5050/5060, Intel and AMD | Card purchase is OPEN. 3060 dimensions are historical fit examples only. No card-specific chassis commitment. |
| GPU budget | Original under $1,000; old BOM totals $1,079.97 before tax | Old price snapshot is not an approved purchase list. Requote after software/fit decisions. |
| Printer | v2 identifies Ender-3 S1 Pro | Carry as recorded baseline; verify the actual machine before slicing. |
| CAD tool | Some files say Blender/.blend; newer handoff says FreeCAD | Parametric FreeCAD is latest documented handoff. Blender remains possible if dimensional gates are preserved. |
| Filament | README/material plan choose ZYLtech 5 kg; purchase BOM says SUNLU | Plain PETG, one actual continuous 5 kg spool, remains baseline. Exact brand/price OPEN; verify winding and print behavior. |
| PSU | Older docs RM1000e 140 mm deep; dimensional authority RM1000x 160 mm | Exact PSU SKU and envelope OPEN. Keep dimensions parametric. Do not use e and x interchangeably. |
| PSU capacity | 1,000/1,200 W earlier; user asks for 20% headroom | Size from selected card board power plus non-overlapping local overhead, connector inventory and transient requirements. 1,000 W is an option, not a mandatory purchase. |
| Cable sections | Two current documents list different starting trunk sizes | Treat dimensional authority/airflow values as minima; size trunks to the real bundle. Larger power trunk may be required. |
| Handoff filename | HANDOFF_STATUS mentions missing ASTRA_HANDOFF_PROMPT in current | Use current ASTRA_FREECAD_HANDOFF.md. The differently named prompt is in an archived alternate branch. |
| Receiver CAD | Old package advertises ADT downloadable ZIP | Both official download URLs returned HTTP 404 in this session. Receiver dimensions remain TBD; no fixed hole pattern released. |
| VRAM | Aggregate capacity sometimes described as pooling | J-Link delivers explicit placement/sharding over a host-staged bridge. Transparent arbitrary allocation across vendors is SETTLED-UNSUPPORTED, not open research: architecturally excluded on Windows by specification, and no supported mechanism exists on Linux consumer hardware as of 2026. Do not spend further budget here. |

## Revalidation findings

MSI's official PRO X870-P table lists E1 CPU x16 with x4/x4/x4/x4 bifurcation and E4 chipset Gen4 x4 sharing bandwidth with M2_3. Runtime enumeration must confirm link state and BIOS behavior. Bifurcation does NOT create a P2P domain: the four branches remain separate CPU root ports, which is precisely the PCI_P2PDMA_MAP_NOT_SUPPORTED case. This source establishes lane counts and bandwidth sharing only — it is not evidence that four bifurcated cards can peer. **The topology gate is the kernel's chipset allow-list plus BIOS ACS/IOMMU state, not the presence of a PCIe switch** — an AMD Zen host (`family >= 0x17`) passes it without a switch, and this host **is** AMD AM5, so no switch chassis is required for an Intel Arc arm; a switch is only needed where the root complex is not allow-listed (notably consumer Intel desktop chipsets). The x4 caveat still stands on those correct grounds: each of the four branches must independently pass the gate, every verified-working rig in the Intel evidence uses x8 links, and a Gen4 x4 branch halves bandwidth against Intel's own ~20 GB/s unidirectional / 40 GB/s bidirectional figures at Gen5 x8. The fourth E1 branch is consumed by bay D; further pods need additional transport capacity.

Official AMD documentation currently exposes both a legacy Radeon 7.2.1 matrix and a newer consolidated ROCm matrix. Pin the exact GPU/OS/driver/runtime tuple from the appropriate matrix. The legacy page alone must not be used as a blanket statement of latest support.

## No-hardware boundaries

Measured host population: ONE discrete GPU (RTX 5070 Ti, 16303 MiB, 00000000:01:00.0), ONE AMD integrated APU GPU (Raphael, VEN_1002 DEV_164E, shared system memory, no dedicated VRAM), ZERO Intel GPUs (exhaustive scan including hidden and disabled), C:\Windows\System32\ze_loader.dll absent. Directed peer pairs possible on this host: ZERO. No two-card or four-card peer experiment is runnable here; this is a hardware fact, not a software defect. No four-card VRAM capacity, inference speedup, pod power draw or thermal result has been measured. No new GPU purchases, driver changes, BIOS changes or PyRe code changes were made. Validation records distinguish planner checks, tiny compute/transfer probes on installed devices and future discrete-card qualification. Smoke timing is not a representative bandwidth benchmark.

The experimental `j_link/opencl_executor.py` runs one residual neural workload across the installed NVIDIA/AMD pair, with unique resident weights, eight actual kernels and independent CPU parity at every layer. Both vendor orders passed; corruption of a real forwarded activation produced a measured failure. This establishes the bounded execution precursor, not four-card dedicated-VRAM capacity. See its source-specific acceptance receipt before reusing a result after code changes.

The original full-model Vulkan fixture executes Qwen3-0.6B Q8_0 across both installed GPUs, with 29/29 layers offloaded in backend logs, but fails measured CPU-logit parity in both orders. That failure remains preserved. A later, separate CPU-dequantized F32 fixture now passes the fixed CPU comparison in both device orders; matrix runs and four host-side corruption controls also pass their scoped acceptance. See `../records/root_continuation_20261004/FP32_FRESH_NUMERICAL_ACCEPTANCE_20261004T1910Z.json`. This does not qualify the original Q8 model, Intel execution, P2P or four-card capacity. Native HIP computation passed a separate 1 MiB affine test. A local Intel DPC++ compiler is callable and compiles the SYCL fixture, while actual GPU execution remains NOT_CHECKED. See `08_VENDOR_DEVELOPER_TOOLS.md` and `09_FULL_GOAL_GATE_REGISTER.md`.

The earlier Tetris packing SVG and revision-2/3 collision trials remain historical. The current editable integrated FreeCAD core and saved-BRep preview are under `records/cad_draft_20261004`. Revision 4 moves four posts into the gaps between the upright cards and stops them below the rolled top card. Both compact and large hypothetical card bodies are clear in independently checked, connected solids, measuring 188 × 200 × 150 mm and 188 × 200 × 199 mm. The printed envelope excludes the authorized GPU overhang. Exact contacts, receiver/PSU/fan/cable interfaces, loads and print release remain unqualified.
