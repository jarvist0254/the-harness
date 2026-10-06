# Nightly verification receipt - 20261005T144548Z

Target: **T7** (nightly build and continuous verification)  
Schema: 1.0  
Generated (UTC): 2026-10-05T14:45:49Z  
Duration: 688 ms

## Verdict: **PASS** (exit 0)

Checks: 4 total - 4 PASS, 0 FAIL, 0 TIMEOUT, 0 UNAVAILABLE, 0 ERROR

| Check | Status | RC | ms | Parsed result |
|---|---|---|---|---|
| j_link_unittest_suite | PASS | 0 | 313 | tests_ran=115, verdict=OK |
| cad_unittest_suite | PASS | 0 | 77 | tests_ran=15, verdict=OK |
| j_link_planner_mixed | PASS | 0 | 47 | status=PLANNED_NOT_ALLOCATED |
| artifact_manifest_integrity | PASS | 0 | 125 | checked=219, failure_count=0 |

## Artifact manifest

- Selection mode: newest_by_filename_sort
- Resolved: E:\the_harness\records\ADAPTATION_SHA256_20261005_110323Z.json
- Candidates by filename sort (3): ADAPTATION_SHA256_20261004.json, ADAPTATION_SHA256_20261004_2148Z.json, ADAPTATION_SHA256_20261005_110323Z.json

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

No failures. Every check met its parsed criteria.

## Notes

- manifest resolution: mode=newest_by_filename_sort status=OK resolved=E:\the_harness\records\ADAPTATION_SHA256_20261005_110323Z.json
- manifest candidates by filename sort (3): ADAPTATION_SHA256_20261004.json, ADAPTATION_SHA256_20261004_2148Z.json, ADAPTATION_SHA256_20261005_110323Z.json

