# J-Link and the Harness — achievement targets and acceptance criteria

Written 2026-10-05. **This document is framed as what must be achieved, not as what is impossible.**

Its purpose is to let a reviewer with no prior context — human or model — judge the problem fresh.
Every target below states a binary, testable acceptance criterion and the evidence any proposed
solution must beat. Where a target is currently unmet, that is recorded as *status*, never as a
verdict. Section 6 lists the claims most worth attacking and exactly what evidence would overturn
each one.

Companion documents: `10_JLINK_CROSS_VENDOR_P2P_VERDICT_AND_PLAN.md` holds the full research, the
first-hand-vs-delegated provenance split, and the measured host inventory. `09_FULL_GOAL_GATE_REGISTER.md`
holds the gate register. This document is the target list; those are the evidence.

---

## 1. Definitions used in the acceptance criteria

These are fixed so that a claimed result cannot be reinterpreted after the fact.

- **Dedicated VRAM** — memory physically on a discrete GPU's own DRAM, reported by that GPU's driver
  as device-local. Shared host memory exposed to an integrated GPU is **not** dedicated VRAM.
- **Direct peer access (P2P)** — one GPU reads or writes bytes that are resident in *another* GPU's
  dedicated VRAM, with the payload never copied into host system memory. Verified by a residency
  delta on both endpoints (§5, control R), not by a success code.
- **Host-staged transfer** — payload traverses host system memory between the two GPUs. The CPU may
  or may not be in the *control* path; if system memory is in the *data* path, it is host-staged.
- **Directed pair** — an ordered (source, destination) pair. A→B passing does not qualify B→A.
  For *n* devices the directed off-diagonal pair count is **n(n−1)**.
- **Capacity aggregate** — a single workload successfully using more bytes of dedicated VRAM than any
  one installed GPU physically has.
- **Peer bandwidth** — GB/s measured on a direct peer path, with control N1 (§5) run at the same
  buffer sizes on the same rig to establish the host-staged baseline for comparison.

---

## 2. Achievement targets

### T1 — Aggregate dedicated VRAM beyond a single card

**Achieve:** one workload uses more dedicated VRAM than any single installed GPU contains, with the
excess resident on other GPUs' dedicated VRAM rather than in host memory.

**Acceptance criteria (all required):**
1. A named workload (model, quantization, context length) runs to completion producing correct
   output, with peak dedicated-VRAM usage recorded per GPU.
2. Sum of per-GPU peak dedicated usage > the largest single GPU's capacity, **and** host-memory
   residency of model weights is reported separately and does not account for the excess.
3. Numerical parity against a single-device reference within a pre-declared tolerance, with the
   tolerance declared *before* the run.

**Status: UNMET.** No four-card or two-card aggregate result has been measured on this host. The
measured population is one discrete GPU, so the target is not yet reachable here (§3).

**Evidence a solution must beat:** the recorded Q8_0 attempt at aggregate inference failed numerical
parity — 99,853 of 151,936 logits outside tolerance on the default path, 99,891 on the reverse path —
and the corruption control was inconclusive because the baseline already failed
(`records\vulkan_llm_qualification_20261004\whole_model_qualification_receipt.md`). Any new attempt
must explain that failure or avoid it, and must not use the dequantized F32 fixture as the reference.

### T2 — Direct peer access between two physical GPUs, same vendor

**Achieve:** a measured direct peer copy or peer kernel access between two discrete GPUs of the same
vendor, with residency evidence.

**Acceptance criteria:**
1. `canAccessPeer`-class query returns true for the directed pair, recorded separately in **both**
   directions.
2. A transfer of ≥64 MiB completes with a **checksum match** on the full payload.
3. **Residency evidence** (control R): source and destination dedicated-vs-shared byte counters
   sampled before and after, showing the payload left dedicated VRAM on the source and arrived in
   dedicated VRAM on the destination.
4. **Control N1** run at the same sizes on the same rig: the host-staged two-hop path is materially
   slower. If the "P2P" number is at or below the host-staged number, it is host-staged and the
   target is not met.
