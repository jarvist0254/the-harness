# Admitted pure-QA run result

The exact root-admitted controller invocation completed without timeout or output overflow. Outer controller PID 23544 exited 1 after 0.246 s; inner test PID 53756 exited 1 after 0.094 s. Source, provider-test, controller, independent-test, Python, and admission pins matched before and after. Both child output readers reached EOF, joined, and recorded no reader errors. The provider test artifact was not included in the Python command. No native/GPU/provider calls occurred.

Raw evidence is adjacent: `outer_receipt.json`, `controller.stdout.bin`, `controller.stderr.bin`; the inner controller's raw receipt/stdout/stderr are in `../pure_qa_20261004T224944Z/`. The inner suite ran 10 test methods and reported 8 failures, 2 errors, and one passing test; the two subcases for `inf` and `nan` account for two reported failures under one method.

## Candidate findings observed

- A callback return indicating `observed_fd_consumed=False` still ended with `DECLARED_PROTOCOL_READY`.
- The default export path and a string `"false"` prerequisite/outcome also ended `DECLARED_PROTOCOL_READY`.
- `inf` and `nan` deadlines ended `DECLARED_PROTOCOL_READY`.
- Calling the public completion observer and then signaling invoked the host sync-object callback without producer callback evidence.
- A callback exception propagated uncaught out of `run()`.
- The retry-after-timeout control passed: after one successful call followed by a timed-out second producer wait, the second report showed neither producer nor consumer completion proven.

## Incomplete controls

- The host-relay order test stopped at its first assertion because the result was unexpectedly READY; its later wait-before-signal assertion did not run. Order is source-visible but this test run did not measure it.
- The invalid-export control stopped at its first result assertion, so `seen == []` (whether EGL import was blocked) was unreachable. The candidate's source constructs a placeholder descriptor, but this run does not count as the independent callback assertion.
- The textual-false prerequisite and outcome controls likewise stopped before their callback-list assertions.
- The infinite/NaN subcases stopped before confirming the callback list was empty.
- The event-report immutability case errored in test setup: its synthetic `NativeOutcome` used unsupported keyword `detail`; no report mutability assertion ran.
- The callback-exception case errored at the uncaught `RuntimeError`; its cleanup callback assertion did not run.

No corrections or reruns were made after these results. Preserve the raw failures as the admitted run outcome.
