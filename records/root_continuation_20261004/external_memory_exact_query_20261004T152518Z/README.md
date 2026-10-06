# Exact external-host-memory capability query

This is a compile-only preparation for a root-admitted read-only Vulkan capability query. The executable has not been run. Runtime execution remains subject to separate root review/admission.

The program creates a Vulkan 1.1 instance, enumerates physical devices and their device extensions, reads `VkPhysicalDeviceProperties2` chained to `VkPhysicalDeviceIDProperties`, and when advertised reads `VkPhysicalDeviceExternalMemoryHostPropertiesEXT.minImportedHostPointerAlignment`. On each enumerated device advertising `VK_EXT_external_memory_host`, it calls `vkGetPhysicalDeviceExternalBufferProperties` for both `VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT` and `VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_MAPPED_FOREIGN_MEMORY_BIT_EXT`, separately for:

- buffer usage `TRANSFER_SRC | TRANSFER_DST`
- buffer usage `STORAGE_BUFFER | TRANSFER_SRC | TRANSFER_DST`

Each result reports external-memory feature bits, importable/exportable booleans, the dedicated-only bit, and compatible/export-from-imported handle masks. Device output includes vendor/device IDs, API version, device/driver UUID, device type, and the exact host extension/alignment information. Intel is counted only among physical devices enumerated by this Vulkan instance; zero is labeled `NOT_ENUMERATED_BY_THIS_VULKAN_INSTANCE`, not a statement about the system outside Vulkan enumeration.

The executable intentionally does not create a `VkDevice`, buffer, allocation, imported host pointer, semaphore, command queue, or GPU workload. Reported capability bits alone cannot establish cross-vendor direct access, P2P, VRAM residency, or usable end-to-end sharing.

## Build evidence

The build used the existing extracted copy-only LunarG SDK at `E:\the_harness\records\build_vulkan_real\toolchain\sdk`, Visual Studio 18 Community MSVC 14.51.36231 x64, and the exact cached SDK include/library locations in `records/build_vulkan_real/build/CMakeCache.txt`. It was split into direct `cl.exe /c` and direct `link.exe` calls after a bounded `vcvars64.bat` environment bootstrap. Each tool had a 60-second deadline; log capture was capped at 1 MiB per stream. The executable was not run.

Successful compile/link: `attempt_004/compile_receipt.json` reports `COMPILE_PASS`, `native_execution_performed=false`, input hashes unchanged, and all retained child processes absent after wait. The executable is `attempt_004/external_memory_query.exe`, 315,392 bytes, SHA-256 `67c69e60c12780415bfd62858536078e09d2749cc539ee3928079657bbc718b5`.

The source SHA-256 is `9ae6355ddc8ff72f4c33bce5116669ad84a734e7271287490926d136ec360e8c`. Compiler SHA-256: `064ea2a183199eea939974fa6033c1b61d11e9504112ab17179887f5011b615d`; linker SHA-256: `3e173cdf4a8ea9493d26ce007da3dba0e053f4002fa981fb47699db0f1da91a3`; Vulkan core header SHA-256: `944cd8f81d98e94999c7353dd632f73be471f2da95afecbc7d9ffe0ad5295deb`; Vulkan library SHA-256: `02caa31b8665a79f327cbfe97286fd7d0017c0b1f9b39eb78687b7a509de52b3`.

Earlier tool-bootstrap failures are preserved as separate attempts (`attempt_001` through `attempt_003`). They occurred before compiler invocation; none ran the query binary. The successful build did not overwrite those records.
