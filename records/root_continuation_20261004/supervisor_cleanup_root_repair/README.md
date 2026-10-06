# Root cleanup repair candidate

This source is a separately attributed root repair of the actual Qwen candidate `6bb4e7edb317044e34d426d44b0035c2ea57fb762aade601f81e3be599ca59f9`. Grok's subsequent five-minute edit request timed out without an artifact; its raw failure and unknown usage are preserved. No edits here are attributed to that failed request.

Root retained writer-close uncertainty, moved the shared cleanup deadline to cleanup entry, continued bounded reader joins after exceptions, made reader inspection failures preserve remaining parent cleanup, propagated reader uncertainty to drain status regardless of task outcome, and treated native job BOOL zero as failure. The terminal journal now precedes the atomic receipt commit. A failed terminal write produces a best-effort refusal receipt with `UNKNOWN_DURABILITY`; it never certifies durability.

Reader-owned handles remain owned by their readers. A live or uninspectable reader does not authorize the parent to close its handle merely to satisfy a mocked close counter. This source is not installed in `j_link` or used by the global Factory.

Revision 1 passed 40 mock controls, then its native exit-3 fixture exposed an `UNKNOWN_DRAIN` defect. The transparent diagnostic traced a redundant attempt to terminate the already-exited process. [The source-bound diagnosis](revision2_diagnosis.md) explains the minimal revision-2 correction and preserved failure evidence. Revision 2 passed 44 independent mock controls and [all five admitted native CPU cases](../supervisor_native_fixture_revision2/fixture_result_report.md). [Root independently recomputed those receipt gates](../native_revision2_root_adjudication_20261004T144416Z.json), including the raw driver's list-valued timeout/cancel acceptance fields.

Production workers, arbitrary descendants/controller loss, resource high-water and GPU execution remain unqualified. Native fixture admission is separate from production installation or whole-tree certification.
