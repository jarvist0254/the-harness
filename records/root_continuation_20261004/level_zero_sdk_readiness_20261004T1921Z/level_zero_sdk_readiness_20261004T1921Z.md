# Level Zero SDK staging and DMA-BUF readiness — 2026-10-04

## Staged official Windows SDK

The GitHub Releases API `latest` endpoint and the explicit tag endpoint both identified `oneapi-src/level-zero` **v1.34.0**, published 2026-09-17, as the current non-prerelease at retrieval time. Its release notes identify Level Zero Spec 1.19.12. The exact Windows asset was `https://github.com/oneapi-src/level-zero/releases/download/v1.34.0/level-zero-win-sdk-1.34.0.zip` (317,053 bytes). The SHA-256 advertised in official release metadata matches the downloaded archive: `3050280cc94b7a5db7fb173391fcced9b7284ae196bcaf05a566d2911baa7733`.

I extracted only `include\level_zero\ze_api.h` and `lib\ze_loader.lib` under `E:\the_harness\records\toolchains\level_zero_20261004\sdk`. Header SHA-256: `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de` (1,240,682 bytes). Import-library SHA-256: `be1ff9cb298a54463fa4c04117ffe0ed6ddf54a7d2419745ebfc4381d28c6d30` (256,346 bytes). The Windows SDK archive contains no `ze_loader.dll`, so this stages a compile/link interface only. No archive program, compiler, loader, fixture, or GPU operation was executed. The MIT license and raw release metadata, signature asset, and versioned API-document snapshots are in the `upstream` subfolder; the detached `.sig` was saved but not cryptographically verified. The API-provided archive digest matched.

For a direct Level Zero compile, add `sdk\include` to includes and link `sdk\lib\ze_loader.lib`. Runtime calls still require a loader DLL and a working driver/device stack, which this staging did not install or verify.

## CUDA-exported Linux DMA-BUF question

The current Level Zero header defines distinct handle flags: `ZE_EXTERNAL_MEMORY_TYPE_FLAG_OPAQUE_FD` is an opaque POSIX FD; `ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF` is a file descriptor for a Linux dma_buf; `ZE_EXTERNAL_MEMORY_TYPE_FLAG_OPAQUE_WIN32` is an NT handle (`ze_api.h`, lines 434–436). Level Zero describes external-memory import as optional and says the device reports supported import types via `zeDeviceGetExternalMemoryProperties`. For a supported DMA-BUF type, its documented route is `ze_external_memory_import_fd_t` with `ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF` chained through the allocation descriptor to `zeMemAllocDevice`.

Thus, a CUDA-produced FD can be *attempted* as a Level Zero DMA-BUF import only when it is actually a Linux dma_buf FD and the importing Level Zero device advertises `DMA_BUF` in `memoryAllocationImportTypes`; the importing allocation size/alignment must satisfy the importer and exporter contracts; the precise cross-vendor layout and alignment constraints remain unknown until the actual exporter object and device are specified. CUDA's `cuMemExportToShareableHandle(..., CU_MEM_HANDLE_TYPE_POSIX_FILE_DESCRIPTOR, ...)` produces an opaque POSIX FD, which is not proof of a DMA-BUF. CUDA documents DMA-BUF export through `cuMemGetHandleForAddressRange(..., CU_MEM_RANGE_HANDLE_TYPE_DMA_BUF_FD, ...)` subject to `CU_DEVICE_ATTRIBUTE_DMA_BUF_SUPPORTED` (and, for host allocations, its host-allocation support attribute). It requires page-aligned address/size; reserved virtual ranges must be fully mapped. The API can return `CUDA_ERROR_NOT_SUPPORTED`.

This is a Linux-only handle path; it cannot be exercised as the same `DMA_BUF` FD path on the current Windows host. Level Zero's existence of a generic import API does not guarantee that a particular Intel driver accepts a particular CUDA-produced object, nor does successful import establish direct CUDA-to-Intel P2P bandwidth, synchronization, cache coherency, or JLink protocol acceptance. A later source-specific test would first need both capability bits and a genuine exporter DMA-BUF; cross-vendor import and data correctness remain `NOT_CHECKED`.

For peer-access semantics, Level Zero separately documents `zeMemOpenIpcHandle` as requiring P2P access when importing a different Level Zero device. That IPC rule is distinct from external DMA-BUF import. A successful external import must not be reported as P2P proof.

## Boundaries

This task staged the official Windows development asset and checked public API definitions only. It did not install drivers, modify BIOS or global PATH, query the GPU, compile a fixture, run downloaded binaries, or claim P2P/protocol acceptance. Evidence files and exact source URLs are recorded in `E:\the_harness\records\toolchains\level_zero_20261004\upstream\UPSTREAM_RECEIPTS.json`.

