# Independent ROOT static review: Qwen adapter

The actual Qwen artifact edf6735cd7a553dc0625f89964e97918dd741c138d8f168d3bb017e36eb7b082 remains untrusted and unexecuted. ROOT read its complete adapter and pure-test source. This note is an independent review baseline; it is not supplied as an answer key to Muse's first audit.

Blocking findings:

1. The hook checks cancellation, overflow, bad_read and deadline before GetExitCodeProcess, then returns the compiler-root status immediately after querying exit zero. A fake exit query that sets cancel, overflow, bad_read or advances the clock past dead_by produces a concrete false success against the ROOT specification. Recheck every terminal guard after the successful exit query and before returning.
2. The supplied tests execute an embedded duplicate ADAPTER_SRC, instead of importing the exact separately pinned adapter artifact. Changes to the delivered adapter would not affect that copy. The tests must load and exercise the actual candidate source without allowing native APIs/process launch at import or install.
3. The named after-wait overflow and bad_read tests set those flags before calling the hook. The named cancellation-after-wait case sets cancellation during sleep while the root is still pending. These controls do not exercise the claimed post-signal or post-exit-query transitions. Inject the changes from the fake wait and exit query to discriminate those paths.

Additional corrections:

- Clock/sleep injection is taken from ad hoc dependency keys absent from the actual supervisor import contract. Bind the supplied private supervisor's _monotonic and _sleep in install; use those same clocks for its deadlines and the hook's tests.
- Python False compares equal to integer zero. Reject malformed/noninteger wait and exit values explicitly in the mocked interface; actual _winapi returns integers. Require assigned/resumed to be the boolean True.
- The import-side-effect test only asserts that functions exist after exec. It does not deny native or process APIs. Add discriminating traps and verify that install changes only the private module's wait hook.

The design correctly preserves generic supervisor files and returns a distinct compiler-root status, allowing the original shutdown path to request owned Job cleanup. A caller must still refuse incomplete cleanup, missing final logs or changed pins. None of these static findings proves numerical GPU behavior or licenses production execution.
