# Post-Grok executor revision — 2026-10-04

This revision supersedes the provisional pre-Grok runtime source for current code review. Pre-Grok source, tests, raw hardware logs, and receipt remain preserved in the parent evidence directory. Only the three authorized post-patch hardware gates were run; the single-NVIDIA baseline was not repeated.

## Provenance and changes

- Source: `j_link/opencl_executor.py`
- Pre-Grok SHA-256: `765B2BE5E976DFB6709F3D0E7754F71696E2B9287CC87120A767E8820F69DF94`
- Post-Grok SHA-256: `AB509DEFF1A1DA75DF02A7E85471A6501E9799CCD6F9F6C7CBBCE8F6EF521AAF`
- Authenticated provider patch: `records/factory_runs/20261004/gemini_grok_pipeline_20261004T110000/grok_fast_patch_extracted.json`, SHA-256 `13C78488D7A488FABD2731F8A0893E0FA1561D865D11B63D19C84A0A597DA70D`; model `grok-4.7-build-fast`.
- The four provider replacements matched exactly once each in the frozen source. The change adds strict known-positive integer max-allocation admission before contexts/buffers and chooses the corruption point at the first vendor change rather than the first device/context change. NVIDIA PCI-domain logic was not altered.
- Root-authorized reporting changes use a generic `RESIDUAL_MLP_EXECUTION_ONLY` label, add `execution_population` and sorted `selected_vendor_keys`, emit `MIXED_VENDOR_RESIDUAL_MLP_EXECUTION_ONLY` only for actual multi-vendor execution, rename the corruption result key to `applied_at_first_vendor_boundary`, and correct help/refusal wording.
- `j_link/tests/test_grok_executor_review.py` SHA-256: `B05E45059701C8FBEF39DD28668D41C46D6B73B3399A634527595A284FB503B0`.
- `j_link/tests/test_executor_supervision.py` SHA-256: `130DD222B591A89D2CDF18230E03ABE12F2E80F15503341CD800F2CEA0512B20`.
- Provider originals were not edited. The prior single-NVIDIA result log retains the pre-patch label and is historical; the GPU-free label contract now verifies the explicit `SINGLE_VENDOR` label behavior.

## Verification

Before applying Grok, the frozen source passed 34 tests (PID 20208, exit 0, 0.133s); captured in parent `pre_grok_frozen_full_suite.stdout.log` and `.stderr.log`.

The new adaptation suite first produced RED on the known defect: max-allocation values 0/None/bool were silently accepted, a string raised an unclassified `TypeError`, unknown limits could reach the mocked GPU executor, and vendor-boundary helpers were absent. Captured as `grok_adaptation_red.stdout.log` and `.stderr.log` (PID 41832, exit 1).

After the approved patch and reporting fixes, full GPU-free suite PID 5836 exited 0: 43 tests passed in 0.097s. This includes planner contracts, child-supervisor timeout/exit/JSON/atomic-write checks, vendor-boundary ordering, homogeneous-vendor corruption refusal, single-vendor labels, and unknown max-allocation admission proving `_execute_gpu` is not called. Logs: `gpu_free_suite.stdout.log`, `gpu_free_suite.stderr.log`.

`python -B j_link/opencl_executor.py --help` ran as PID 72756, exit 0; its output says “first vendor boundary.” Logs: `help.stdout.log` and `help.stderr.log`.

## Post-patch bounded hardware gates

Each CLI run was supervised by the executor's 60-second child deadline; the outer harness waited at most 65 seconds and would terminate its owned process tree on timeout. All three completed without timeout. Exact commands and parent/child PIDs are in `runtime_summary.json`; raw stdout and stderr are preserved beside it.

| Command | Parent / child PID | Exit | Result |
|---|---:|---:|---|
| `python -B j_link/opencl_executor.py` | 28652 / 92256 | 0 | NVIDIA + AMD, `MIXED_VENDOR`, 8/8 kernels and CPU stages, final parity true |
| `python -B j_link/opencl_executor.py --reverse` | 27988 / 6848 | 0 | AMD + NVIDIA, `MIXED_VENDOR`, 8/8 kernels and CPU stages, final parity true |
| `python -B j_link/opencl_executor.py --inject-corruption` | 78836 / 30740 | 1 | 8/8 kernels completed, measured parity mismatch, final parity false, corruption detected at `layer_03`, control `PASS` |

Both clean runs report 8 unique weight hashes, 8 one-time weight uploads, 2 activation uploads, 8 readbacks totaling 131,072 bytes, one 16,384-byte cross-context host staging boundary, weights resident before the first kernel, and `execution_population=MIXED_VENDOR`. Corruption reports 4 mismatching later stages and final absolute error 1.00120770931244. It sets `applied_at_first_vendor_boundary=true`; the old context-boundary key is absent.

Unknown max-allocation admission and single-vendor corruption refusal were verified through GPU-free child mocks before `_execute_gpu` is called. The previous single-NVIDIA policy17 GPU baseline passed before this revision; it is not repeated under this phase, so do not treat its old label fields as evidence for the new output schema.

These results demonstrate a bounded mixed-vendor host-staged MLP workload only. They do not establish direct P2P, physical VRAM residency, production durability/leases, or multi-card capacity.
