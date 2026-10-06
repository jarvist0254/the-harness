# Level Zero query measured-repair source review

Status: full candidate and provider-test source read. Candidate has not been imported or executed, and no Level Zero runtime, device, or GPU API was called. Object-only compilation is separately authorized; provider tests and native runtime remain out of scope.

## Pins and API surface

- Candidate: `records/factory_runs/20261004/l0_compiler_two_prep_v2_20261004T214600Z/qwen_l0_query_measured_repair/source.qwen_untrusted.cpp`, 18,540 bytes, SHA-256 `27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2`.
- Provider test source: sibling `tests_source.qwen_untrusted.txt`, 12,803 bytes, SHA-256 `df49c5aa406c27a9d1cee14ded78804ef95551a0eac703635c9268bb13f06ac8`.
- Header: `records/toolchains/level_zero_20261004/sdk/include/level_zero/ze_api.h`, version v1.19-r1.19.12 in staged oneAPI Level Zero v1.34.0 source, SHA-256 `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de`.
- Compiler: WSL Ubuntu `/usr/bin/c++`, GCC 13.3.0, binary SHA-256 `1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769`.

The source uses only `ze_api.h` and standard C/C++ headers. The pinned header prototypes for `zeInit`, `zeDriverGet`, `zeDeviceGet`, `zeDeviceGetSubDevices`, `zeDeviceGetProperties`, external-memory properties, queue-group properties, `zeDeviceCanAccessPeer`, and `zeDeviceGetP2PProperties` match the call shapes in the candidate. The candidate requests `ZE_INIT_FLAG_GPU_ONLY`. Compilation is object-only (`-c`): it does not link the loader or execute the candidate.

## Static findings and evidence limits

The implementation is a bounded Level Zero inventory query, not a transfer test. It does not create a device context, memory allocation, command list, fence, or queue work; and it emits `direct_transport_qualified:false`. Its P2P fields remain API-reported capability values only.

The current synthetic provider suite covers normal two-root enumeration, one init error, duplicate root-handle aliasing, and zero drivers. It does not exercise most API failure points, unsupported external-memory or peer-property queries, device/subdevice/root capacity truncation, queue-group truncation, or output-buffer overflow. It also does not independently stress JSON escaping, UTF-8 device names, count/list inconsistencies, or aliasing across drivers with equal UUIDs.

The writer stops appending after capacity is exhausted; the final truncation fields then cannot be emitted. The normal path sets exit status 0 before serialization, so output capacity exhaustion may produce a partial JSON document with a nominal success exit. `output_truncated` and inventory truncation are reported as fields but the consumer must still validate complete JSON and treat truncation as incomplete inventory. The source's global arrays and counters are reset on each collection, but this does not make the C++ stub a complete validation of actual driver behavior.

## Limits

An object compile can establish source/header compatibility only. No provider tests, link, driver load, runtime query, or cross-vendor transport claim is part of this evidence.

The authorized `-c` compile completed with GCC 13.3.0: exit code 0, 27,176-byte object, 0 warnings and 0 errors. GCC emitted only large-source column-tracking notes for the one-line JSON serializer. Raw streams, object, before/after pins, compiler SHA, and bounded command are in `compile_receipt.json` and sibling files.
