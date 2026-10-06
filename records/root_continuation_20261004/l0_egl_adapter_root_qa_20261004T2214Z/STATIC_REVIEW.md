# Pure L0-to-EGL adapter review

Status: static review only. The provider module and its tests have not been imported or executed. No EGL, Level Zero, GPU, driver, or provider call was made.

## Pinned artifacts

- Candidate: `records/factory_runs/20261004/l0_egl_sync_bridge_two_prep_20261004T212837Z/qwen_l0_egl_fence_adapter/source.qwen_untrusted.py`, SHA-256 `99375e8072f22a7103517e0772f327b232dd3134f1f6820039a42a55f37c017c`.
- Provider test source: `records/factory_runs/20261004/l0_egl_sync_bridge_two_prep_20261004T212837Z/qwen_l0_egl_fence_adapter/tests_source.qwen_untrusted.txt`, SHA-256 `0e4372f0c706c2e7f9b5ba8354b4e46b7c70649b2f585e8824ab1c8598014491`.

The adapter's ordinary route orders producer import, semaphore import, bounded completion callback, host sync-object signal, sync-file export, EGL import, consumer completion callback, and cleanup. A host relay after a callback has actually established bounded producer completion is a valid serialized control-plane route; it does not imply CPU payload staging. A pre-signaled/stale fence is not equivalent. Cache visibility remains a separate requirement. The source advertises `DECLARED_PROTOCOL_READY` and keeps `direct_transport_qualified` false, which is the appropriate limit for a pure callback state machine.

## Discriminating risks

1. `Prerequisites` fields and callback outcomes are trusted by truthiness. A string such as `"false"` can satisfy a prerequisite or completion gate.
2. Deadline inputs are not checked for finite numeric values. `NaN` and positive infinity can bypass expiration checks and be passed to callbacks as if bounded.
3. The sync-file export path constructs a placeholder `FdToken(fd=-1)` instead of requiring a usable exported descriptor. EGL import's `observed_fd_consumed` result is not checked.
4. Callback exceptions escape instead of producing a structured fail-closed result; ordinary callback failures do not consistently trigger cleanup. Cleanup callback exceptions also escape.
5. State is retained across repeated `run()` calls, so prior completion proof can contaminate a later failed/timed-out attempt. Public `observe_completion()` also permits setting producer-complete state without a producer-wait result.
6. `report()` shallow-copies the events list but exposes mutable event dictionaries and the missing-prerequisites list, allowing callers to rewrite the apparent history.
7. Binding and prerequisite tokens are declarative strings, not authenticated provenance. Even successful pure callbacks cannot establish actual device identity, cache visibility, or hardware transport.

## Independent controls prepared

`test_adapter_independent_contract.py` adds adversarial cases for successful serialized relay ordering, descriptor validity/consumption, finite deadlines, strict booleans, callback failure and cleanup, stale state across runs, direct completion-proof injection, and report immutability. These cases are independently authored and are not the provider's test source. They have not been executed pending a root admission.

The bounded runner is `pure_qa_controller.py`. It pins the candidate, provider test artifact (for provenance only), independent tests, and Python 3.10 executable; it requires a separately supplied root admission SHA, runs only the independent test file in an isolated child with a 20-second deadline and 128-KiB per-stream cap, and records hashes and child status. The provider tests are not passed to Python. Native/GPU calls are outside its scope.

## Limits

This is a static contract review plus an unexecuted test plan. It is not evidence that callbacks are correctly implemented, that either driver's FD ownership matches the assumed contract, that cache visibility is established, or that a cross-vendor transfer works.
