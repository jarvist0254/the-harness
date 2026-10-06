# The Harness — JE Horizon

Consolidated on 2026-10-04; cross-vendor P2P verdict and plan added 2026-10-05. Owner: Thomas Jarvis.

This package adapts the recovered chassis project to four external 8 GB GPU cards, with the existing RTX 5070 Ti kept separate as the host/display card. It combines J-Link research, an experimental NVIDIA/AMD residual neural workload, native developer tools, transfer probes, a capacity planner and editable integrated-core CAD. A fixed dequantized F32 Vulkan model fixture now passes CPU-logit parity across NVIDIA/AMD in both device orders, with four corruption controls detected. The original Q8 model remains unqualified. **Cross-vendor direct dedicated-VRAM peer access does not exist as a supported mechanism on consumer GPU hardware, on Windows or on Linux, as of 2026** — see `docs/10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md`. Intel *same-vendor* multi-Arc peer access is real, but Linux-only, Arc Pro B60/B70-only, and a **~15% throughput optimization rather than a capacity unlock**. Four-card capacity and production fit remain unqualified.

## Start here

1. `docs/00_STATUS_AND_PRECEDENCE.md` — what was recovered, current decisions, conflicts, missing access.
2. `docs/01_HARNESS_MASTER.md` — mechanical, electrical, printing and expansion plan.
3. `docs/02_J_LINK_RESEARCH.md` — practical ways to use aggregate VRAM across Intel, AMD and NVIDIA **via explicit sharding over a host-staged bridge**; cross-vendor direct VRAM P2P is settled-unsupported (see item 16).
4. `docs/03_EXPERIMENT_RUNBOOK.md` — same-vendor and mixed-vendor qualification sequence.
5. `docs/04_PYRE_INTEGRATION.md` — current on-disk source audit and integration boundary.
6. `docs/05_PRIMARY_SOURCES.md` — current primary sources and findings.
7. `docs/06_LOCAL_AGENT_HANDOFF.md` — actionable instructions for the Windows-side coding session.
8. `docs/07_5050_CANDIDATE.md` — the added Best Buy candidate and fit/VRAM implications.
9. `sources/library/Harness Project/current/` — complete recovered latest mechanical documents.
10. `docs/RECOVERED_CURRENT_COMPLETE.md` — those current text documents combined without abridgment.
11. `sources/library/Harness Project/archive/` — earlier designs retained for traceability.
12. `docs/08_VENDOR_DEVELOPER_TOOLS.md` — actual AMD HIP kernel and locally extracted Intel compiler results.
13. `docs/09_FULL_GOAL_GATE_REGISTER.md` — full goal and explicit remaining evidence gates.
14. `cad/README.md` — actual integrated-core BRep drafts, both body-clear envelope fixtures and current preview.
15. `records/root_continuation_20261004/CONTINUATION_ACCEPTANCE.md` — actual requested-provider usage, current quota observation, accepted fixtures and open full-goal gates.
16. `docs/10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md` — **read first for any P2P, peer-access or transport question.** The cross-vendor verdict with primary sources, the measured host inventory, the settled-unsupported list, the genuinely-open list, the host-staged architecture that actually works, the performance ceilings, the directed test matrices with thirteen negative controls, and the software that must be fixed before any hardware arrives.
17. `docs/11_JLINK_ACHIEVEMENT_TARGETS.md` — the achievement target list (T1–T7) with acceptance criteria, plus the **claims-most-worth-attacking** table. **The intended entry point for a fresh reviewer.**

## Install on E:

Extract the archive, then run this in ordinary PowerShell from the extracted `the_harness` directory:

```powershell
powershell -NoProfile -File .\install_to_E.ps1
```

The installer targets `E:\the_harness`. It copies new files, skips identical files, and refuses conflicting existing files before copying. It does not require administrator privileges. Initial assembly ran on Linux without local-drive access; the 2026-10-04 Windows continuation verified this installed directory directly. The installer itself was not rerun here.

## Work before buying cards

Python 3.10+; the planner has no third-party dependencies:

