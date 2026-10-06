# PyRe GPU and python_gpu integration

## Evidence actually available

The current public PyRe page describes a Windows Python workbench with queues, resource planning and run records. It says acceleration depends on compatible code/hardware and that scripts specify device use. The public guide describes measured transfer-inclusive crossover, parity gating and resource reservation. These are product descriptions, not proof of today's local implementation.

The Library's PYTHON_GPU_MAXIMIZE_OVERVIEW_20260728.pdf describes conservative CPU/accelerator routing, explicit device and per-device VRAM budgets, durable progress, detached resumable runs and warm GPU state. The PDF has malformed content-stream operators; its original bytes are preserved, and extracted text is best effort. The document is historical, not a current source-code audit.

Windows-side source audit on 2026-10-04 identified `E:\JE_Horizon\pyre\pyre-release-source`, HEAD `174c8ae4af10a4163cc039ee3073056e5fcb5cf1`. Current files were read directly; HEAD is provenance, not a claim that the worktree is clean. Source originals and installed PyRe were not modified.

## Audited precursor: what PyRe already provides

Paths below are relative to `E:\JE_Horizon\pyre\pyre-release-source\src\pyre`; line numbers describe this inspection and can drift.

| Responsibility | Current source evidence | Reuse boundary |
|---|---|---|
| CUDA inventory | `hardware.py:158-229` | Identity/free/total telemetry; discovery differs from execution |
| CUDA/ROCm/XPU execution probes | `capability_probe.py:137-190`, `capabilities.py:162-207,362-385` | Bounded interpreter probes and physical-identity matching |
| Controller vendor launch | `controller_adapter.py:83-157,241-305` | Real CUDA/XPU/ROCm branches; one physical device per controller job at `117-140` |
| Scheduling/admission | `controller.py:420-465`, `controller_resources.py:135-155` | Fresh samples, leases and GPU_DEVICE_BUSY; distinct device lanes can run separate jobs |
| Memory budgets/ceilings | `allocation.py:258-280,345-378`, `target_bootstrap.py:49-112` | Measured free bytes/reserve and cooperative framework ceilings; unsupported enforcement refuses |
| Explicit multiple devices | `allocation.py:171-182`, `target_bootstrap.py:52-93` | Exposes/budgets devices for a target implementing its own distribution |
| Mixed backends in one target | `hardware.py:396-409` | Explicit `MIXED_ACCELERATOR_BACKENDS_UNSUPPORTED`; no mixed-vendor shard executor |
| Physical job contract | `controller_protocol.py:110-155`, `controller_resources.py:42-49` | Single backend/device key/reservation; distributed execution needs a new contract |
| Vendor telemetry | `vendor_telemetry.py:16-19,43-90`, `controller_resources.py:242-254` | ROCm/XPU telemetry and configured interpreter adapters |
| Process ownership | `windows_job.py:172-270,345,366,388` | Windows Job Object process-tree containment, drain/termination evidence |
| Durable controller state | `controller_ledger.py:179-180,217,252,470`, `controller.py:55-77` | WAL/FULL commits/hash chain; unknown process trees retain leases |
| Checkpoint/journal/resume | `checkpoint.py:5,81`, `durable_jsonl.py:144,253,289`, `resume.py:306,334` | Identity-bound committed progress; no automatic distributed tensor/KV replay |
| Warm device state | `gpu_context.py:77-128` | Selected CUDA/ROCm/MPS/CuPy context; XPU warm state not implemented here |

Bounded search covered release `src/pyre`, tests and README. No peer/P2P, VRAM pooling or mixed-backend distribution implementation was found within that scope. Source branches establish implementation intent; PyRe hardware execution and its broad suite were not run. Independent harness smoke tests do not certify installed PyRe.

The parallel repair tree `E:\JE_Horizon\impl\PYRE_RELEASE_REPAIR_20260924` exists, but `controller_resources.py` and `target_bootstrap.py` differ from the release tree. Do not mix them. `E:\python-gpu-maximize` is missing; the fresh manifest points to an archived repo shell rather than an active checkout. The older `E:\python_gpu` runner/governor assumes machine-specific CUDA paths/NVIDIA telemetry. Its portable core has CUDA/ROCm/MPS but no XPU. Prefer a coherent current PyRe snapshot.

## Local audit needed

The direct audit above met this session's bounded source scope. `scripts/audit_local_projects.ps1` was inspected rather than run: defaults scan wide roots and write a report. For further discovery, supply narrow roots/output under the harness and read local AGENTS first. Recheck selected files/commits before integration.

Read local AGENTS.md instructions before editing. Map source paths/symbols to responsibilities. Identify whether python_gpu is a still-active dependency, an ancestor or a separate project. Preserve existing behavior and review the local git diff before any integration. The historical overview's flags must not be assumed to remain current.

## Proposed architecture

PyRe owns user-visible scripts, run queue, resource plan approval/selection, durable progress and results. J-Link is an optional service/library behind it: device registry, capability probing, capacity proposals, leases, worker topology and sharded-model execution. Backend workers own runtime allocations and compute.

Start with subprocess/JSON integration and a documented versioned contract. Avoid importing CUDA/HIP/SYCL into the UI process. Keep native environments separate; expose error codes and artifact paths. The first prototype can run entirely as a sidecar under E:\the_harness with no Store application changes.

## Proposed request and response

Request: request_id; mode (task_pool/layer_shard); exact executable/commit; model/workload fingerprint; participating physical device IDs; backend aliases; context/batch/sequence count; precision; per-device peak-memory plan; transfer requirements; timeout; checkpoint policy.

Response: plan_id; selected devices; block ownership; predicted capacity (not speed); source of memory sample; measurement timestamps; leases acquired or refusal reason; launch manifest; run/result IDs. A plan alone is not an allocation guarantee.

Runtime records: leased-but-unallocated bytes, resident bytes, high-water mark, worker heartbeat, topology sample, committed task count, exit status and output parity artifact. GUI capacity labels must distinguish dedicated VRAM, usable allocation budget, host RAM offload and hypothetical capacity.

## Integration sequence

1. Read-only audit and baseline current tests.
2. Add pure planning and JSON serialization behind an optional flag.
3. Add stable discovery/alias mapping and memory snapshots.
4. Implement atomic per-device admission and bounded host buffers.
5. Add one backend/one worker and parity tests.
6. Qualify all-NVIDIA, all-AMD and all-Intel separately.
7. Add mixed Vulkan/RPC experiments with explicit experimental labeling.
8. Add resumable orchestration only at well-defined commit/replay boundaries.
9. Expose measured results in PyRe; keep CPU fallback until crossover proves benefit.

The July goal of being never slower requires an admission/routing policy, not a universal promise about arbitrary scripts. Benchmark end-to-end workload shapes, including process startup, model load, copies and result collection. Do not convert general Python code to GPU code silently.

## Future source review output

Amend this source map with fresh commits/byte hashes, physical acceptance and minimal interface changes before editing PyRe. Reuse identity normalization, byte budgets, admission, ledger/reconciliation, process ownership and checkpoint/journal primitives behind adapters. A distributed J-Link executor still needs partitioning, transport, lifecycle, parity and physical-device acceptance; this audit does not implement it.
