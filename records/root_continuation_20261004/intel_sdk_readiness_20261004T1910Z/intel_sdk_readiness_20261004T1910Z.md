# Intel SDK readiness audit — 2026-10-04

Scope: read-only inspection of `records/toolchains/intel_sycl`, `records/vendor_headers`, and `records/vendor_cli_qualification_20261004`, plus explicit `ze_loader.dll` checks at listed Windows/oneAPI paths. No GPU or executable was run in this audit. No files outside this report directory were changed.

## Finding

The staged Intel LLVM/DPC++ nightly has a usable compiler, SYCL headers, and `sycl-ls`. Prior qualification evidence shows a SYCL program compiled successfully under the Visual Studio environment. The staged package and vendor-header tree do not contain `ze_api.h`, `ze_loader.lib`, or `ze_loader.dll`. The three explicit runtime locations checked (`C:\Windows\System32`, and the listed Intel oneAPI paths) had no `ze_loader.dll`; other machine locations are not checked. The bounded staging tree therefore supports a SYCL compile, but does not currently evidence a direct Level Zero C API SDK or a working Level Zero runtime.

The host inventory records an NVIDIA GeForce RTX 5070 Ti and AMD Radeon integrated graphics, and no Intel GPU in the current display-device inventory. The saved SYCL probe reported zero platforms/devices and `ZE_RESULT_ERROR_UNINITIALIZED`. This is evidence for those recorded probes, not a claim about hardware beyond the inventory scope.

## Paths and hashes

- DPC++ compiler: `E:\the_harness\records\toolchains\intel_sycl\nightly_20261004\bin\clang++.exe`, SHA-256 `882e0708da94ee433861aa3f12d24571580cceafe1797d793064fe0ddad37740` (version output: DPC++ 7.2.0 pre-release, target `x86_64-pc-windows-msvc`).
- SYCL device query: `E:\the_harness\records\toolchains\intel_sycl\nightly_20261004\bin\sycl-ls.exe`, SHA-256 `995f69127c49da9b0089c5434983e2cd4a7967a2dba95b534e7191d72ab7d262`.
- SYCL header: `E:\the_harness\records\toolchains\intel_sycl\nightly_20261004\include\sycl\sycl.hpp`, SHA-256 `194b35f256b9c7486f8712b8a4eae54442d9097f3815f05246cf7f41526fac3d`.
- Compiled probe artifact: `E:\the_harness\records\vendor_cli_qualification_20261004\intel_vector.exe`, SHA-256 `411be45a8b2b9fd5469ee1398358e788d8b9e5f86ddc01cb44ada7185123389`.
- Archive digest recorded in `records/toolchains/intel_sycl/extraction.json`: `ec02b21bfffc142765633b4d9ab5ced9a2b4e088d9250ceb8cff05c34d71ef49`.
- `ze_api.h`, `ze_loader.lib`, and `ze_loader.dll`: no matches in the bounded extracted nightly package or `records/vendor_headers`; runtime DLL also not found at `C:\Windows\System32\ze_loader.dll`, `C:\Program Files\Intel\oneAPI\bin\ze_loader.dll`, `C:\Program Files\Intel\oneAPI\redist\intel64_win\compiler\ze_loader.dll`, or the two checked `oneAPI\level-zero\latest\bin` locations. No global absence is claimed.

## Prior evidence and minimal prerequisites

`intel_compile.json` records an initial link failure (`LNK1104`, missing `msvcrt.lib`). The later `compile_vs_results.json` records `intel_compile_vs` exit code 0 using the same DPC++ compiler after calling Visual Studio 18 Community `vcvars64.bat`; `native_execution_summary.json` labels Intel compile PASS and records the output binary hash above. `intel_native_runs.json` records both normal and corruption invocations as `NOT_CHECKED`: the probe found no allowed NVIDIA/AMD OpenCL GPU and forbids CPU fallback. The source filter excludes Intel devices, so it does not qualify Intel hardware execution.

`intel_opencl_probe_revision2.json` records `sycl-ls --verbose` with `ONEAPI_DEVICE_SELECTOR=opencl:gpu`: `Platforms: 0`, selectors report no device, OpenCL is loaded from the system directory, and Level Zero initialization returns `ZE_RESULT_ERROR_UNINITIALIZED`. It also records no actual Unified Runtime OpenCL adapter DLL in the archive; the system `OpenCL.dll` is not a substitute for that adapter. A host OpenCL platform result alone would not establish an Intel GPU or Level Zero device.

For a future source-specific compile/query, the proven compile path is the staged `clang++.exe` plus the Visual Studio environment. A direct Level Zero C API source additionally needs a matching `ze_api.h` and linkable `ze_loader.lib` (or source-defined dynamic loading); runtime device enumeration needs a loadable `ze_loader.dll` and a compatible Intel driver/device. The actual Qwen fixture will determine which API pieces are required. No purchase, driver, BIOS, or integration action is part of this readiness result.

Bound note: the root agent reported exact filename searches in fresh C/E drive manifests with no `ze_api.h` or `ze_loader.lib` hits, while noting those snapshots may predate current harness staging. This audit independently checked only the explicit trees and paths above.