```powershell
python .\j_link\planner.py .\j_link\examples\mixed.json
python -m unittest discover -s .\j_link\tests -v
# verify against the NEWEST dated adaptation manifest (re-pinned forward; see note below)
python -B .\scripts\verify_adaptation.py (Get-ChildItem .\records\ADAPTATION_SHA256_*.json | Sort-Object Name | Select-Object -Last 1).FullName
.\scripts\audit_local_projects.ps1 -Roots @('E:\JE_Horizon\pyre\pyre-release-source\src\pyre', 'E:\python_gpu\portable_core\python_gpu_maximize') -OutputDirectory 'E:\the_harness\records\local_audit_narrow'
```

The planner reserves per-device overhead and assigns whole ordered layer blocks. Each current example models four 8 GB cards: 32,768 MiB hypothetical free capacity, 26,624 MiB after modeled reserves, and 24,576 MiB of synthetic blocks. The same workload fails with three cards. These are capacity fixtures, not measured model sizes. The planner does not allocate VRAM or launch inference.

`verify_adaptation.py` checks the explicitly supplied curated code/document/evidence manifest. Its no-argument default remains the frozen earlier `ADAPTATION_SHA256_20261004.json`, which does not describe later edits. Use the dated manifest above for its stated curated artifact scope. Hash verification establishes file integrity, not hardware qualification or acceptance of provider proposals. The earlier README referenced a nonexistent `FULL_CONTINUATION` manifest; that broken command is replaced by the actual dated manifest. The original `records/PACKAGE_SHA256.json` remains the immutable imported baseline.

Manifests are re-pinned forward, never edited in place. The newest `records/ADAPTATION_SHA256_*.json` re-pins the same 219 curated paths at current hashes after this cycle's documentation corrections, chaining `prior_manifest` back to `ADAPTATION_SHA256_20261004_2148Z.json`; that predecessor remains immutable and still reports the nine corrected documents as drift, which is the intended historical record. When a curated document is deliberately edited, expect the current manifest to report it and re-pin with a new dated file rather than modifying an existing one — always verify against the newest by filename sort, as the command above does. `docs/10`, `docs/11` and `scripts/nightly_verify.py` are not yet pinned and should be added at the next re-pin.

With the existing NumPy/PyOpenCL installation, the experimental executor runs eight unique residual MLP layers across NVIDIA and AMD GPUs:

```powershell
python -B .\j_link\opencl_executor.py
python -B .\j_link\opencl_executor.py --reverse
python -B .\j_link\opencl_executor.py --inject-corruption
```

The first two commands require measured CPU-reference parity and exit 0. The corruption control must execute the remaining layers, detect a numerical mismatch, and exit 1. Missing required devices return `NOT_CHECKED`/exit 2. See `records/J_LINK_ACCEPTANCE_20261004.md` for final source-specific evidence, actual model-provider work and integrity checks, and `docs/03_EXPERIMENT_RUNBOOK.md` for the separate four-card acceptance gates. The small artificial memory policy demonstrates placement; it cannot establish an 8 GB capacity result.

The highest-value work here that needs no new hardware is itemized in `docs/10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md`. Its Part 3 lists the software still RED with no hardware dependency — the completion/FD adapter v2+v3 findings and the original L0 collector's four proved defects. Its Part 4 gives the recommended execution order, whose top no-hardware item is adopting ThunderEP's three host-staged optimizations: remove ring relay hops so each boundary crossing is a single source→host→destination path, move boundary data with DMA/copy engines instead of compute shaders, and minimize completion-flag polling overhead in host memory.

## Repositories

`repos/` contains pinned upstream checkouts of llama.cpp, Intel compute-benchmarks and AMD TransferBench. See `records/repositories.json` for exact commits and submodule state. These are research dependencies, not installed drivers. Follow their own licenses and build instructions. Do not replace your PyRe/python_gpu repositories with them.

## Completion boundaries

