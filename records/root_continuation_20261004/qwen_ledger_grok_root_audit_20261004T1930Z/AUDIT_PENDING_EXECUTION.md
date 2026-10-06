# Grok ledger audit — static review complete, pure execution pending

Exact verdict: STATIC_REVIEW_COMPLETE_PURE_EXECUTION_PENDING. NOT ACCEPTED OR PROMOTED. No candidate import, provider-test import, or test execution occurred. Previous Qwen RED17 results remain separate immutable evidence and are not a Grok GREEN result.

Source SHA256 d73ebcd2570d955fd81732e706803e701159a040d4bd3326f2377af6a9bbae6a. Provider tests SHA256 c30fa288671e21f9c19644a51051bac909c22b15fccf1111c8c5f16f40418173. Complete source and tests were read; both AST-parse successfully. Source top level contains only hashlib/json/math imports, literals, builtin tuple(range16), and class/function definitions. No top-level native, process, network, GPU or filesystem calls are present. Tests import an unpinned module name state_ledger: executing them safely requires ROOT-controlled aliasing to this exact source and import traps. AST safety alone is not semantic acceptance.

## Fixes visible in the actual replacement

The numeric threshold now uses abs(cpu_value), line424. Strict integer checks cover count, context/batch/padding and model sizes. Huge numeric conversions and malformed model keys are refused through bounded diagnostic results. Constructor records pass the same acceptance path; actual per-experiment prior state is searched at565–574 and terminal restart is refused at588–594. Inputs are recursively detached through freeze, standard returned item assignment is blocked, and model_pass/transport_corruption_proof/superseded flags are forced false. These are source observations, not executed GREEN tests.

The anonymous DLL list API was replaced by an exact named five-DLL map. Registry names/hashes/bytes in source match the actual attempt5 fresh_dll_manifest and current five on-disk files, which were independently hashed read-only. Receipt current_dll_registry_read_only_verification.json records this limited file check. It does not prove the OS loaded those files or a GPU workload used them.

## Remaining testable mutation hypothesis

FrozenDict line101 stores its backing data in a mutable dictionary exposed as _items on the objects returned by records(). FrozenList line73 places its tuple in an assignable _items slot. Normal dict/list item assignment is now refused, but direct backing-storage edits may still rewrite prior states or nested pins. This is a source-backed hypothesis until controlled execution. The source-only additional tests exercise those specific operations on the actual returned wrappers and require the ledger's historical snapshot to remain unchanged. No speculative native exploit is claimed. ROOT may adjudicate whether access to these internal wrapper attributes falls within the requested immutability boundary; the distinction is explicit rather than silently weakening the test.

## Provider test contradiction requiring adjudication

Provider test391–407 reaches actual state RUNNING, then at397–398 expects appending FAILED_NUMERIC with omitted prior_state to raise ValueError. The actual transition table permits RUNNING→FAILED_NUMERIC; _accept only compares prior_state when that field is present and otherwise uses real history. Other supplied tests permit omitted prior_state for valid transitions. Source inspection therefore predicts this provider assertion contradicts the implemented legal transition. No provider test was run. The additional independent legal-transition control expects the valid transition to succeed. A terminal restart, with omitted or dishonest prior_state, must still be refused.

## Provenance and control scope still limited

Runtime validation still accepts any syntactically valid exe SHA256, any nonempty build ID, arbitrary nonempty device names (including duplicate aliases), and nonempty CPU/GPU origin strings without an externally trusted intended-workload comparison. DLL registry matching is materially stronger, but the API cannot authenticate physical execution, loaded modules, CPU reference origin, residency, VRAM capacity or P2P from declared metadata.

Perturbed-negative comparisons remain explicitly comparison-only, model_pass=false and transport_corruption_proof=false. There is no paired clean-baseline identity/input/source/device binding in this API. That omission means it cannot certify a real negative transport control or clean-baseline-before-control qualification; it does not by itself make a comparison-only diagnostic a false transport PASS. Identical arrays labeled perturbed_negative would simply produce a diagnostic with zero failing logits, not proof a corruption discriminator passed.

candidate_plan limits included record count but still has no JSON byte budget or per-record size/depth limit. No exact byte-budget assertion was invented because ROOT has not yet fixed that contract. durable_commit_representation honestly reports writes_performed=false and does not prove filesystem durability. State-only append records are declarations unless a trusted caller separately binds them to evaluate_experiment and actual receipts; they must not be reported as hardware or model qualification.

## Independent controls prepared, not executed

The same17 independent controls are in test_independent_same17_adapted.py. Only source path/pin and the documented dll_hashes named-map fixture interface changed. The float-context and duplicate-DLL controls now first establish that the unmodified new runtime fixture is valid, preventing a wrong-schema failure from masking the tested defect. Duplicate hashes are applied to the valid named map rather than an obsolete anonymous list. All expected rejection/immutability/tolerance assertions remain unchanged. test_adapter.diff documents every change. The original Qwen RED test/receipts are preserved.

Additional three source-only controls are in test_additional_storage_and_legal_transition.py: two backing-storage mutation hypotheses and the valid RUNNING→FAILED_NUMERIC transition. These remain pending explicit ROOT execution admission. No actual Grok pass/fail count exists yet.

Historical three-failure receipts remain immutable. ROOT's current attempt5 normal/reverse clean0/151936 status is separate actual GPU evidence; this static audit did not rerun those workloads and cannot promote the ledger or derive four-card/P2P qualification from them.