5. Peer bandwidth reported with link generation and width (e.g. Gen5 x8), since bandwidth scales with
   both.

**Status: UNMET on this host** (one discrete GPU; zero directed pairs constructible). **MET elsewhere
by third-party report** — see §4 for what is on record and at what confidence.

### T3 — Direct peer access between GPUs of *different* vendors

**Achieve:** T2's criteria satisfied where source and destination GPUs are from different vendors
(any of Intel↔AMD, Intel↔NVIDIA, AMD↔NVIDIA).

**Acceptance criteria:** T2's 1–5, plus:
6. Both endpoints are discrete GPUs with dedicated VRAM (an integrated GPU on shared host memory does
   not qualify as an endpoint).
7. The vendor of each endpoint is recorded from the driver, not inferred from the device name.
8. The mechanism is named precisely — which API, which handle type, which kernel path — so it can be
   independently reproduced.

**Status: UNMET. No working instance is known to this project on any host, on any OS.** This is the
hardest target and the one the project has spent most of its research budget on. The evidence
accumulated against it is extensive but **it is evidence, not proof**, and §6 lists the specific
points where it is weakest and most worth attacking.

**Known best partial results on record:** a D3D12 cross-adapter shared-heap copy NVIDIA→AMD passed
256 KiB verification with corruption controls — but the shared resource is backed by system memory
(L0), so it satisfies the *transfer* half of T3 and fails the *dedicated VRAM* half. This is the
closest achieved result and it is host-staged by construction.

### T4 — Four-card harness: physical, electrical and thermal acceptance

**Achieve:** four discrete GPUs installed in the enclosure, running a sustained representative
workload, within stated electrical and thermal limits.

**Acceptance criteria:**
1. Physical fit verified against the actual printed/machined mounting, not the CAD model alone.
2. Each card's negotiated PCIe generation and width read back from the device (`LnkSta`), matching
   the design.
3. Pod power draw measured at the wall under sustained load, against the 100 kW design envelope and
   the actual circuit capacity.
4. Per-GPU and intake/exhaust temperatures logged over a sustained run, with throttle events recorded.
5. No card throttling below its sustained clock for thermal or power reasons.

**Status: UNMET.** No four-card VRAM capacity, inference speedup, pod power draw or thermal result
has been measured. CAD is parametric and unprinted.

**Design constraint discovered this cycle and worth carrying forward:** link width trades directly
against card count on a fixed lane budget. Intel's own first-hand calibration is ~20 GB/s
unidirectional / 40 GB/s bidirectional **at Gen5 x8**; a Gen4 x4 branch has roughly a 6.5 GB/s
realistic one-way ceiling and ~3.2 GB/s for a host-staged round trip. **Two cards at x8 will out-peer
four cards at x4 by a wide margin, while four cards at x4 hold more aggregate capacity.** The target
should state which of those it is optimizing, because the hardware buy differs.

### T5 — Real quantized inference with numerical parity

**Achieve:** a real quantized model (not a dequantized fixture) produces output matching a declared
reference within a declared tolerance, on the target topology.

**Acceptance criteria:**
1. Model file hash matches the declared reference model.
2. Tolerance declared **before** the run and not widened afterward.
3. Reference is a single-device run of the same quantized model — not a higher-precision fixture.
4. A corruption control demonstrates the harness can detect a deliberately corrupted run.

**Status: UNMET / currently RED.** See T1's evidence note. The prepared diagnostic for this is on
disk and runnable on the current host (§7).

### T6 — Verified software baseline with no new hardware

**Achieve:** the software layer is correct, tested and green on the existing host, so that hardware
arrival is the only remaining blocker for T1/T2/T4.

**Acceptance criteria:**
1. Full unit suite passes, exit 0, count recorded.
2. Curated-artifact integrity manifest verifies with zero failures.
3. Every known-RED item either fixed with a regression test, or recorded with its receipt path and an
   explicit statement of what is unresolved.
4. No claim of "fixed" without a re-run command and its raw output.