- Recovered files and new planning materials: packaged and checked.
- E: installation and bounded PyRe/python_gpu source audit: inspected on this Windows host; see the amended integration and validation records.
- Installed NVIDIA/AMD OpenCL kernels and host-staged transfers: six directed size cases passed, with corruption detected. Vulkan host-staged copies and D3D12 shared cross-adapter heap copies passed 256 KiB verification and corruption controls. Four CPU-backed RPC workers passed arithmetic and transfer checks. These results do not certify four-GPU inference or direct VRAM P2P. The D3D12 result's L0/system-memory classification is now **specification text, not inference** (Microsoft: "Cross-adapter shared resources are only supported in system memory"). Host staging is also the **documented normal path, not a fallback** — NCCL: "SHM is used between devices when peer-to-peer cannot happen, therefore, host memory is used."
- Installed NVIDIA/AMD residual MLP: eight unique resident layers executed with eight independent CPU comparisons in both vendor orders; maximum final error about 8.35e-6. The corruption control executed all eight layers and failed measured parity. This is a small neural workload using explicit host staging, not an LLM or pooled VRAM allocation.
- Actual AMD-native HIP affine kernel: 1 MiB verified exactly on gfx1036; changed-readback control detected. Intel DPC++ compiles a SYCL fixture, but its installed OpenCL adapter filters both current vendors, so SYCL GPU execution remains `NOT_CHECKED`.
- Real Qwen3-0.6B Q8_0 Vulkan inference: clean pinned build offloaded 29/29 layers across NVIDIA and AMD in both device orders; all 151,936 logits were finite, but CPU parity failed. See `records/vulkan_llm_qualification_20261004/whole_model_qualification_receipt.md`. This is a measured failure being diagnosed, not accepted model inference.
- Later fixed derived-F32 fixture: repaired build and both NVIDIA/AMD orders pass CPU parity over 151,936 logits per order; matrix runs pass 12,288 comparisons per device. Four host-side corruption controls each detect exactly one mismatch. See `records/root_continuation_20261004/FP32_FRESH_NUMERICAL_ACCEPTANCE_20261004T1910Z.json`. This separate CPU-dequantized fixture does not qualify original Q8 inference, Intel execution, direct P2P or four-card VRAM.
- Integrated four-bay CAD revision 4: both compact and large hypothetical card boxes are body-clear in valid one-solid cores, measuring 188 × 200 × 150 mm and 188 × 200 × 199 mm respectively. Posts occupy the gaps between upright cards and end below D; all four bays share the continuous core. Editable FCStd/STEP drafts and `records/cad_draft_20261004/integrated_tetris_revision4_actual_brep.png` show the actual saved geometry. Earlier collision failures remain historical evidence. Contacts, printability, interfaces and loads still need qualification.
- Four-card same-vendor and mixed-vendor execution: pending physical hardware. **Measured host population is one discrete GPU (RTX 5070 Ti) plus one AMD integrated APU on shared system memory; zero Intel GPUs; ze_loader.dll absent — so directed peer pairs possible here are ZERO, and no two-card or four-card peer experiment is runnable on this machine.** For pooled capacity, four **same-vendor** cards strictly dominate any mixed-vendor population. Motherboard x4/x4/x4/x4 bifurcation does **not** create a P2P domain, but the reason is **not** a missing switch: the peer-access gate is the kernel's chipset allow-list plus BIOS ACS/IOMMU state, and an AMD Zen host (`family >= 0x17`) passes it without a switch — so the existing AM5 host (MSI PRO X870-P WIFI, Ryzen 7 7700) needs **no switch chassis** for an Intel Arc arm, and a switch is only required where the root complex is not allow-listed (notably consumer Intel desktop chipsets). The four x4 branches remain four separate CPU root ports, each of which must independently pass that gate, and every verified-working rig in the Intel evidence uses x8 links, not x4 — while a Gen4 x4 branch also halves bandwidth against Intel's own ~20 GB/s unidirectional / 40 GB/s bidirectional figures at Gen5 x8, so prefer fewer cards on wider links if peer bandwidth matters. Installed-device smoke results have narrower scope and are recorded separately.
- Final CAD/STL: pending measured component interfaces, fit, slicer and thermal checks.

J-Link here means JE Horizon's proposed software fabric, distinct from NVIDIA NVLink and SEGGER J-Link.
