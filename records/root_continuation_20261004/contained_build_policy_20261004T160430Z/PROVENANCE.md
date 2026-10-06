# Build-only supervisor policy copy

Status: `ROOT_REVIEW_READY_FIVE_NATIVE_CASES_MET`. This folder contains a scoped build-only policy variant, completed pure tests, and a separate root-admitted native CPU fixture run. No compilation, GPU job, provider call, or global queue activity occurred.

## Source lineage and exact delta

- Immutable source: `records/root_continuation_20261004/supervisor_cleanup_root_repair/contained_supervisor_revision2.py`
- Immutable source SHA-256: `3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c`
- New copy: `contained_build_supervisor.py`
- Candidate SHA-256: `fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3`
- Exact single replacement: `_int(manifest.get("deadline_seconds"), 1, 60, "deadline")` → `_int(manifest.get("deadline_seconds"), 1, 600, "deadline")`.
- The source bytes otherwise match the immutable revision-2 source exactly. Startup remains capped at 10 seconds; log limit remains capped at 131,072 bytes; containment, process creation, cleanup, status, and logging code are unchanged.

This extends the per-build deadline validation ceiling only. It does not authorize a 600-second worker fixture and does not establish production admission. Exact native fixture cases still require a later separate root admission.

## Static gate

`static_gate.py` compared the exact source bytes and parsed both files without importing either module. It verified the one-occurrence byte replacement, unchanged startup/log-cap literals, and identical full ASTs after restoring the one deadline upper-bound constant from 600 to 60. Result: `BYTE_GUARD=PASS`, `AST_GUARD=PASS`, exit code 0.

Static checker SHA-256: `5bdf13b494bc36e70a3f4538a7cac4e07df2b1b4ac3c54de6daf593619e539df`.

## Pure test results

- `test_build_policy_boundaries.py` SHA-256: `c9bbbb16a2f4c4eca94a3bf9abfa530d8222874fd185dcd7fc9a2674658fc11c`
- Tests cover baseline deadline behavior, candidate integer bounds (`1`, `60`, `61`, `600`; refusal of `0`, `601`, bool, float), unchanged 131,072-byte log ceiling and 133,000-byte rejection, and an import guard denying `_winapi`, `ctypes`, `msvcrt`, and `subprocess` during candidate import and validation.
- Boundary run: `pure_runs/boundary/run_receipt.json`, PID 94204, exit 0 in 0.131141 seconds, 5/5 tests passed, both streams below 1 MiB, all input hashes unchanged, PID absent after wait. `stderr.raw.log` records the five named test cases and `Ran 5 tests`.
- Existing mock evaluator copy: `evaluate_revision2_build_candidate.py` SHA-256 `53d2c3468eecbd6cca0c71b263b9293788123ed8183cc18101ff09d2f800e6e5`. It is the exact prior `evaluate_revision2.py` copy with only `S` path and expected source SHA changed. Run receipt: `pure_runs/legacy44/run_receipt.json`, PID 30612, exit 0 in 0.662424 seconds, 44/44 tests passed, both streams below 1 MiB, all input hashes unchanged, PID absent after wait. The evaluator result records `actual_native_process_calls: []` and `MOCK_ONLY_NOT_NATIVE_QUALIFICATION`.

Both runs used the pinned Python 3.10.11 executable at `C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe`, SHA-256 `3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260`. They are pure validation/mock results, not native qualification.

## Native fixture preparation and admitted CPU run

`native_fixture_prepared/` contains fresh copies of the original revision-2 driver, controller, worker, contract, and prepared admission files. The driver has only its pinned candidate source hash changed; the controller has only the candidate source path and hash changed; the worker is byte-identical. The historical prepared contract/admission remain unchanged and state `PREPARED_FOR_ROOT_REVIEW_NO_NATIVE_AUTHORIZATION` / `native_cases_started: false`. Root separately admitted the exact five-case CPU fixture in `ROOT_NATIVE_FIXTURE_ADMISSION.json` (SHA-256 `cb3dfaa9c23e65638504987ac1e23a2aa845af6854835696ea82143b33d4dd4e`). The candidate's 600-second validation ceiling remains recorded, while every fixture worker stays capped at 5 seconds; no extended-deadline case was included.

The admitted driver ran once at `native_fixture_prepared/native_runs/native_20261004T162557Z/`. Its retained hidden Python 3.10 child (PID 38032) exited 0 after 2.639625 seconds; stdout was 230 bytes, stderr 0 bytes, the PID was absent after wait, and all pinned inputs matched before/after. The independent raw-receipt recomputation is `native_fixture_prepared/qualification_review_ready.json` with Markdown companion. All five case conditions passed. Natural workers all exited 0 with exact stream markers; nonzero exited 3; timeout and cancel returned expected bounded states with CLEANUP; overflow reported LOG_LIMIT at a 1,024-byte stdout capture. Overflow worker exit was 1 after the bounded pipe closed (BrokenPipeError is in its stderr). Every case reported job active count 0, restart receipts matched, controller and worker PIDs were rechecked absent, and `whole_tree_certificate` remains false.

The driver `accepted` field is not treated as proof: timeout and cancel values were arrays, so the independent receipt records their type but recomputes expected statuses and cleanup conditions directly from raw case receipts. No build, GPU, provider, or global queue was authorized or run.

An initial native-preparation checker incorrectly applied PowerShell `-replace` to a byte array and reported a false driver comparison. That receipt is preserved as `native_fixture_prepared/prepare_receipt_static_attempt_001.json`; a unified diff confirmed the driver source hash as the only intended code-line change, and the corrected exact-text comparison passed. This was a checker-expression error, not a source modification.

The first attempt to invoke the AST comparison inline failed at PowerShell/Python quote parsing before the checker ran. The checked-in static checker then passed. No native or supervisor API was invoked by that attempt or by the pure test runs.
