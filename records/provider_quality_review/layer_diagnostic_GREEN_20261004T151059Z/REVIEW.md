# Independent Grok comparator QA

Exact candidate SHA-256: `2786a0213039cdeb1654dd1de7688e9f628672a963355fcfef6ebe94cba87495`, unchanged before/after.

Original 62 independent controls: **62 passed** with no assertion or output-adapter changes. Three additional malformed-input controls: **3 failed**, preserving failures as evidence. Total 65 tests, 3 assertion failures, zero test errors/skips and zero trapped native/network/process/GPU calls. The bounded child exited 1 in 1.047 seconds; its PID was absent afterward. All observed fixture input hashes remained unchanged.

Concrete API defects: `_validate_expected` applies `set(devices)` before element string validation, leaking TypeError for nested list/dict inputs (line143). `_canonical_name` converts unrestricted decimal suffixes before bounded length validation, leaking ValueError for 5000 digits under this interpreter (line75). These are malformed-input refusal failures, not false numerical MATCH results. No implementation repair was made.

Result mapping remains compatible with original assertions: result/comparator, first_divergent_ordinal/stats on threshold failure. New nodes list includes every capture; first_noise is separate from first_threshold_violation. Strict origins, fixed tokens/tolerances, bytes/hash/finite checks, structural refusals and static path symlink controls passed the original suite.

Only synthetic artifacts were used. Metadata matching does not authenticate hardware execution. Dynamic rename/reparse confinement is NOT_CHECKED: lstat checks precede open, with no opened-handle fstat binding. Provider tests and native/GPU captures were not executed. The 144-node limit cannot be independently reached with 142 allowed canonical IDs.

The first gate attempt failed before candidate import because an AST string rendering used different quotes. That receipt is preserved; the derivative uses a structural AST argument check. `adaptations.json` lists all independent test/gate changes. Old RED artifacts remain immutable.
