# Independent EGL proposal and exporter-validator audit

## Pins and scope

Reviewed without changing the provider artifacts:

- EGL probe: qwen_intel_egl_consumer/source.qwen_untrusted.cpp, SHA-256 816d95e717de6b5164485fa8a540ebb96f00ad9320fae313a6be62db8de08631 (14,885 bytes). Its companion token-scan tests SHA-256 da8eb59c94f549207851ca8a2833f5cbe2ec05772f18c64378b6c8be0440c4e8 (2,426 bytes).
- Python exporter checker: qwen_intel_exporter_sync_contract/source.qwen_untrusted.py, SHA-256 9da36c9700d1ecedde8f63913d4d72a953bfaf572e87df6753fc8388ca9742b0 (19,125 bytes). Companion tests SHA-256 ad8d75201b9f52bb59b3722d0bdc8fec743eae9fe32e78c72bf77e4ee72f8fc6 (5,592 bytes).
- The adjacent transport_headers.json and prior primary-source report are pinned in the provider batch and records/root_continuation_20261004/intel_device_nv_egl_route_20261004T204514Z/RESEARCH.md plus source_receipt.json. This prior research explicitly leaves exporter layout, producer completion/cache visibility, physical backing, and runtime gates unresolved.

Originals and their original provider tests are unchanged. Byte-for-byte review snapshots and test inputs/results are stored in this folder. No EGL API, GPU, native library, or provider call was made.

## EGL candidate findings

The .cpp-named artifact is Python (source.qwen_untrusted.cpp:1; imports sys/os/json/argparse/signal). It is a capability probe plus a hard stop, not the proposed producer/consumer workload. In main (:286-319), a --probe-consumer request checks the selected NVIDIA EGL display's ARGB8888/LINEAR/external-only support and returns ANALYSIS; otherwise a syntactically accepted contract still ends in NOT_CHECKED2 with the producer-consumer phase not launched (:314-319). It does not allocate a Level Zero buffer, import an FD with eglCreateImageKHR, create a GLES context/texture, write/read payload, establish a producer fence, compare bytes, or test cleanup of an actual FD. Consequently this artifact must not be reported as an interop, payload, sync, or transport result.

The extension-query path obtains extension functions with getattr(egl, ... eglQueryDevicesEXT/eglQueryDeviceStringEXT/eglGetPlatformDisplayEXT/eglQueryDmaBufFormatsEXT/eglQueryDmaBufModifiersEXT ...) (:157-258) instead of resolving extension entry points through eglGetProcAddress. EGL 1.5 states that implementations may statically export queryable functions but portable clients cannot rely on this; the direct-symbol lookup can therefore produce a false NOT_CHECKED2 on a conformant implementation with the extension available. Primary source: https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf, section 3.3.

After successful eglInitialize, ordinary error branches call eglTerminate, but an unexpected exception jumps to the outer handler (:268) without a finally that terminates the initialized display. The current probe creates no context/image/buffer, so this is limited to an EGL display/thread-state cleanup gap, but it should be fixed before repeatedly probing a driver. Also, Python signal.alarm(60) (:273) does not constitute a dependable parent-enforced timeout for a blocked foreign ctypes call; use an external retained process bound for that probe. The Level Zero header stash has no EGL/egl.h or GLES3/gl31.h under its SDK include path, and the proposed artifact is Python rather than a C++ translation unit, so an object-only C++ compile was not applicable and not attempted.

The companion tests_source.qwen_untrusted.txt only checks source tokens, length, and absence of selected substrings; it does not exercise EGL function lookup, failure cleanup, device selection, time bounds, or any import/work behavior.

## Exporter validator measured controls

After a full AST/import audit, the Python module was imported under an import guard and only its pure validate_candidate function was called against nine owned JSON inputs. Only explicit JSON paths could be opened; writes, network imports, subprocess/process APIs, and ctypes imports were blocked. The module has only import json at import time. Source and case hashes are pinned in this folder. The result is pure_control_results.json (SHA-256 3477c71f375f78de4ae0529405e2fe94873b07316f554f05e871b9e5bc83a001); runner audit_controls.py SHA-256 d2b256254536ef125b80f23bae122a3abf70baaa7a4a54a0b52418f3ca4b8e04.

Observed outcomes:

- Baseline metadata returned ANALYSIS, ok=true, with unresolved gates preserved. This is a metadata analysis result, not hardware acceptance.
- Required artifacts with nonexistent path values and fabricated nonempty spans still returned ANALYSIS, ok=true; the checker compares claimed SHA text to baked-in constants but does not read artifact paths or verify the named spans against content (source:60-78). Duplicate names also pass when the last duplicate has the expected metadata (:62-64).
- claims.p2p_proof="true" and claims.fence_proof=1 bypass the forbidden-claim check because it tests is True (:101-106), and still return ANALYSIS, ok=true.
- A consumer_read=true / producer_write=false operation set is accepted with ANALYSIS; a string "false" for allocate_export is treated as truthy. The checker does not validate the requested-operation bool schema or order/dependencies.
- Contradictory payload.word_count=1, fake digest, actual_work_proof=true, and nonfinite rmse=NaN returned ANALYSIS; no payload bytes/expected digest/metrics are read or cross-validated.
- producer=[] escapes as AttributeError ('list' object has no attribute 'get') (source:132-169) instead of a shaped fail-closed result.

These are provenance/schema-validator defects. The module does not execute the requested GPU operations; its fixed unresolved-gate list and ANALYSIS note state that transport is unqualified. Do not convert its ok=true metadata analysis into a runtime PASS. Its own companion tests exercise ten friendly source-built cases and do not cover these malformed or contradictory inputs.

## Review recommendation

Keep the EGL provider artifact at NOT_CHECKED; first resolve extension function pointers portably and guarantee cleanup/outer deadline for the capability probe. Do not admit producer/consumer execution from it. The exporter checker needs strict input-type validation, schema/dependency checks, actual artifact-byte/span verification, payload/metric consistency checks, and fail-closed malformed-type handling before it can serve as an evidence gate. These findings do not establish that EGL import or Intel-to-NVIDIA interop is impossible.
