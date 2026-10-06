# Expanded actual-source RED baseline

Ran exactly once against old immutable Grok sources: 55 cases, 32 failures, 0 errors, 23 passes. The bounded evaluator process exited 1 in 1.25 seconds and is absent. Exact command/PID/hash/bound are in execution_receipt.json.

expanded_evaluator.py imports the exact SHA-pinned actual candidate modules and uses fully fake process/job/pipe/reader dependencies. Native _winapi exports, ctypes DLL entry points, subprocess factories and os launch routes are deny-trapped. RUN_CONTAINMENT_FIXTURES is unset. Zero forbidden attempts, real workers, Job mutations or GPU calls occurred.

RED_results.json retains per-case synthetic inputs/trust sets, actual algorithm results, exceptions, allocation/owner/close count/outcome ledgers and call traces. RED_summary.json records coverage limits. Keep failure assertions unchanged as evidence; both candidate sources remain unmodified.

Normal anonymous-pipe EOF represented by OSError.winerror=109 passed. Unexpected winerror=5 was silently treated as completion by the old candidate and failed its discriminator. These tests establish mock behavior only, not actual Windows containment or hardware qualification.

No provider self-admission constant grants authority. Root’s external authorization and exact source hashes govern this run. New source pairs require fresh static review and a separate hash-bound evaluator derivative. No native fixtures are admitted here.