**Status: PARTIALLY MET, and advanced this cycle.** Measured now, all exit 0:
- `j_link` unit tests **80/80 OK** (was 79; +1 regression test added this cycle)
- `cad` tests **15/15 OK**
- `j_link\planner.py examples\mixed.json` → `PLANNED_NOT_ALLOCATED`, exit 0
- `scripts\verify_adaptation.py` against the newest dated `records\ADAPTATION_SHA256_*.json`
  (currently `..._20261005_110323Z.json`) → **219 checked, 0 failures**, exit 0. Re-pinned this
  cycle: the nine documents corrected during the audit drifted against the prior
  `..._20261004_2148Z.json` manifest, which by convention stays immutable and still records that
  drift. Same 219 paths, current hashes, `prior_manifest` chained. Reference the manifest by
  newest-by-filename-sort rather than by exact stamp, so the citation cannot dangle on the next
  re-pin — `scripts\nightly_verify.py` resolves it that way automatically.

One real defect was found and fixed this cycle, with the safety property *proved* rather than assumed:
`j_link\device_inventory.py::_parse_bytes_value` had an unconditional `return` that made its entire
string-handling branch unreachable dead code, so string-typed AMD/Intel memory fields always yielded
`None`. Demonstrated by direct execution before and after. The fix cannot loosen the admission gate,
because `_extract_amd` hardcodes `observed_free_bytes: None` and `_parse_bytes_value` is called only
from the AMD and Intel extractors — verified end-to-end: both string and integer inputs still end at
`eligible_count = 0`. Neither edited file is among the 219 pinned manifest paths, confirmed by direct
grep, so the integrity gate is untouched.

**Remaining RED items** are listed with receipt paths in doc 10 Part 3. The two that most affect T5
are the completion/FD adapter (v3 QA: 10 methods, 9 failure events, 1 error, 1 pass, returncode 1)
and the L0 collector (4 proved defects).

### T7 — Nightly build and continuous verification

**Achieve:** an unattended nightly job that builds every component, runs every test, verifies the
artifact manifest, and publishes a dated receipt — so a silent regression is caught within a day
rather than at hardware-arrival time.

**Acceptance criteria:**
1. Nightly job runs unattended and produces a dated receipt with pass/fail per component.
2. Version pins recorded per run: OS build, GPU driver, CUDA/ROCm/oneAPI, kernel (for the Linux arm),
   compiler, Python, and every third-party commit hash.
3. Failure is loud — a RED nightly blocks or alerts rather than being recorded and ignored.
4. The job runs on the current host today, without waiting for hardware.

**Status: NOT STARTED.** This target needs no new hardware and is the cheapest way to protect every
other target.

**Why it matters specifically here, with evidence:** the Intel multi-GPU stack regressed silently
between releases — NEO **25.40 worked**, **25.44/25.48 broke** multi-Battlemage device enumeration,
and it was only resolved by kernel ≥ 7.1 plus compute-runtime ≥ 26.18/26.22. A nightly pin-and-probe
job is the only thing that catches that class of break before it invalidates a hardware investment.

---

## 3. Current host capability, measured

Recorded so a reviewer knows what is and is not reachable *here*, independently of any target.

Measured this cycle by three independent methods (`Win32_VideoController`, `Get-PnpDevice` including
hidden and disabled devices, `nvidia-smi -L`) plus the project's own OpenCL enumerator:

| Item | Measured value |
|---|---|
| Discrete GPUs | **1** — NVIDIA GeForce RTX 5070 Ti, 16303 MiB, `00000000:01:00.0` |
| Integrated GPUs | **1** — AMD Radeon(TM) Graphics, `VEN_1002 DEV_164E` (Raphael), shared host memory, classified `SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM`, `host_unified=true` |
| Intel GPUs | **0** — exhaustive scan including hidden and disabled |
| Level Zero loader | `C:\Windows\System32\ze_loader.dll` **absent** |
| Directed peer pairs constructible | **0** |
| Host | AMD AM5 — MSI PRO X870-P WIFI, Ryzen 7 7700 |
| OS | Windows (win32) |

