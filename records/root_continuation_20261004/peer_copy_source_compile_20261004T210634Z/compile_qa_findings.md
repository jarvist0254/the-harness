# Level Zero peer-copy candidate: compile-only QA and static review

## Result

The unchanged candidate did not compile. `/usr/bin/c++` (Ubuntu GCC 13.3.0) exited 1 in 1.031 s while compiling the text artifact as C++17 with `-c -x c++`. There were five diagnostics, all for `ZE_RESULT_ERROR_FAILURE`, which the pinned `ze_api.h` does not declare; GCC suggested `ZE_RESULT_ERROR_UNKNOWN`. No object was produced. The candidate and its test artifact were never executed, imported, linked, or used to call a GPU API.

## Exact compile command

```text
C:\Windows\System32\wsl.exe -d Ubuntu-24.04 --exec /usr/bin/timeout --signal=TERM --kill-after=5s 85s /usr/bin/c++ -std=c++17 -c -x c++ -I/mnt/e/the_harness/records/toolchains/cuda_driver_headers_20261004/include -I/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include /mnt/e/the_harness/records/factory_runs/20261004/qwen_transfer_four_prep_20261004T202539Z/qwen_l0_peer_repair/source.SCHEMA_REFUSED_UNTRUSTED_REVIEW_ONLY.txt -o /mnt/e/the_harness/records/root_continuation_20261004/peer_copy_source_compile_20261004T210634Z/candidate.o
```

The source is named `.txt`, so `-x c++` explicitly selected the input language. The compile had an 85-second Linux timeout plus 5-second kill grace and a 100-second outer WSL bound; it completed far inside both. Raw stderr is `compile.stderr.txt` (4,836 bytes); stdout is empty. Exact argv, timing, PIDs, and before/after pins are in `compile_receipt.json`.

## Compiler diagnostics

All five diagnostics identify the same unavailable enum constant in the candidate:

- Source line 76: synthetic error result for a null source allocation.
- Source line 77: synthetic error result for a null destination allocation.
- Source line 79: synthetic error result for a null host allocation.
- Source line 82: synthetic error result for a source-owner/type mismatch.
- Source line 84: synthetic error result for a destination-owner/type mismatch.

The pinned header defines `ZE_RESULT_ERROR_UNKNOWN` at `ze_api.h:286`; `ZE_RESULT_ERROR_FAILURE` has no declaration. This is a compiler finding only; no correction was made.

## Source scope and intended measurement

The translation unit includes only the pinned `level_zero/ze_api.h` and standard C/C++ headers. It enumerates Level Zero GPU devices, requires two distinct Intel device UUIDs on the same driver, checks directed peer-access properties, allocates source/destination device memory plus host readback memory, fills 65,536 bytes on the source device, optionally overwrites one GPU word at byte offset 32,768, copies source to destination on an eligible queue, reads back, and compares all 16,384 words against the pattern. It emits `direct_transport_qualified=false` and labels successful bytes as observed payload only. The source makes no affirmative VRAM-direct-P2P claim.

## Static safety and evidence gaps

These are source-review findings, not runtime observations:

- On any `zeFenceHostSynchronize` error, including timeout, the path calls `emit_fail`, which immediately invokes `destroy_tracker`. That helper destroys fences, lists, queues, frees memory, and destroys the context without first establishing that submitted work has drained. If a fence times out while a command is still active, cleanup can release resources still in use. The affected waits are the source fill, corruption fill, peer copy, and readback at source lines 95, 97, 108, and 116.
- The CLI loop at line 49 accepts repeated `--inject-corruption` flags and silently ignores extra arguments after collecting two UUIDs. Unexpected command-line input therefore does not consistently fail closed.
- Driver and per-driver device counts from enumeration are used to size vectors without an explicit cap (lines 54-57). This leaves allocation bounds dependent on returned counts.
- Device matching counts only handles returned by `zeDeviceGet`; it does not enumerate subdevices with `zeDeviceGetSubDevices`. The `subdeviceId != 0` check at line 62 is not, by itself, evidence that root/subdevice aliases were exhaustively excluded.
- The negative control returns a failure for any nonzero mismatch count when injection is requested. It reports the first mismatch and injected index, but does not require that exactly one mismatch occurred at the injected index with the injected value. A separate comparator control would need that condition before treating corruption as specifically detected.
- The source does full byte-pattern comparison on the successful path and performs corruption through a device memory-fill command. That establishes the intended test shape in source; it does not establish hardware execution, directionality beyond its selected copy path, transport topology, or successful cleanup.

The accompanying Python artifact was read as text only. It checks source tokens and a few fabricated receipt shapes; its positive fixture does not validate actual allocation-owner/type consistency or prove the native program ran. It was not executed.

## Provenance

- Candidate SHA-256 before/after: `4144749084d6b74dddfb5ff314c461c8444c12413f57bb380a0bbe32d13c893f`.
- Test artifact SHA-256 before/after: `cc09cb3f891be064c6bd0c10f6e1dceda532cc3c4b4aa3934f199cc53bb4ffc9`.
- Pinned Level Zero `ze_api.h`: `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de`.
- Compiler: `c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`; `/usr/bin/c++` SHA-256 `1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769` before/after.
- All candidate, test, header, supervisor, WSL, and compiler pins matched before and after; the owned WSL PIDs were absent after wait.
- Compile controller SHA-256: `b549dbd8f6429b25cf3ab591ae83819fa3f98e6b41deeb88fedf0640e5ca01e3`.
