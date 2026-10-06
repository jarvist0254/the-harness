# Actual-source adversarial evaluation

Root admitted only isolated pure/mock evaluation. Both candidates remain refused for intended use.

17 tests ran: 14 failures, 0 errors, 3 baseline passes. Failure assertions are retained unchanged as evidence. `evaluation.json` contains the complete synthetic receipts, external test trust sets, fake native call traces and assertion tracebacks. `summary.json` ties failures to the static source review.

The only launched process was the bounded Python evaluator (PID 19624), which exited 1 and is absent. RUN_CONTAINMENT_FIXTURES was removed from its child environment. Real subprocess calls, WinDLL and uninjected supervisor native imports were explicitly blocked; zero forbidden attempts occurred. No worker, native job, GPU or provider was launched.

Exact execution command and 60-second bound are in `execution_receipt.json`. The evaluator imports immutable sources only after exact SHA256 checks. No original candidates or provider tests were modified or run.

These are discriminating synthetic schema and mock tests, not hardware measurements. Passing scalar labels or a trusted synthetic fixture cannot qualify real physical capacity.
