# Nightly verification receipt - 20261005T105808Z

Target: **T7** (nightly build and continuous verification)  
Schema: 1.0  
Generated (UTC): 2026-10-05T10:58:08Z  
Duration: 781 ms

## Verdict: **FAIL** (exit 1)

Checks: 4 total - 3 PASS, 1 FAIL, 0 TIMEOUT, 0 UNAVAILABLE, 0 ERROR

| Check | Status | RC | ms | Parsed result |
|---|---|---|---|---|
| j_link_unittest_suite | PASS | 0 | 235 | tests_ran=80, verdict=OK |
| cad_unittest_suite | PASS | 0 | 139 | tests_ran=15, verdict=OK |
| j_link_planner_mixed | PASS | 0 | 78 | status=PLANNED_NOT_ALLOCATED |
| artifact_manifest_integrity | FAIL | 1 | 156 | checked=219, failure_count=9 |

## Version pins

- Platform: Windows-10-10.0.26200-SP0
- OS build: 10.0.26200
- Python: 3.10.11 (`C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe`)
- Compiler: MSC v.1929 64 bit (AMD64)
- Packages: numpy=2.2.6, pyopencl=2025.2.6, pytest=7.4.4
- GPU inventory (nvidia-smi): 1 device(s)
  - NVIDIA GeForce RTX 5070 Ti | driver 591.86 | 16303 MiB
- Tool probes: nvidia-smi=OK, rocminfo=UNAVAILABLE, clinfo=OK, nvcc=OK, ze_loader=UNAVAILABLE
  - Level Zero `ze_loader.dll` present: **False**

## Failures requiring attention

### artifact_manifest_integrity - FAIL

    C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe -B E:\the_harness\scripts\verify_adaptation.py E:\the_harness\records\ADAPTATION_SHA256_20261004_2148Z.json

- Reason: 9 pinned artifact(s) drifted
- Error: exit code 1
- stdout tail:

          "changed: docs/02_J_LINK_RESEARCH.md",
          "changed: docs/03_EXPERIMENT_RUNBOOK.md",
          "changed: docs/04_PYRE_INTEGRATION.md",
          "changed: docs/05_PRIMARY_SOURCES.md",
          "changed: docs/06_LOCAL_AGENT_HANDOFF.md",
          "changed: docs/07_5050_CANDIDATE.md",
          "changed: README.md"
        ],
        "scope": "Dated current hashes of prior curated paths plus explicitly listed numerical and pure-QA artifacts. Integrity only: no new hardware/P2P/capacity, provider-source acceptance or product promotion is certified. Original package and earlier adaptation manifests remain immutable. Does not enumerate every later record."
      }

