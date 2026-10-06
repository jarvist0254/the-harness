# External-memory capability query result

The build-local LunarG Vulkan SDK tool was found at `E:\the_harness\records\build_vulkan_real\toolchain\sdk\Bin\vulkaninfoSDK.exe`, file version 1.4.363.0, SHA-256 `3DD853CA5ACB16F6BC99FD00B5BB40783ACF65B386AA9F6A3FDFA36122D52273`. The existing build cache points at this copied SDK; adjacent source provenance identifies it as a copy-only 1.4.363.0 extraction. Toolchain path/version/hash and build provenance hashes are in `build_toolchain_evidence.json`.

One default full `vulkaninfoSDK.exe` query ran hidden with a 30-second bound and 2-MiB per-stream cap. It timed out at 30.032 seconds and exited 1 after the wrapper terminated only its retained child process handle. The capture was not truncated: stdout 184,323 bytes; stderr 508 bytes. The status remains `TIMEOUT`, so this is incomplete capability evidence, not a completed enumeration. No rerun was made. Stderr reports failure to read layer manifests from the Windows registry and missing display-properties entry points from the ICDs.

The captured partial stdout had already enumerated two GPU entries and printed their extension/property sections:

| Partial output device | Vendor/device IDs | Observed extension strings | `minImportedHostPointerAlignment` |
|---|---|---|---:|
| NVIDIA GeForce RTX 5070 Ti | `10de:2c05` | `VK_EXT_external_memory_host`, `VK_KHR_external_memory_win32`, `VK_KHR_external_semaphore_win32` | `0x1000` (4096 bytes) |
| AMD Radeon(TM) Graphics | `1002:164e` | `VK_EXT_external_memory_host`, `VK_KHR_external_memory_win32`, `VK_KHR_external_semaphore_win32` | `0x1000` (4096 bytes) |

The captured output did not report external-buffer feature results for `HOST_ALLOCATION` or `HOST_MAPPED_FOREIGN`; these remain `NOT_CHECKED`. Because the full query timed out, the two printed device blocks are partial observations, not a complete inventory. Extension and alignment reporting does not demonstrate that either device can import the other's host allocation, nor that any memory is physically shared or resident in VRAM. No buffer, semaphore, `VkDevice`, cross-device import, or GPU workload was created by the harness; `vulkaninfo` itself creates a Vulkan instance to enumerate physical devices.

OpenCL external-memory/semaphore extension enumeration is `NOT_CHECKED`: the admitted query timed out, so the stop condition ended capability probing. No OpenCL context, buffer, or import was attempted. The raw query receipt, stdout, and stderr are `vulkaninfo_20261004T145207Z.receipt.json`, `.stdout.txt`, and `.stderr.txt`. The run receipt records the exact command, process ID, elapsed time, exit status, stream hashes, and unchanged executable hash.
