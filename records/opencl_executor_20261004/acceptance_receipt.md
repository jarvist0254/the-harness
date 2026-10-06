# OpenCL executor implementation and acceptance evidence — 2026-10-04

Status: runtime evidence is provisional pending Gemini review, Grok edit, and root validation. This is a one-workload experimental execution record, not production qualification.

## Source and provenance

- Candidate: `j_link/opencl_executor.py`
- Candidate SHA-256 at test time: `765B2BE5E976DFB6709F3D0E7754F71696E2B9287CC87120A767E8820F69DF94`
- Contract tests: `j_link/tests/test_opencl_executor_contract.py`
- Test SHA-256: `C4A7880F01B40DA47C3E6243354EB9D3CE39E4A6980A510E1E8407C05CA12CA3`
- Rejected provider artifact preserved and never executed: `records/factory_runs/20261004/qwen_mlp_executor_20261004T104200/generate/mlp_executor_candidate.py`
- Provider artifact SHA-256: `EA9D0529D5CCDA52C33CE725029A05CD82AE090F7E7F3172301114BE78C0EB7C`
- Implementation was written as a new executor after provider source rejection. Existing planner, OpenCL smoke probe, PyRe, drivers, and provider artifact were not edited.

## Static and GPU-free verification

Command: `python -B -m unittest j_link.tests.test_opencl_executor_contract j_link.tests.test_planner`

Process PID 94852, exit 0. Output: 28 tests passed in 0.101s. Captured in `contract.stdout.log` and `contract.stderr.log`. The suite covers pure import, byte/MiB accounting and ownership, dimensions, identity aliases, ephemeral/mixed PCI identity refusal, subdevice and CPU/GPU filtering, missing IDs, child payload revalidation, forged metadata rejection, and policy refusal before execution.

Command: `python -B j_link/opencl_executor.py --help`

Process PID 31588, exit 0. Captured in `help.stdout.log` and `help.stderr.log`. It does not enumerate devices.

The original RED baseline remains in `red_receipt.md`, `red.stdout.log`, and `red.stderr.log`. It began with seven tests before implementation. During test review, the width-32/16-layer/three-device case was corrected to a width-512 workload because the smaller workload correctly fits three 8 MiB usable device budgets. Current GREEN test count is 28 total including the pre-existing planner suite.

## Bounded hardware runs

Every parent process launches the worker with a 60-second supervisor timeout and Windows `CREATE_NO_WINDOW`; the outer harness waited at most 65 seconds and would kill its owned process tree on timeout. No run timed out. Exact command, process IDs, exit codes, stdout, and stderr are retained in each named log and `runtime_matrix_summary.json`.

| Command | Parent PID / child PID | Exit | Result |
|---|---:|---:|---|
| `python -B j_link/opencl_executor.py` | 73376 / 95036 | 0 | `PASS`; 8/8 kernels, 8/8 CPU reference stages, final parity true |
| `python -B j_link/opencl_executor.py --reverse` | 47260 / 86028 | 0 | `PASS`; AMD then NVIDIA, 8/8 kernels, final parity true |
| `python -B j_link/opencl_executor.py --inject-corruption` | 31756 / 48308 | 1 | Measured mismatch; 8/8 kernels, final parity false, control `PASS` |
| `python -B j_link/opencl_executor.py --policy-mib 1` | 88476 / 28000 | 2 | `REFUSED` before GPU execution: layer cannot fit any device budget |
| `python -B j_link/opencl_executor.py --device-ids p0:d0 p0:d0` | 52516 / n/a | 2 | `REFUSED`: duplicate explicit runtime ID |
| `python -B j_link/opencl_executor.py --device-ids p9:d9` | 96800 / 73424 | 2 | `NOT_CHECKED`: runtime ID unavailable |
| `python -B j_link/opencl_executor.py --device-ids p0:d0 --policy-mib 9` | 8312 / 38572 | 2 | `REFUSED`: one device cannot fit modeled default layers within policy |
| `python -B j_link/opencl_executor.py --device-ids p0:d0 --policy-mib 17` | 91420 / 492 | 0 | `PASS`; single NVIDIA baseline, 8/8 kernels and final parity true |
| `python -B j_link/opencl_executor.py --device-ids p0:d0 --inject-corruption` | 13844 / 42604 | 2 | `REFUSED`: no inter-device boundary exists |

The default hardware records identify NVIDIA GeForce RTX 5070 Ti (`p0:d0`, NVIDIA vendor) and AMD `gfx1036` (`p1:d0`, AMD vendor). Runtime metadata reports NVIDIA `host_unified_memory=false` and AMD `true`; the receipt preserves these returned values and labels AMD shared-host memory. This does not establish physical VRAM residency or peer-to-peer transport.

Default measured accounting: 8 unique layer weight/bias hashes; 8 weight uploads totaling 8,404,992 bytes; 4,202,496 resident weight/bias bytes per vendor; resident before first kernel; 2 host activation uploads totaling 32,768 bytes; 8 readbacks totaling 131,072 bytes; one cross-context boundary staging 16,384 bytes; 8 completed kernels and 8 CPU stage comparisons. Maximum absolute final error was 8.34465026855469e-06 at tolerance 5e-05. The corruption control changed the actual forwarded host activation at the first device boundary; all 8 kernels still completed, four later stage comparisons failed, final absolute error was 1.00120770931244, and the expected negative control was detected.

Labels in runtime JSON: `MIXED_VENDOR_RESIDUAL_MLP_EXECUTION_ONLY`, `EXPLICIT_HOST_STAGED`, and `POLICY_LIMIT_EXPERIMENT_NOT_PHYSICAL_CAPACITY_PROOF`. No P2P, production lease/durability, or four-card capacity claim is made.

The complete `runtime_matrix_summary.json` includes the default run. The earlier matrix lacking default was preserved as `runtime_matrix_summary_baseline.json`; no GPU commands were repeated to make this evidence correction. Denial rows report source-control-flow admission only and intentionally contain no fabricated zero allocation or kernel counters.

Final confirmation: `python -B -m unittest j_link.tests.test_opencl_executor_contract j_link.tests.test_planner` ran as PID 6696 and exited 0; 28 tests passed in 0.103s. See `contract_final.stdout.log` and `contract_final.stderr.log`.