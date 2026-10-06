# Shared host import prototype: not admitted

The pinned draft (`21a0379e778bdb8c31e5da7774410b59236e2b6f72a87eaf1b68ff584a666815`) remains source only. ROOT read the source and current Khronos specification. No compile, memory import or GPU submission is admitted by this review.

Three issues prevent using this draft as evidence of a valid transport:

1. The producer releases one buffer view while the consumer acquires a different view of the same host payload in another instance. The specification permits repeated host-payload imports and defines FOREIGN ownership, but also says ownership transfer leaves other aliased resources' contents undefined. This review does not establish that the draft's two views qualify as the corresponding external resource. That question remains unresolved; byte parity alone would not resolve it.
2. The negative control writes the original host pointer after the producer's release and before the consumer's acquire. The ownership rules prohibit an acquire after intervening modification other than a matching release. A revised control should corrupt on the producing GPU before its release, or use a separately justified host-domain protocol. The same original pointer is not inherently forbidden for HOST_VISIBLE imports; access still needs a correct synchronization protocol.
3. The private readback budget is checked after both allocations. Each allocation must be checked against a per-device share of the budget before `vkAllocateMemory`. Capability and alignment failures must remain refusals.

The contract also overstates undefined contents on import: that restriction is described for imports into non-host-visible memory. This draft explicitly requires HOST_VISIBLE and HOST_COHERENT types. General memory-import text requires preserving the imported contents. The source initializes host RAM before import, despite the contract saying it does not; that initialization cannot be described as GPU-produced data.

Primary references read on 2026-10-04:

- [Host pointer import](https://docs.vulkan.org/refpages/latest/refpages/source/VkImportMemoryHostPointerInfoEXT.html): same payload may be imported into multiple instances; original-pointer access and lifetime restrictions.
- [Memory allocation](https://docs.vulkan.org/spec/latest/chapters/memory.html): import contents, host visibility and host cache synchronization.
- [Synchronization](https://docs.vulkan.org/spec/latest/chapters/synchronization.html): external ownership, matching ranges, intervening modification and alias contents.

This is a rejection of this protocol as presently justified, not evidence that all shared-host methods are impossible. The executed property query already found HOST_ALLOCATION import capability on the installed NVIDIA and AMD devices. No Intel device participated. A future successful shared-host test must remain labelled SHARED_HOST_BACKING_NOT_VRAM_P2P.
