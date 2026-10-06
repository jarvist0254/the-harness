# Actual Grok pure execution followup — not accepted

ROOT admitted only the17 adapted independent controls and3 existing additional controls against source SHA d73ebcd2570d955fd81732e706803e701159a040d4bd3326f2377af6a9bbae6a. These controls executed; the earlier pending static report remains historical and unchanged.

Measured outcome: adapted17 passed17/17. Additional3 produced1 pass and2 assertion failures. Aggregate20 controls:18 passes,2 failures,0 errors. This is a pure numerical/state-contract result, not model, GPU, capacity, physical-residency, transport-corruption or P2P qualification.

The original numerical threshold, strict-number, constructor, ordinary immutability, nested input alias, prior-state, anonymous-DLL and huge-input17 controls now pass. They ran against the actual Grok source with the documented named-DLL fixture adaptation; the old Qwen RED was not reused as GREEN.

The two storage hypotheses are now proved within the admitted test boundary:

- Source FrozenDict line101 exposes its actual backing dict through the wrapper returned by records(). Changing records()[0]._items['state'] to DIAGNOSTIC_ONLY changed the ledger's stored FAILED_NUMERIC history.
- Source FrozenList line73 has an assignable backing slot. Reassigning the returned nested pin list's _items tuple to('forged',) changed the ledger's stored original pin.

These controls directly call internal wrapper attributes, rather than ordinary item assignment (which is correctly blocked). ROOT explicitly admitted this boundary. A fix should detach records() output or protect the backing storage; no fix was made here. Do not claim a hostile-Python memory security boundary or hardware exploit from these findings.

The legal transition control passed: an actual RUNNING experiment can transition to FAILED_NUMERIC without a caller-supplied prior_state. Actual prior lookup enforces the transition. This supports the static finding that provider test397–398's expected ValueError is a provider-test defect. Provider tests themselves were not executed.

Owned children: same17 PID39356 exit0/reaped in0.657s; additional3 PID25184 exit1/reaped in0.140s. Each had a30-second deadline and2MiB per-stream cap. No timeout or overflow; stdout0 for both, stderr1244 and1678 bytes. Both stream readers joined. Source, provider tests and both independent test hashes were identical before and after. The import deny trap list was empty. No provider test, native, network, GPU, model or provider API ran.

Remaining provenance/control/byte-budget limitations in AUDIT_PENDING_EXECUTION.md remain static scope limits, not new executed failure cases. Named DLL hashes match current on-disk attempt5 files but do not independently prove runtime loads. Arbitrary exe/device/origin declarations remain untrusted; perturbed diagnostics are not paired-baseline transport qualification. No integration or promotion was performed.

Evidence: execution_receipt.json, actual_red_results.json, same17.stdout.raw.log, same17.stderr.raw.log, additional3.stdout.raw.log, additional3.stderr.raw.log. Verdict PURE_EXECUTED_ORIGINAL17_PASS_STORAGE2_FAIL_NOT_ACCEPTED.