**Consequence for the targets:** T1, T2, T3 and T4 are not reachable on this host, because each
requires at least two discrete GPUs. T5, T6 and T7 **are** reachable now. The AM5 host is
significant for T2/T3 — see §4.

---

## 4. What is already on record elsewhere, and at what confidence

A reviewer should know which prior results are solid, because they change what needs proving.
Confidence grades: **A** = first-hand from a primary source read this cycle; **B** = first-hand from a
vendored third-party artifact read this cycle; **C** = delegated research, not re-verified.

### Grade A — Intel's own platform evaluation guide (doc 863931 rev 1.0, Sept 2025, 27 pp)

Read directly this cycle from the vendored PDF. Establishes, for **Intel B60 Pro** multi-GPU:

- BIOS must **disable PCIe ACS and IOMMU**: *"ACS would route all the data transfer back to the root
  complex. IOMMU would introduce unnecessary address translation. Both features would block the P2P
  transfer."* Verify via `ACS-` in `lspci -vvv`; IOMMU via `intel_iommu=off` in grub.
- Tooling is **`ze_peer`** (P2P) and **`ze_peak`** (bandwidth) from `oneapi-src/level-zero-tests`;
  oneCCL for AllReduce / AllGather / AllToAll.
- **Bandwidth calibration, B60 Pro at PCIe Gen5 x8:** ~20 GB/s unidirectional write between two
  devices, up to 40 GB/s bidirectional. Gen5 x8 = 32 GB/s bus, **24 GB/s payload** after 128/130
  encoding and TLP overhead; 22.7 GB/s D2H measured is called "reasonable".
- **4-GPU ring recipe:** `ze_peer -t transfer_bw --parallel_pair_targets 0:1,1:2,2:3,3:0 -z 134217728
  -o write -v -c` → ~20 GB/s per pair, **79.37 GB/s total** for 512 MB.
- **Known tool defect:** with `-c`, per-pair bandwidth is wrong while the total is correct. Take
  per-pair numbers from non-`-c` runs.
- Cross-socket P2P is additionally UPI-limited.
- The document is Ubuntu-oriented and contains **zero** occurrences of "Windows".

### Grade B — `intel/compute-runtime#921` (vendored JSON, 27 comments, closed/completed)

Title: *"Multi-BMG Level Zero device enumeration broken by deferred internal-engine init (regression
NEO 25.40→25.44, Arc Pro B50/B60/B70)"*. Labels `Type: Bug`, `OS: Linux`, `Status: Merged`. Read
directly this cycle. Establishes:

- The product family is **Intel Arc Pro B50 / B60 / B70** (Battlemage). Device IDs **B60 = `0xe211`**,
  **B70 = `0xe223`**. `sycl-ls` reports `Intel(R) Arc(TM) Pro B60 Graphics`.
- **`zeDeviceCanAccessPeer` returned `canAccess=1` in both directions on 2× Arc Pro B60**
  (`P2P 0 -> 1: ze_result=0x0 canAccess=1`, and the reverse). This is a direct T2-class result.
- **It works on an AMD AM5 motherboard.** One reporter's rig: *"2x Intel Arc Pro B60, device ID
  8086:e211 — AMD AM5 / PCIe 5.0 motherboard — Both GPUs linked at PCIe 5.0 x8."* The most recent
  comment (2026-06-28) states: **"Verified P2P works on AM5 host with 7.1.2 kernel, Intel Compute
  26.22.38646.4."** No PCIe switch is mentioned anywhere in the thread.
- **The gate is the kernel's chipset allow-list**, not a switch. Asked directly whether B70s *"can
  actually do P2P DMA if the kernel allow lists the chipset"*, the answer was **"Yes, though make sure
  you have the latest 7.1 kernel."**
- **A silent-corruption hazard specific to this path:** VRAM compression races with peer reads, so
  P2P reads return garbage. Workaround `NEOReadDebugKeys=1 RenderCompressedBuffersEnabled=0`. An Intel
  contributor confirmed it as one of two distinct issues; fixes are merged
  (`e91243a9d03de849f45d8b862a62afd4424cff8b`, `258518f8039afba59c46d98bb7f6f068d12f026d` — both
  vendored on disk as commit snapshots).
