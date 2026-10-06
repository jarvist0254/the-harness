# Independent actual-source ledger audit: REJECTED

Scope: complete static read of delivered source, delivered tests and task spec, then ROOT-authorized execution of independently authored tests against the exact immutable module. No provider tests, native APIs, GPU/model runs, providers, fixes or promotion.

Source SHA256: 6dfb6a72a1310d23cf435c73f32dcd0b6a57b85cef774c9a47c8748ce3e68dc1. Provider tests SHA256: 612325517bf27fd37d2a3aa0c96906c013f97ca48d4a8bfc1e9934ab674ca2a5. Both unchanged after the run. Source import is limited to hashlib/json/math and definitions/constants; the independent importer denied native, process, network and GPU dependency imports. No deny trap was invoked.

Measured RED: 17 tests, 12 assertion failures, 3 uncaught-error cases, 2 passes. Owned child PID91120 exited1, was reaped in0.641 seconds, with no timeout or stream overflow. stderr11395 bytes, stdout0. Limits30 seconds and2MiB per stream. Raw source/tests with line numbers, tests, results and execution receipt are preserved here.

## Concrete source defects

1. **Wrong tolerance reference changes the verdict.** Source line190 compares against0.01+0.01*abs(GPU), although the fixed workload requires abs(CPU). With one element CPU0/GPU0.01005 and the other151935 equal zero, candidate returns DIAGNOSTIC_ONLY/fail_count0; the fixed CPU threshold0.01 requires FAILED_NUMERIC/fail_count1. Reversing this pair produces a false numeric failure: CPU0.01005 gives threshold0.0101005, so error0.01005 should pass. Both payload hashes and independent one-element analytic max/RMSE were bound correctly. This is measured by two failed actual-file controls, not inferred from a historical failure count.

2. **Ledger history is mutable.** Lines247 and250–251 store and expose actual record dictionaries; line265 copies only the outer dictionary. Mutating records()[0] changed FAILED_NUMERIC to DIAGNOSTIC_ONLY. Mutating a nested input pin after append changed the ledger's stored pin. Mutating model_pass through records() made candidate_plan emit model_pass=true despite no_pass=true. The delivered immutability test only checks that the old empty ledger still has zero entries (tests167–176); it does not test object or nested mutation.

3. **Constructor bypasses all record validation.** Lines244–248 accept arbitrary records without append checks. A constructor record with stateREADY and model_pass=true was accepted. Candidate serialization can therefore contain forbidden state/qualification claims. The constructor must validate and detach records just as strictly as append, without changing old receipts.

4. **The actual per-experiment previous state is not enforced.** Lines262–264 trust the incoming prior_state and never look up the latest record for that experiment. A terminal FAILED_NUMERIC experiment was restarted as RUNNING by omitting prior_state or claiming prior_statePENDING. Both controls failed. The delivered test178–183 rejects only an explicitly supplied forbidden literal, not a dishonest prior-state assertion. New builds/model experiments need distinct IDs; this correction must not overwrite or supersede prior measured failures.

5. **Strict integer fields accept floats.** Model size equality at line73, context equality at lines84–93 and count equality at line166 accept639446688.0,128.0 and151936.0. All three controls failed. Tokens/requestedKV/actualKV already use the stricter integer helper, so fixing these fields need not change numeric comparison tolerance.

6. **DLL/build provenance is syntax-only and anonymous.** Runtime lines96–102 accept five identical all-zero hashes; the measured duplicate-zero control failed. No filename-to-hash mapping or trusted expected DLL/build/exe/device-origin binding is accepted by the API. The delivered runtime fixture itself uses five identical zero DLL hashes at test line38 and an anonymous zero exe hash at line42. This validates declared shapes, not the five freshly loaded DLLs. ROOT must define the trusted expected mapping/API before treating this as provenance qualification. A pure ledger cannot authenticate OS loads, physical devices, residency, VRAM capacity or P2P from strings/booleans.

7. **Malformed numeric/identity inputs escape instead of refusing.** Huge finite Python integer10**400 in a logit raises OverflowError at line150; the same value in claimed max error raises OverflowError at line40. An unhashable model_key[] raises TypeError at line68. All three are actual unhandled errors. Structural malformed values should produce the applicable refusal result or documented validation exception, not a crash in the numerical diagnostic path.

## Other static limitations, not additional measured RED cases

candidate_plan bounds record count at270–286, but has no byte bound or per-record size/schema limit. A single large arbitrary record can exceed any intended JSON byte budget. The spec does not state the byte budget, so an exact size gate needs ROOT adjudication before adding an acceptance test. durable_commit_representation honestly reports writes_performed=false; it is not a durable filesystem commit or atomic rename proof.

Metadata contains no actual opened-file/model/logit provenance authentication or trusted caller expected artifact mapping. Model whitelist declarations match fixed pins, but declaration equality does not establish that the native workload used those bytes. Runtime device_order accepts arbitrary nonempty names and origins can be identical. These gaps should remain explicit rather than becoming claims of verified execution.

The comparison outputs explicitly set transport_corruption_proof=false and model_pass=false, and perturbed_negative is labeled comparison-only. Those are correct scope choices. Arbitrary record fields and constructor/exposed mutation can still put generated qualification claims into a serialized plan; schema restrictions and immutable snapshots must prevent such fields from being mistaken for measured qualification.

## Delivered test credibility

The delivered tests are synthetic, were read but not run, and do not ingest current actual numerical receipts. Their three-failure test126–136 creates three1.0 differences; it does not preserve or validate an actual old model receipt. The helper7–18 calculates max/RMSE for synthetic arrays but does not test the CPU-reference tolerance boundary. Immutability/state tests omit the measured mutation and dishonest-history discriminators. Runtime metadata intentionally accepts invented build/exe/device origins and repeated zero hashes. No test binds the exact delivered source hash; importstate_ledger assumes some separately staged module name. Native/hardware evidence cannot be inferred from this suite.

## Historical versus current measured runs

The adjacent provider spec's three-failure statement is historical and superseded as a current-status description by ROOT's separately measured attempt5 normal and reverse clean0/151936. This audit did not rerun or independently re-open those GPU receipts. Old failures must remain immutable independent experiments; new clean comparisons do not justify rewriting their records, changing tolerance, or claiming model/P2P/residency/capacity qualification from this pure module.

## Discriminating controls and next gate

Independent actual-file controls are in test_independent_ledger_red.py, SHA13f38d27153456da43f4ebc8bf7ceb69ef3f3262ff19d1180193f3a7fff95d34. Keep the immutable17-case RED evidence. A corrected actual module needs the same tests rerun with only a documented source-path/hash retarget, plus ROOT-adjudicated trusted named artifact provenance and JSON byte budget. No source fix or promotion was performed here.
