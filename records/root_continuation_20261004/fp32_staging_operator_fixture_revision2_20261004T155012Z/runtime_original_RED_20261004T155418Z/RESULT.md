# Original-build Vulkan0 operator RED

The single admitted run produced complete six-case JSON and exited1 (`OPERATOR_PARITY_FAIL`) in1.281 seconds. PID94852 was reaped and absent. No native assertion, timeout, unsupported refusal, stream truncation or pin change occurred. All12,288 compared outputs were finite;10,240 violated the unchanged per-element gate `2e-5 + 2e-6*abs(double_reference)`.

| Case | Failed comparisons | Max absolute error | RMSE |
|---|---:|---:|---:|
| contiguous | 0 / 2048 | 4.17216371886e-05 | 1.24252472328e-05 |
| X_stride | 2048 / 2048 | 0.0103784038376 | 0.00999649203412 |
| Y_stride | 2048 / 2048 | 0.0172785746556 | 0.016646917187 |
| X_stride_Y_stride | 2048 / 2048 | 0.0276345650356 | 0.0266384119262 |
| Y_transpose | 2048 / 2048 | 0.0172785746556 | 0.016646917187 |
| X_stride_Y_transpose | 2048 / 2048 | 0.0276345650356 | 0.0266384119262 |

The contiguous case passed; every noncontiguous output failed in all five other layouts. Graph API success, shape and selected-device buffer ownership checks completed in every case. The fixed deterministic values/reference and child flags were unchanged. This is a discriminating original-build numerical RED, not a passing operator workload.

Read-only enumeration through the retained owned process handle observed all five exact local ggml DLL paths and matching hashes. Source/executable/copied and original DLL hashes remained unchanged, as did parent flags. Raw logs, module observations, copy pins and run receipt are preserved.

No AMD, corruption or retry run followed. This does not prove the staging path causes residual whole-model mismatches, independently trace shader instructions, or qualify models, P2P, four-card capacity, shared VRAM, performance or production use.