- The regression window: **25.40 worked, 25.44/25.48 broke**; root cause was BMG internal
  engine/context init changing from eager to deferred.
- Multi-GPU **Vulkan** is not a fallback: *"atrocious, even negative performance gains per added gpu."*
- Support is thin: *"Seems Arc Pro is low priority (few people have them)."*

**This is the strongest T2 evidence the project holds, and it is directly relevant to the existing AM5
host.** It also means an Intel Arc arm does **not** require a PCIe switch chassis on this motherboard,
which lowers the cost of reaching T2 substantially.

### Grade C — delegated research, not re-verified

Extensive findings on cross-vendor transport mechanisms (D3D12 cross-adapter heaps, Vulkan device
groups and external memory, the Linux `pci_p2pdma` whitelist, per-driver dma-buf behaviour in
amdgpu/xe/i915/nvidia, NCCL/RCCL/oneCCL/MSCCL++/UCX, ZLUDA and translation layers, CXL, UALink) are
recorded in doc 10 §1.1–§1.5 with the reasoning and citations the research agents supplied. **They
were not confirmed first-hand this cycle and should be treated as leads.** Doc 10 §6.2 lists exactly
which is which. A reviewer is specifically invited to challenge them (§6).

Also grade C, and **positively unsupported** by both vendored Intel sources:
- Arc Pro **B60 = 24 GB / B70 = 32 GB** VRAM capacities. Doc 863931 contains no occurrence of "VRAM"
  or "graphics memory", and its only "24GB"/"32GB" strings are PCIe **bandwidth** figures (24 GB/s
  payload, 32 GB/s bus). The capacity claims match those bandwidth numbers exactly, so a
  bandwidth↔capacity transcription error upstream is a live possibility. The only capacity-shaped
  evidence is a `lspci` Resizable-BAR line showing `BAR 2: current size: 32GB` on a B70 — a BAR
  aperture, not a stated capacity. **Confirm from Intel ARK before any purchase.**
- The iGPU+dGPU / different-generation compatibility table.
- "Project Battlematrix — up to 8 GPUs, up to 192 GB combined VRAM".
- The 28.00 GB/s measurement with checksum PASS on 268,435,456 bytes, and the ACS-redirect ON→refuse /
  OFF→pass A/B result.

**Blocked verification attempts, recorded honestly:** every `intel.com` and `ark.intel.com` fetch this
cycle returned HTTP 301 to a 404 redirector (4 distinct URLs). The arXiv API returned HTTP 429 on
every attempt, so delegated arXiv *negative*-search counts are unverified and must not be cited.

---

## 5. Verification protocol any claimed result must satisfy

A result that does not satisfy these is not evidence, regardless of how good the number looks. This
section exists because the failure modes below have each been observed in the wild.

**Control R — residency.** Per transfer, sample dedicated-vs-shared byte counters on **both** endpoints
before and after (NVML / ADL / sysfs `mem_info_vram_used` and `mem_info_gtt_used` as applicable). The
payload must be shown to leave dedicated VRAM on the source and arrive in dedicated VRAM on the
destination. Without this, a passing byte comparison cannot distinguish P2P from a host bounce.
**No project found in this cycle's research measures this — it would be a genuine contribution.**

**Control N1 — host-staged baseline.** Run the same buffer sizes through an explicit host-staged
two-hop on the same rig. The peer number must be materially higher. If it is at or below the baseline,
**it is host-staged.** Expected gap on a working peer path is roughly an order of magnitude.

**Control N2 — checksum on every transfer, always.** A success return code is not a correctness
certificate. Two independent observations justify treating this as mandatory: a forced-open kernel
whitelist produced `ZE_RESULT_SUCCESS` on a 256 MB peer copy with **every element wrong** (grade C),
and Intel's Arc compression race returned garbage from P2P reads that reported success (grade B).

