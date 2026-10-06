# Final executor revision — nonfinite diagnostic receipt fix — 2026-10-04

This revision adds only the root-approved diagnostic aggregation fix to the reviewed post-Grok source. Earlier evidence remains preserved at parent level and under `post_grok_revision`; this file and its logs bind final hardware evidence to the new final source hash.

## Root cause and TDD evidence

The code stores `None` in `stage_max_errors` whenever a stage comparison contains non-finite output, then previously evaluated `max(stage_max_errors)` while constructing the final JSON. With `[0.0, None]`, Python raises `TypeError: '>' not supported between instances of 'NoneType' and 'float'`. The child then emitted a generic failure receipt, losing the per-stage diagnostic detail.

Exact reproduction: `records/opencl_executor_20261004/post_grok_revision/diagnostic_red_repro.py`, PID 87812, exit 0 with the caught TypeError captured in `diagnostic_red_repro.stdout.log`.

The new GPU-free test file `j_link/tests/test_executor_diagnostics.py` first ran RED as PID 39076, exit 1, because `_max_stage_abs_error` was absent. It covers finite values, mixed finite/unknown values, all-unknown values, and an empty list. The narrow helper now returns `None` whenever a stage error is unknown or non-finite, otherwise returns the maximum; it preserves zero for an empty list.

## Final source and tests

- Final source: `j_link/opencl_executor.py`
- Final SHA-256: `FF13C3783BDA61CF153B1BB58AFB9472BBE9C2404FA056C2816D011E749EA387`
- Diagnostic tests: `j_link/tests/test_executor_diagnostics.py`
- Test SHA-256: `A3E47C0AC2CAA914BFD8EEF1E39411464BB88B281F5218F6DC457ADAC6F33186`
- The earlier Grok provider artifact and immutable pre-Grok logs were not changed.

Full GPU-free suite PID 84056, exit 0: 47 tests passed in 0.156s. It includes planner, supervisor, Grok admission/vendor-boundary/label, and new diagnostic aggregation tests. Captured in `gpu_free_suite.stdout.log` and `gpu_free_suite.stderr.log`.

## Final bounded hardware gates

Each parent process used the 60-second child supervisor; the outer harness waited at most 65 seconds and would have terminated its owned process tree on timeout. All completed without timeout.

| Command | Parent / child PID | Exit | Result |
|---|---:|---:|---|
| `python -B j_link/opencl_executor.py` | 20732 / 35804 | 0 | `PASS`, mixed NVIDIA + AMD, 8/8 kernels and CPU stages, final parity true |
| `python -B j_link/opencl_executor.py --reverse` | 51692 / 21580 | 0 | `PASS`, reversed vendor order, 8/8 kernels and CPU stages, final parity true |
| `python -B j_link/opencl_executor.py --inject-corruption` | 17324 / 81156 | 1 | Measured mismatch at the first vendor boundary after `layer_03`; all 8 kernels completed, final parity false, corruption control `PASS` |

All three final GPU commands ran at exactly the final source SHA above. Clean runs each report eight unique weight hashes, eight uploads, two activation uploads, eight readbacks totaling 131,072 bytes, and one 16,384-byte cross-context host-staged boundary. Final max stage error was `8.344650268554688e-06` on clean runs and `1.001207709312439` for the corrupted run. The corruption JSON contains `applied_at_first_vendor_boundary=true` and no old context-boundary key.

Raw process outputs are `default.stdout.log`/`.stderr.log`, `reverse.stdout.log`/`.stderr.log`, and `corruption.stdout.log`/`.stderr.log`; `runtime_summary.json` records exact commands, IDs, exit codes, and source hash. These demonstrate one bounded host-staged workload, not direct P2P, physical VRAM residency, or production capacity.
