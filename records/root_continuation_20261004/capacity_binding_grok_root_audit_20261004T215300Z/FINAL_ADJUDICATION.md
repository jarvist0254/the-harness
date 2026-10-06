# Independent capacity binding QA

73 / 73 independent pure synthetic controls passed; zero failures, exceptions, input mutations or denied audit events. Actual evaluator PID87892 exited0, reaped in0.438seconds, both streams drained without overflow or errors. All candidate, test, controller and Python pins unchanged.

The three previous false passes now refuse with cpu_ref_mismatch, owner_subset:single and owner_subset:three. All original47 substantive controls were retained, alongside26 approved full-JSON-reference and subset tests. Digest-only missing bytes, reordered/count-mismatched values, nonfinite/nested/wrong-type payloads, byte/count limit+1, partialforeign and ambiguousowners refused. Legal bytes, separately bound digest+bytes, alternate subsets and physicalalias matches passed.

Source:446d78eaebd631eac79bca9f32c71671a485642371e1e9899306c7199543c5a5. Raw73 outcomes:stdout.raw.json. Process/pin receipt:execution_receipt.json. Exact adaptations:test_adaptation.diff. Previous47-control44/3 receipt remains immutable.

This validates synthetic receipt logic within the tested contract. It does not authenticate caller artifacts or prove hardware residency, capacity, transport, four installed cards or P2P. Provider tests were not run; no source promotion.
