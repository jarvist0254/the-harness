# Actual source static gate

The complete delivered source and provider tests were read. Candidate source SHA256: 446d78eaebd631eac79bca9f32c71671a485642371e1e9899306c7199543c5a5. Top level imports hashlib, math and json, assigns literal constants, and defines functions / an exception class. There are no import-time calls, decorators, filesystem, network, process or native imports. AST parsing succeeded. This permits considering confined pure QA; it is not execution admission or correctness acceptance.

The new source hashes complete CPU-reference bytes before parsing, supports digest plus separate bytes, validates a finite flat bounded JSON array, compares supplied CPU values and count exactly, and checks alias-resolved single/three owners against four owners. The original metric rounding constant remains 1e-12. These are actual source observations, not measured fixes.

Independent test preparation preserves the original47 substantive assertions and adds26 approved schema / subset discriminators. Candidate and provider tests have not been imported or executed. Provider tests are not acceptance tests. Source mutation and physical device / allocation / capacity / P2P qualification are outside this pure gate.

Function line anchors: {"_cpu_raw": 89, "_cpu_numbers": 109, "_bind_cpu": 153, "_index_owners": 168, "_map_subset": 184, "_bind_owners": 195, "validate_capacity": 203}

Files: test_independent_capacity.py, test_adaptation.diff, run_bounded_pure.py and PREPARATION_RECEIPT.json. Execution remains NOT_RUN_PENDING_ROOT_ADMISSION.
