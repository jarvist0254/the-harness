# Independent supervisor cleanup mock gate

Scope: MOCK ONLY. Neither source is admitted for native or production use.

Final baseline 603916: 36 tests, 23 failures, zero errors. Actual Qwen 6BB4E7ED: 36 tests, 18 failures, zero errors. Both runs recorded zero forbidden native/process calls. Both owned evaluator processes exited within sixty seconds and are absent.

The successful baseline closes all nineteen fake handles exactly once. Candidate source hashes are checked before import and after execution. Test and mock adaptations are independently authored, not provider execution claims.

Remaining Qwen defects:
- Cleanup deadline starts before execution (lines 662): Twenty seconds of successful work leaves zero milliseconds for cleanup waits.
- Writer release uncertainty discarded (lines 405, 420): Ten independently injected writer/duplicate close exceptions still permit CLEANUP; initial close result is not retained.
- Reader close failure drain mismatch (lines 696): Four reader self-close exceptions return UNKNOWN status while drain remains CLEANUP because slot uncertainty is processed only in the completed branch.
- Inspection exception bypasses remaining cleanup (lines 692): A fake is_alive exception bypasses process/thread and job handle closes and receipt emission.
- Stale durable receipt on terminal journal failure (lines 645): Receipt is written before terminal journal; failure returns UNKNOWN_DURABILITY but restart loads the previous PROCESS_COMPLETED receipt.
- Reader join failure (lines 689): First join exception is swallowed; subsequent readers are not joined, and live reader handles remain unresolved. Mock failure proves incomplete ownership resolution, not permission to close a handle underneath a real reader.

Initial fake scheduling error and its original results are preserved and explicitly excluded as final evidence. See initial_evaluator_caveat.json. Final receipts and per-case calls are qwen_RED_results.json and baseline_complete_RED_results.json.

No real containment fixture may follow from this result. Root owns any subsequent native admission.