**Controls N3–N13** — query-vs-outcome consistency in both directions; ACS on/off on the same boot;
IOMMU on/off; peer-enable env toggle on/off; same-device ceiling; the vendor's documented
compression-disable key for D2D (Intel documents a spurious **2×** bandwidth inflation without it);
cross-generation pair must refuse; iGPU+dGPU pair must refuse; consumer-vs-pro SKU substitution;
single-card sanity benchmark; driver-version regression pair across the pin.

**Control N14 — conformance runs prove nothing about peer access.** At the pinned `level-zero-tests`
commit whose stated purpose was adding `zeDeviceCanAccessPeer` scenarios, every P2P conformance test
is vacuous for two distinct physical cards: one asserts only symmetry (`false == false` passes), two
call the properties query with **no assertion on the result**, the rest assert trivial self-peer
cases, and all skip when device count < 2. **A full PASS on a single-GPU machine is
indistinguishable from a full PASS on a qualified four-card machine.**

**Control V — version pins per run.** OS build, kernel, GPU driver, compute runtime, CUDA/ROCm/oneAPI,
compiler, Python, and every third-party commit hash. The Intel regression window (§4, grade B) is the
reason this is a control and not a footnote.

---

## 6. Claims most worth attacking, and what would overturn them

This section is the point of the document. A fresh reviewer should start here. Each entry states a
claim the project currently holds, and the **specific evidence that would overturn it** — so a
reviewer can disagree productively rather than generally.

| # | Claim currently held | What would overturn it |
|---|---|---|
| 1 | No supported mechanism gives direct dedicated-VRAM peer access between **different** vendors on consumer hardware (T3) | A named API + handle type + kernel path, with control R residency evidence on two different-vendor discrete GPUs. A benchmark number alone is not sufficient — see N1. |
| 2 | Windows cannot do cross-vendor dedicated-VRAM sharing at all | A Windows mechanism whose payload provably stays in dedicated VRAM (control R). Note the known trap: D3D12 cross-adapter heaps are GPU-initiated and CPU-free but live in **system memory**, so they satisfy "no CPU marshaling" while failing T3. |
| 3 | Mixed-vendor Vulkan device groups are impossible | A device group spanning two vendors that passes `VkDeviceGroupDeviceCreateInfo` validation. The claim rests on a requirement for identical extensions/features/properties plus per-ICD enumeration. |
| 4 | Linux `pci_p2pdma` excludes consumer desktop hosts | The whitelist contents in the **specific kernel version** to be deployed. The AMD Zen family blanket-enable is grade C and was not read from source this cycle — #921 confirms the AM5 *outcome* but not the mechanism. Reading `drivers/pci/p2pdma.c` in the target kernel settles it either way. |
| 5 | A PCIe switch chassis is required for four-card peer access | Already **partially overturned this cycle**: #921 shows 2× Arc Pro B60 doing P2P on an ordinary AM5 board with no switch. The open question is whether that extends to **four** cards on bifurcated x4 branches, which no source addresses. |
| 6 | Intel peer access is a throughput optimization, not a capacity unlock | An Intel source or measurement showing a single allocation spanning two Arc cards' VRAM. The ~15% figure and the absence of any capacity claim are grade C; worth checking against Intel's multi-Arc quick-start guide, which is **not vendored** and was not fetchable. |
| 7 | Arc Pro B60 = 24 GB, B70 = 32 GB | **Already flagged as unsupported.** Both vendored Intel sources lack any VRAM capacity statement, and the numbers coincide with that document's bandwidth figures. Intel ARK settles this. Highest-value single check before spending money. |
| 8 | Host staging is the correct baseline architecture, not a fallback | A 2024+ result showing consumer-GPU workloads using direct P2P as the normal path. Counter-evidence already found: ThunderEP (**arXiv:2609.40093**, fetched first-hand) is built entirely around optimizing CPU-memory-traversing transfers on RTX 4090/5090 — *same vendor* — and reports 2.00× dispatch / 1.53× combine over NCCL. Its own framing: *"on PCIe-based consumer GPU systems, where all inter-GPU transfers traverse CPU memory."* |
| 9 | Four same-vendor cards dominate a mixed-vendor population for pooled capacity | A mixed-vendor configuration that achieves direct peer access at all, which would make claim 1 false too. These stand or fall together. |
| 10 | Nothing published demonstrates cross-vendor direct VRAM peer access | Any paper or repo doing it. **This claim was overstated once already this cycle and corrected** — an earlier draft asserted arXiv had zero relevant works, which was false (ThunderEP is directly relevant, and confirms claim 8 instead). Search coverage was limited by arXiv API rate limiting, so absence of evidence here is weak evidence of absence. |

