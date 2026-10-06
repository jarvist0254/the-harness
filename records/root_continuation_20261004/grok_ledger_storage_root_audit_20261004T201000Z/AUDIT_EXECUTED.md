# Independent actual-file Grok ledger storage repair QA

Verdict: **PURE_QA_20_PASS_0_FAIL_0_ERROR — NOT PROMOTED**. Provider response status remains REFUSED; this separate Root-authorized audit does not overwrite that receipt or reinterpret its enum. No GPU, provider, model, native-driver or accepted-module execution occurred.

Exact delivered source SHA256 e44e86db99225b95cb9c9b63a41987d978e692eb0efc3f431741e2adf28833df; provider test source938739185fe5e6e12d115639160a228a6f917a20a18bd7368bb16231ccdf7869. Both actual files were fully read; numbered snapshots retained. Candidate top level contains only hashlib/json/math imports, constants (including the explicitly inspected pure tuple(range(16))), undecorated definitions/classes. Its imports have no native/process/filesystem/network/GPU actions. The delivered provider tests import state_ledger by name rather than the exact delivered path; they were inspected, not executed or counted as acceptance evidence.

The independent17 test derivative changes ONLY source path and SHA. test_adapter.diff documents that two-line retargeting; no assertions or fixtures changed. The additional3 file is a byte-identical copy of the earlier discriminator, SHA970be14778e48df834ef4172c0dbcdc319f8a237d7c9359da59124c6c973aed3. All candidate calls use importlib to load the exact source file after its SHA assertion; there is no duplicate embedded candidate implementation.

| Group | Actual results | Exit / cleanup |
|---|---|---|
| Same independent17 |17 passed,0 failures,0 errors |PID94380,exit0,reaped/retained handle signaled;0.578s |
| Backing storage/legal3 |3 passed,0 failures,0 errors |PID68284,exit0,reaped/retained handle signaled;0.109s |

Each owned hidden Python subprocess had a30-second deadline,2MiB cap per stream and bounded readers; no timeout, overflow or reader errors. Captured stderr1244 and357 bytes respectively; stdout0. Native dependency guards and audit traps for process/network/ctypes actions recorded zero denied events. Source, provider tests, independent tests, fence, bounded driver and Python hashes match before/after (execution_receipt.json). Reaping proves termination of these owned processes; no arbitrary PID attachment or name-based kill was used.

Concrete verified behavior:

* CPU-reference tolerance at source477 rejects CPU0/GPU0.01005 with exactly1 failing element; reversed boundary succeeds using abs(CPU), not abs(GPU).
* Floating count/context/model-byte metadata refuse; huge logit/metric integers and unhashable model keys fail closed without escaping exceptions.
* Named pinned DLL declarations reject anonymous duplicate/zero values. Zero payload comparison is DIAGNOSTIC_ONLY with model_pass/transport_corruption_proof false.
* Input nested metadata is detached; ordinary mapping item mutation, model_pass mutation, forged prior-state terminal restart and constructor READY bypass refuse.
* Former storage failures now discriminate successfully: FrozenDict uses tuple backing (source123 onward), so _items['state'] cannot rewrite history; FrozenList inherits sealed attribute assignment (source69–103), so replacing nested _items fails. These are the same controls that previously produced two actual failures against d73ebc source, not weakened assertions.
* PENDING→RUNNING→FAILED_NUMERIC works using actual stored prior history when caller prior_state is omitted (source618–657). This preserves the legal transition and prevents caller-provided prior_state bypass.

Scope and residual limits:

This establishes the specified pure numerical ledger and ordinary backing-storage regression controls only. It does not authenticate declarations of model execution, executable/build/device origin, OS-loaded DLLs, residency, allocator high-water, shared VRAM capacity, transport corruption or P2P. A perturbed_negative result remains comparison-only; no baseline/control hardware linkage is established by this pure API. candidate_plan is bounded by record count, not a newly asserted byte budget; that contract was not broadened or retested. Frozen Python wrappers are ordinary API immutability, not a hostile in-process Python security boundary against object.__setattr__ or module-global replacement. No such boundary is claimed.

Audit-driver correction preserved: prepare_attempt1.py initially required ast.literal_eval for every top-level assignment and rejected the already inspected tuple(range(16)) expression before candidate import. prepare_attempt2.py permits only that exact pure expression; source unchanged, no candidate/test execution in the failed static preparation attempt. The failure was in the independent static checker, not candidate behavior. Both preparers remain for provenance.

Execution artifacts: execution_receipt.json, actual_red_results.json (historical filename only; actual source hash identifies this20-control GREEN), same17.stderr.raw.log, additional3.stderr.raw.log, same17.fence.json, additional3.fence.json, test_adapter.diff, source.grok_untrusted.py.numbered.txt and tests_source.grok_untrusted.py.numbered.txt. Original Qwen and first Grok RED artifacts remain unchanged.
