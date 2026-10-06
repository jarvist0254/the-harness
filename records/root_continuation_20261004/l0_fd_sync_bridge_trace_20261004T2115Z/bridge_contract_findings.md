# Pinned Intel L0 DMA-BUF import and semaphore trace

Scope: source-only tracing against the staged official Intel compute-runtime tree at commit `d4fc0756006fa28738766cb66034dc9acadea91e`. No compiler, provider, GPU, context, allocation, or transfer was run. The root staging receipt is `records/root_continuation_20261004/intel_runtime_contract_sources_20261004T2100Z/PINNED_SOURCE_RECEIPT.json`. Additional same-commit files are recorded in `source_manifest.json` in this folder; each was obtained by exact path from that commit and checked against the tree entry's declared Git blob ID and byte size, then locally SHA-256 pinned.

## DEVICE external-FD import and lifetime

For `zeMemAllocDevice` with a shared opaque-FD or DMA-BUF descriptor, `Context::allocDeviceMem` calls `getMemHandlePtr` with `isHostIpcAllocation=false` (`context.cpp:301-315`). A null import returns `ZE_RESULT_ERROR_INVALID_ARGUMENT` before `closeExternalHandle(fd)` (`context.cpp:316-319`). Thus, on this path, the caller's FD is consumed by the L0 context only after successful import; on this import failure the caller retains it. The close implementation invokes `close(2)` only for the DRM driver (`context_drm_or_wddm.cpp:59-67`).

The path is `Context::getMemHandlePtr` -> `DriverHandle::importFdHandle` -> `MemoryManager::importFdHandle` -> `DrmMemoryManager::createGraphicsAllocationFromSharedHandle` (`context_drm_or_wddm.cpp:70-107`, `driver_handle.cpp:692-715`, `memory_manager.cpp:1556-1603`, `drm_memory_manager.cpp:1836-2005`). For this non-host-IPC case, NEO's shared-handle import calls PRIME_FD_TO_HANDLE, tags the imported allocation `MemoryPool::systemCpuInaccessible`, and returns a BO-backed `DrmAllocation` with the original FD stored as its shared handle (`drm_memory_manager.cpp:1836-1877, 1993-2005`). L0 marks the allocation imported and classifies it internally as `deviceUnifiedMemory` (`memory_manager.cpp:1595-1603`). These runtime enum/pool labels describe this implementation's allocation bookkeeping; they do not establish where another driver's allocation physically resides or prove VRAM P2P.

On destruction, `DrmMemoryManager::freeGraphicsMemoryImpl` unrefs the BO and closes the shared handle only for non-imported allocations (`drm_memory_manager.cpp:2058-2107`). Since the imported allocation has `setIsImported()`, the importer-side descriptor is not closed a second time through `closeSharedHandle`; L0 already closed its input FD after successful import. This conclusion is specifically for `zeMemAllocDevice`/direct DMA-BUF import above. Do not apply the separate `createUSMHostAllocationFromSharedHandle(... consumeFd ...)` host-IPC ownership rules to it.

## External semaphore import and operations

`ExternalSemaphoreLinux::importSemaphore` passes the incoming FD to DRM `syncObjFdToHandle`; it then closes the descriptor when `fd > 0` before checking ioctl success (`external_semaphore_linux.cpp:55-74`). This differs from the memory-import failure path. The implementation's `fd > 0` guard means this source does not close FD 0; any wrapper must handle that edge deliberately and must not assume uniform ownership semantics.

Wait and signal are immediate DRM ioctls in `ExternalSemaphoreLinux::enqueueWait` and `enqueueSignal`, not command-list appends: timeline and binary paths invoke `syncObjTimelineWait`/`syncObjWait` or `syncObjTimelineSignal`/`syncObjSignal` (`external_semaphore_linux.cpp:77-145`). The waits use an effectively unbounded `int64` timeout and `WAIT_FOR_SUBMIT`; they are not suitable evidence for a bounded protocol. At the Level Zero wrapper layer, `ExternalSemaphoreImp::semaphoreWait` and `semaphoreSignal` store the boolean result in `[[maybe_unused]]` locals and only print it when debug output is enabled (`external_semaphore_imp.cpp:16-35`). The visible implementation does not propagate those ioctl failures to a ZE result.

The inspected `cmdlist.cpp` and `cmdqueue.cpp` have no external-semaphore references. This is bounded to those two pinned files; it is not a claim about every possible entry point or application-side ordering. The shown semaphore signal method has no queue/fence parameter and immediately issues the DRM signal ioctl. Therefore the traced API alone does not prove that a producer GPU queue has completed before the host issues the signal. A correct bridge must establish producer completion first and must account for errors and finite waits.

## Bridge verdict and missing proof

These sources establish how this Intel runtime imports its own DMA-BUF FD and sync FD and which layer closes them. They do not show a legal Intel-to-NVIDIA producer-completion bridge, a conversion from an Intel DRM syncobj to a sync-file accepted by NVIDIA EGL, or an NVIDIA-side completion/release path. No memory cache-domain visibility/barrier guarantee across drivers is established. There is no cross-vendor allocation/import/transfer evidence here, and no direct P2P or dedicated-VRAM claim follows from `deviceUnifiedMemory`, `systemCpuInaccessible`, or a semaphore handle.

Any future one-way experiment still needs a pinned, compatible semaphore export/import path; verified FD ownership on every success/failure edge; a bounded producer GPU-completion wait before signaling; a bounded consumer completion proof; error propagation; a cache/visibility rule for the shared payload; and safe cleanup for timeout while work may be in flight. If these cannot be justified from the actual APIs and driver pairing, keep transfer/import disabled and report `NOT_CHECKED`/unsupported.

## Source references

- Root pin and original staged sources: `records/root_continuation_20261004/intel_runtime_contract_sources_20261004T2100Z/PINNED_SOURCE_RECEIPT.json`.
- Additional path/size/SHA-256 pins: `source_manifest.json`.
- Exact same-commit call-chain files: `records/root_continuation_20261004/intel_l0_import_sync_trace_20261004T210634Z/{context.cpp,context_drm_or_wddm.cpp,driver_handle.cpp,memory_manager.cpp,cmdlist.cpp,cmdqueue.cpp}`.
- Exact semaphore/DRM files: `records/root_continuation_20261004/intel_runtime_contract_sources_20261004T2100Z/{level_zero__core__source__semaphore__external_semaphore_imp.cpp,shared__source__os_interface__linux__external_semaphore_linux.cpp,shared__source__os_interface__linux__drm_memory_manager.cpp}`.