**Two structural notes for a reviewer.** First, claims 1, 2, 3 and 9 are interdependent: overturning 1
largely overturns the others. Second, the project has a documented history of false positives in this
exact area — silent corruption reported as success, benchmark-only evidence, stubbed device paths,
unverified vendor claims treated as fact — so §5's controls are not bureaucracy. They are the
response to observed failure.

---

## 7. Work that can proceed immediately, with no hardware

Ordered by value. None of this waits on a purchase.

1. **T7 nightly build + pin recording.** Cheapest protection for every other target, and the Intel
   regression window is concrete evidence of why. Runs on the current host today.
2. **Control R residency harness.** Build the measurement, not just the transfer. It is the
   discriminator every other claim needs, nobody in this cycle's research has it, and it is
   implementable against the single installed GPU as a self-test before any second card arrives.
3. **T5 parity diagnostic.** The prepared run is on disk with a hash-matched model
   (639,446,688 bytes) and the attempt-5 binaries present. This is the one open item that could
   change the numerical picture. Do not substitute the F32 fixture; do not widen tolerances.
4. **T6 RED items.** Completion/FD adapter (v2 and v3 findings) and the L0 collector's four proved
   defects. Pure software, no hardware dependency.
5. **ThunderEP's three optimizations applied to the host-staged bridge** — remove ring relay hops so
   each boundary crossing is a single source→host→destination path; move boundary data with DMA/copy
   engines rather than compute shaders so transfer and compute overlap; minimize completion-flag
   polling in host memory. Measured headroom is roughly **2×, not orders of magnitude**.
   `j_link\opencl_executor.py` already records the right per-stage timing to prove the gain.
6. **Confirm Arc Pro VRAM capacities from Intel ARK** (claim 7). Retry when intel.com resolves. This
   gates any purchase decision and takes minutes once reachable.
7. **Read `drivers/pci/p2pdma.c` in the kernel version that would actually be deployed** (claim 4).
   Settles whether the AM5 allow-list mechanism is real, which determines whether a four-card Intel
   build needs a switch chassis.

---

## 8. Explicit non-targets

Recorded so effort is not spent re-deriving them. These are out of scope by decision, not by failure:

- **Transparent pooled VRAM** — an arbitrary unmodified GPU program allocating one buffer across
  multiple vendors' VRAM. Not pursued. Any design assuming it is invalid.
- **Cross-vendor collective operations** (all-reduce / all-gather / tensor parallelism spanning
  vendors). No collective library can express a mixed-vendor communicator, so the request/response
  contract must not expose one. Placement must be coarse-grained — whole layers, whole experts, whole
  stages — maximizing compute per boundary byte.
- **Cross-vendor atomics or a shared address space.** Not pursued.
- **NVLink / xGMI / UALink-class bandwidth on consumer parts.** Not attainable; design against PCIe.

---

## 9. What "done" looks like

The objective is met when **T1 through T7** each have a dated receipt satisfying their acceptance
criteria under §5's controls, and when the four-card harness runs a sustained representative workload
inside its electrical and thermal envelope.

A reasonable intermediate milestone, reachable with a single purchase and no unresolved research
question: **T2 + T6 + T7 satisfied on two Intel Arc Pro cards in the existing AM5 host running Linux,
with control R and N1 evidence.** That is a real, measured, direct peer-access result on hardware the
project already has a verified-working third-party precedent for (§4, grade B). It does not require
solving T3, and it would be the first genuine P2P result this project has ever recorded.
