# Shared host-allocation import fixture — design draft

Status: **DESIGN ONLY — NOT COMPILED OR RUN**. This is a bounded, disposable experiment proposal. It is not a production feature, throughput benchmark, VRAM-sharing claim, or admission of the Qwen executor.

## Question and labels

Can a single Windows `VirtualAlloc` allocation, imported independently as `VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT` by one NVIDIA and one AMD Vulkan device, carry GPU-produced bytes to the other device and back, with the full returned payload checked on the CPU?

The only allowed positive label is `SHARED_HOST_BACKING_NOT_VRAM_P2P`. A positive result means both Vulkan devices successfully imported and used the same host virtual allocation, and the producer's transfer writes were observed in the consumer's private readback. It does **not** establish device-local residency, VRAM-to-VRAM access, direct P2P, peer bandwidth, or an optimal transport path. Synchronization is `CPU_FENCE_CONTROL_NO_CPU_PAYLOAD_TRANSFER`: the CPU waits on each producer/consumer Vulkan fence and performs ownership control; it does not copy the payload between GPU contexts. The corruption case deliberately changes one host byte and is separately labeled.

## Admission gates

The previous exact capability query reported `HOST_ALLOCATION` importable on the installed NVIDIA (`0x10de`) and AMD (`0x1002`) devices, 4096-byte minimum host pointer alignment on both, and no `HOST_MAPPED_FOREIGN_MEMORY` support. That receipt was capability-only. This prototype must re-query at runtime and refuse before allocation or queue submission unless all the following hold:

- Exactly one selected physical device has vendor ID `0x10de` and exactly one has `0x1002`; device UUIDs differ. Each selected device advertises `VK_EXT_external_memory_host` and `VK_EXT_queue_family_foreign`, and the latter is enabled when its device is created.
- `vkGetPhysicalDeviceExternalBufferProperties` for flags `0`, usage `TRANSFER_SRC | TRANSFER_DST`, and handle `HOST_ALLOCATION` reports `IMPORTABLE` and includes `HOST_ALLOCATION` in `compatibleHandleTypes` on both devices. No exportability is required.
- `VK_EXT_external_memory_host` reports a nonzero `minImportedHostPointerAlignment`; the actual pointer is aligned to both devices' minimum and to each resource's `VkMemoryRequirements::alignment`.
- For the actual `VirtualAlloc` pointer, `vkGetMemoryHostPointerPropertiesEXT` succeeds on each device. Its returned `memoryTypeBits` intersect the buffer's requirement bits in a type with **both** `HOST_VISIBLE` and `HOST_COHERENT`. No noncoherent, device-local-only, or alternative-handle fallback is allowed.
- Each shared buffer's `VkMemoryRequirements::size` is no larger than 256 KiB. Each import uses `allocationSize = 256 KiB`, binds at offset zero, and has exactly the same `VirtualAlloc` pointer. The allocation is created and both imports are bound before any GPU access, since host-import contents are undefined on import.
- Each device has one transfer-capable queue. Each private readback allocation is host visible and coherent; total private Vulkan allocation requests stay at or below 2 MiB. The host payload is 256 KiB. Any failed query, alignment, allocation, bind, queue, or extension gate returns `NOT_CHECKED`/`REFUSED` without trying another memory type or transport.

The selected Vulkan instances are intentionally separate, one per physical device. The source uses `VK_QUEUE_FAMILY_FOREIGN_EXT` for cross-instance handoff. It must never substitute `VK_QUEUE_FAMILY_EXTERNAL`: the latter is limited to the same physical device and driver, while `FOREIGN` is defined for resources accessed outside the current Vulkan instance and supports different devices/drivers when the extension is advertised and enabled.

## Payload and rounds

The payload is exactly 262,144 bytes, divided into 64 aligned 4,096-byte chunks. GPU producer work consists of 64 `vkCmdFillBuffer` commands, one per chunk, with deterministic but distinct 32-bit values derived from a fixed seed. The CPU constructs a separate expected byte vector before submission; it never initializes the shared payload. For each direction, the other GPU acquires the imported shared buffer and issues one `vkCmdCopyBuffer` into its own private readback buffer. After the consumer's fence signals, compare every payload byte against the producer's expected vector.

Run sequentially:

