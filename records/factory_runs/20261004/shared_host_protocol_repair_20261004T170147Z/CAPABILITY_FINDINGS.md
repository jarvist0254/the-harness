# Vulkan external-host-memory capability query

The root-admitted executable completed one read-only query. Status: `QUERY_COMPLETE`, exit 0, 0.297 seconds, PID 83372. The retained child process was absent after wait and again on independent process lookup. Both raw streams stayed below the 256 KiB caps (stdout 3,301 bytes; stderr 0). Full JSON parsed and passed the device/query-matrix checks. Source, source copy, executable, Python, admission, and controller hashes matched before and after; the parent environment fingerprint was unchanged.

The Vulkan instance enumerated exactly two physical devices:

| Device | `VK_EXT_external_memory_host` | Minimum imported host-pointer alignment | HOST_ALLOCATION, transfer-only | HOST_ALLOCATION, storage+transfer | HOST_MAPPED_FOREIGN_MEMORY, both usages |
|---|---|---:|---|---|---|
| NVIDIA GeForce RTX 5070 Ti (`10de:2c05`) | Advertised | 4,096 bytes | Importable and exportable; compatible handle mask `0x80` | Importable and exportable; compatible handle mask `0x80` | Not importable/exportable; feature mask `0x0` |
| AMD Radeon(TM) Graphics (`1002:164e`) | Advertised | 4,096 bytes | Importable, not exportable; compatible handle mask `0x80` | Importable, not exportable; compatible handle mask `0x80` | Not importable/exportable; feature mask `0x0` |

For both devices, the tested buffer flags were 0. The exact queried usages were `TRANSFER_SRC | TRANSFER_DST` and `STORAGE_BUFFER | TRANSFER_SRC | TRANSFER_DST`. The returned `0x80` compatibility mask corresponds to HOST_ALLOCATION. The NVIDIA feature mask `0x6` combines importable and exportable; AMD's `0x4` indicates importable only. Both HOST_MAPPED_FOREIGN_MEMORY queries returned no supported features. Intel vendor ID `0x8086` had zero devices in this Vulkan enumeration and is reported as `NOT_ENUMERATED_BY_THIS_VULKAN_INSTANCE` only.

These are physical-device capability advertisements. No `VkDevice`, buffer, memory allocation, host-pointer import, semaphore, queue submission, payload transfer, or GPU work occurred. This does not prove successful import, usable cross-vendor sharing, direct GPU-to-GPU access, P2P, or physical residency. No Intel/NVIDIA link is established.

Raw stdout SHA-256: `8c3e9fc93014f779f11feb241f945944c22392dede4b619783cff9c771cdcc3f`. Raw stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Receipt SHA-256: `7ba345bd6fe0afff8bb2c96596bff74fd7b59e122a273357acb4d9984cd63274`. Full detail remains in `run_receipt.json` and `stdout.raw.log`.
