# Vendor SDK state (three-vendor arm, 2026-10-05)

Purpose: prove the software path works before hardware spend. Every claim
below was executed on this host unless marked otherwise.

## 1. Intel oneAPI — INSTALLED, toolchain PROVEN

- Intel oneAPI Base Toolkit 2025.1.3.8 via winget, silent, exit 0.
- `icx` 2025.1.1 verified (`icx --version`).
- `sycl-ls`: exactly ONE device, OpenCL CPU (Ryzen 7 7700). No GPU SYCL
  device: no Intel GPU, NVIDIA not a SYCL backend here, AMD iGPU not
  exposed. Honest enumeration, not an error.
- Level Zero is NOT in the Base Toolkit (whole-tree search: no ze_api.h,
  no ze_loader). Source: oneapi-src/level-zero v1.34.0
  `level-zero-win-sdk-1.34.0.zip` (317,053 bytes, headers + import libs).
- `j_link/l0_enum.c` (dynamic-load probe, no link-time L0 dependency):
  compiled with icx (MSVC 14.41 include + SDK 10.0.26100 libs passed
  explicitly -- vcvars64.bat is a no-op in this sandbox; link needs
  kernel32 + Uuid + libcmt + oldnames + libvcruntime + libucrt).
  Run: `NOT_CHECKED / loader / ze_loader.dll absent`, exit 2.
  Receipt: `records/cuda_samples_20261005/l0_enum.txt`.
  The B60 trigger (loader appears with Intel driver) stands.

## 2. AMD HIP SDK — DOWNLOADED, install BLOCKED-silent

- Installer `AMD-Software-PRO-Edition-25.Q3-Win10-Win11-For-HIP.exe`,
  direct from `https://download.amd.com/developer/eula/rocm-hub/`,
  byte-exact 1,629,294,960 bytes (matches Content-Length). Kept at
  `%TEMP%\hipsdk.exe` (re-downloadable; NOT vendored into the repo).
- Silent `-install` (documented CI flag) exits 206 then 1 with zero
  observable effect: no `C:\Program Files\AMD\ROCm`, no hipcc, no
  registry entry, no log. `--help` prints nothing.
- 2026-10-05: installed after reboot (ROCm 6.4, `C:\Program Files\AMD\ROCm\6.4`).
  `hipcc` 6.4 (clang 20, MSVC 14.41 toolset -- VS18 14.51 headers break the
  build exactly as the toolset pin predicted; prepend 14.41 bin to PATH).
- SURPRISE, MEASURED: the Raphael iGPU **is a HIP target on Windows**:
  `hipInfo` + `j_link/hip_enum.cpp` (hipcc-built, exit 0) enumerate 1 device,
  "AMD Radeon(TM) Graphics", **gfx1036**, 38.4 GB (host-shared, NOT VRAM),
  1 CU, PCI 0000:74:00. Directed peer matrix: empty (single device -- no
  pair constructible, which is itself the honest result). 64 MiB H2D/D2H
  checksum: TRUE. Receipts: `records/hip_20261005/`.
- Standing correction: "Raphael iGPU is not a HIP target" (earlier
  expectation) was WRONG -- it enumerates and copies. What stays true:
  it is shared host memory, so it NEVER unlocks a peer tier; discrete-GPU
  cells remain NOT_CHECKED. `amd_probe.py` classification unchanged.
- Self-inflicted bug caught by execution: `hipDeviceProp_t.pciBusID` is an
  int trio in HIP, not CUDA's string -- first build AV'd on `%s`; fixed to
  `%04x:%02x:%02x`, green since. `j_link/hip_debug.cpp` is the localizer.
- USER ACTION DONE 2026-10-05: interactive elevated run + reboot + MS
  Update installed ROCm 6.4 at `C:\Program Files\AMD\ROCm\6.4`
  (NOT on PATH by default; invoke via full path).
- RE-VERIFIED 2026-10-05 ~14:45Z: `hipcc.exe --version` = HIP 6.4.50101,
  clang 20.0.0git, target x86_64-pc-windows-msvc; `hipInfo.exe` = device 0
  "AMD Radeon(TM) Graphics", gfx1036 (`amdgpu-arch.exe` agrees), pci 116:0:0,
  isIntegrated=1, totalGlobalMem 35.75 GB shared, canMapHostMemory=1;
  `amd_probe.py` verdict still `NO_COMPATIBLE_AMD_GPU_THIS_HOST` (PROVEN).
  `rocminfo` / `rocm-smi` / `amd-smi` are absent from the Windows SDK bin
  (expected -- not shipped on Windows, not a failure); `vulkaninfo` SAMPLED.
  Nightly gate same run: PASS 4/4 (115/115 j_link unit, 15/15 cad unit,
  planner, manifest 219 files 0 failures).
- gfx target table for later (audio.cpp CI, DOCUMENTED third-party):
  gfx1100=7900XTX, 1101=GRE, 1102=7600, 1103=780M iGPU, 1150/1151=Strix,
  1200/1201=9070 RDNA4. MSVC toolset pin: HIP clang needs <= 14.44
  (14.51 `<cmath>` breaks it) -- use the VS2022 14.41 toolset that
  already builds our probes.

## 3. NVIDIA developer package — SAMPLES BUILT, negative control green

- Toolkits present: CUDA v12.3 (PATH default) + v12.8 (used for builds);
  `ncu.bat` shim present; no Nsight Systems, no samples dir before today.
- `NVIDIA/cuda-samples` cloned shallow to `%TEMP%\cuda-samples`.
- Built with CUDA 12.8 nvcc (exit 0): `simpleP2P`, `deviceQuery`
  (+ `topologyQuery` sources present, unbuilt).
- `simpleP2P`: "Two or more GPUs required. Waiving test.", exit 2 --
  the honest negative control this host should produce.
- `deviceQuery`: 1 device, 5070 Ti, cc 12.0, 16303 MB, 8960 cores,
  256-bit, driver 13.1 / runtime 12.8. Cross-checks the RTX harness.
- Receipts: `records/cuda_samples_20261005/`.

## 4. Standing toolchain pins (reproducibility)

- CUDA builds: v12.8 nvcc + VS2022 BuildTools MSVC 14.41 (vcvars is a
  no-op here; nvcc self-locates MSVC). CUDA 12.3 + 14.41 fails STL1002.
- icx builds: oneAPI setvars.bat + explicit MSVC 14.41 include +
  SDK 10.0.26100 um/shared/ucrt includes + 6 named .libs (see §1).
- HIP builds: blocked on install; toolset pin 14.41 already compatible.
