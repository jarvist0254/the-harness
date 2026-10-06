# OpenCL executor contract RED baseline — 2026-10-04

Contract suite: `j_link/tests/test_opencl_executor_contract.py`. It tests the stable pure API `prepare_plan(devices, *, width=512, batch=8, layers=8, policy_mib=9)`, planner error identity, GPU-free imports, byte/MiB accounting, work-buffer bounds, unique contiguous layer ownership, two- and four-device budgets, insufficient-device refusal, duplicate identities, unused devices, and dimension/policy validation.

Command: `python -m unittest j_link.tests.test_opencl_executor_contract`
Process PID: 40896
Result: expected RED, exit 1; 7 tests ran, 1 failure and 6 errors. All implementation-facing cases fail with `ModuleNotFoundError: No module named 'opencl_executor'`; the isolated GPU-free import contract fails for the same missing module. No NumPy/OpenCL runtime was imported, and no GPU code ran.

Captured output: `red.stdout.log`, `red.stderr.log`.

Test-authoring decision: result keys are pinned as top-level `planner_result` (the unchanged pure planner output) and `layer_ownership` (ordered entries with `device_id`, `physical_id`, and `layers`). This clarifies the output-shape portion of the acceptance contract for the provider candidate.