1. NVIDIA produces and AMD consumes; require 262,144/262,144 bytes equal.
2. AMD produces and NVIDIA consumes; require 262,144/262,144 bytes equal.
3. NVIDIA produces a fresh pattern and releases it; after that producer fence has signaled and before the AMD acquire, the CPU flips byte offset 12,345 in the shared `VirtualAlloc` payload. AMD consumes and the CPU compares all bytes to the uncorrupted expected vector. The negative control passes only if the full scan detects exactly one mismatch, at offset 12,345, with the returned byte equal to expected XOR `0x01`.

No CPU payload copy is allowed between producer and consumer. The CPU may read the consumer's private readback for full verification and may mutate the one declared corruption byte only in round 3.

## Ownership and synchronization protocol

All imports/resources are created before the first GPU use. A newly created exclusive buffer has no owner until its first queue use; the first NVIDIA producer use is therefore the Vulkan-defined implicit first-use acquire on its local queue. Every subsequent use explicitly follows the external-ownership cycle below. For each imported buffer alias and exact `[0, 262144)` range:

1. Producer records its writes, then a release `VkBufferMemoryBarrier` from its local transfer queue family to `VK_QUEUE_FAMILY_FOREIGN_EXT` (`TRANSFER_WRITE` to no destination access). Submit with a fence and wait at most 5 seconds.
2. The CPU proceeds only after that producer fence signals. This is host-side control; no inter-device payload staging occurs.
3. Consumer records a matching acquire barrier from `VK_QUEUE_FAMILY_FOREIGN_EXT` to its local transfer queue family (no source access to `TRANSFER_READ`), copies shared buffer to its private readback, adds a transfer-write-to-host-read barrier for the readback, and releases the shared range back to `FOREIGN_EXT` after the read.
4. Submit with a consumer fence and wait at most 5 seconds. Only after it signals may the CPU inspect readback, alter the declared corruption byte, or begin the next round.

The implementation must preserve Vulkan's exact matching release/acquire range and queue-family indices. It must not use `VK_QUEUE_FAMILY_EXTERNAL` for this cross-vendor path. In each context, later producer use reacquires its buffer from `FOREIGN_EXT`; consumer use also acquires from `FOREIGN_EXT`. The source draft explicitly relies on the external-memory ownership model applying to the corresponding buffer views independently bound to the same imported host payload. Root must review this alias/handoff assumption against the spec and driver model before any compile or run. If that correspondence cannot be justified, the fixture stops here rather than weakening ownership synchronization.

Each individual `vkWaitForFences` timeout is 5 seconds. There is no infinite fence, queue-idle, or device-idle wait. A timeout or error after successful queue submission must terminate the child without running destructors that could free the host pointer while device work might remain active; process teardown is the cleanup boundary. Normal teardown occurs only after all submitted fences have signaled: unmap and destroy private readback buffers/memory, destroy each shared buffer before its imported `VkDeviceMemory`, destroy each device/instance, then `VirtualFree` the shared allocation. An outer retained-process supervisor must enforce 30 seconds total, capture bounded stdout/stderr, and verify child reaping before this prototype is ever run.

## Evidence fields and interpretation

The eventual runtime record should report selected vendor/device IDs and UUIDs, driver UUIDs, extension presence/enabled state, queried and pointer-specific handle/feature/type masks, minimum and actual pointer/resource alignment, per-device memory requirements and selected heap/type flags, allocation-request totals, all three byte counts/mismatch offsets, each fence outcome, and overall elapsed time. Transport text remains `SHARED_HOST_BACKING_NOT_VRAM_P2P`; there is no P2P or VRAM claim even on byte parity. Unsupported gates must be `NOT_CHECKED`/`REFUSED`, not coerced into a failure or success.

## Primary references

- [Vulkan memory allocation: host external memory](https://docs.vulkan.org/spec/latest/chapters/memory.html) — host pointer import, same payload imported multiple times, pointer alignment/type-bit query, contents undefined on import, host/device synchronization, payload lifetime.
- [VK_EXT_queue_family_foreign](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_queue_family_foreign.html) — foreign queue family represents queues external to the instance and can include other physical devices/drivers; more restrictive than EXTERNAL.
- [Vulkan synchronization and cache control](https://docs.vulkan.org/spec/latest/chapters/synchronization.html) — release/acquire barriers, exact ranges and queue family ownership, host fence synchronization.

Those specifications define API semantics; they do not guarantee that either installed driver can successfully import the particular pointer, preserve the bytes across alias views, or execute the proposed cross-vendor handoff. Those are runtime questions for a separately admitted experiment.
