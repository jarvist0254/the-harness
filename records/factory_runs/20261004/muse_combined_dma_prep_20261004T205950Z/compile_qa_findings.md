# CUDA + Level Zero DMA-BUF candidate: compile-only QA

## Verdict

`COMPILE_FAILED` for the immutable provider candidate. GCC 13.3.0 compiled in C++17 object-only mode (`-c`) and exited 1 in 1.094 s. No object was produced. There was no link, candidate execution, CUDA/Level Zero runtime call, or GPU activity. The source and pinned API headers matched before and after compilation.

## Exact compile command

```text
C:\Windows\System32\wsl.exe -d Ubuntu-24.04 --exec /usr/bin/timeout --signal=TERM --kill-after=5s 85s /usr/bin/c++ -std=c++17 -c -I/mnt/e/the_harness/records/toolchains/cuda_driver_headers_20261004/include -I/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include /mnt/e/the_harness/records/factory_runs/20261004/cuda_l0_device_dmabuf_prep_20261004T195400Z/qwen_cuda_l0_device_dmabuf_v3/source.qwen_untrusted.cpp -o /mnt/e/the_harness/records/root_continuation_20261004/cuda_l0_source_compile_20261004T202000Z_attempt2/candidate.o
```

The outer WSL process had a 100-second bound; the in-WSL compiler command had an 85-second timeout plus 5-second termination grace. It completed normally before either bound. Compiler stderr is preserved verbatim in `compile.stderr.txt` (14,061 bytes); stdout is empty. Full argv, timing, PIDs, and before/after pin checks are in `compile_receipt.json`.

## Measured compile errors and declaration bindings

The compiler found these API mismatches in provider source SHA-256 `e8916bc07ee2a058f5af9371b073b2f47810071c6949480fe0c0a4b2d3064411`:

- Candidate line 43 calls `cuCtxCreate(&cctx,0,cdev)` with three arguments. Pinned CUDA `cuda.h:6648` declares `cuCtxCreate(CUcontext *, CUctxCreateParams *, unsigned int, CUdevice)` (four arguments); the header macro at line 90 maps the spelling to `cuCtxCreate_v4`.
- Candidate line 58 reads `ep.memoryImportSupported`, which is not a member. Pinned `ze_api.h:2738-2748` declares `memoryAllocationImportTypes`, `memoryAllocationExportTypes`, `imageImportTypes`, and `imageExportTypes`. The DMA-BUF enum is declared at `ze_api.h:435`.
- Candidate line 60 writes `ifd.type`, which is not a member. Pinned `ze_api.h:8080-8088` declares `ze_external_memory_import_fd_t` members `stype`, `pNext`, `flags`, and `fd`.
- Candidate line 62 uses undefined `ZE_COMMAND_QUEUE_GROUP_COPY_BIT` and `ZE_COMMAND_QUEUE_GROUP_COMPUTE_BIT`. The pinned header names these flags `ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COPY` and `ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COMPUTE` at lines 2378-2381.
- Candidate line 64 calls `zeMemAllocHost` with four arguments and shifts the output pointer into the alignment position. Pinned `ze_api.h:7619-7627` declares five arguments: context, descriptor, size, alignment, and output pointer.
- Candidate line 65 calls `zeCommandListCreate` with the device as argument one and omits the context. Pinned `ze_api.h:3983-3988` requires context, device, descriptor, and output handle.
- Candidate line 66 calls `zeEventPoolCreate` with four arguments and omits the device-handle-array parameter. Pinned `ze_api.h:5507-5517` declares five arguments: context, descriptor, device count, optional device array, and output handle.
- Candidate line 69 calls `zeCommandQueueCreate` with the device as argument one and omits the context. Pinned `ze_api.h:3588-3593` requires context, device, descriptor, and output handle.

The compiler emitted 10 diagnostics total; the `zeMemAllocHost` argument-count and conversion messages describe the same call-site defect. These are compile-time API incompatibilities, not evidence about whether either driver supports DMA-BUF import or whether a corrected program could transfer data.

## Provenance and process state

- Candidate SHA-256 before/after: `e8916bc07ee2a058f5af9371b073b2f47810071c6949480fe0c0a4b2d3064411` (unchanged).
- CUDA `cuda.h`: `7a79d67ca888061b1dfbe4739b51ad64f85a2f3ad874947ce09b2c635b4c7072`.
- CUDA `cudaTypedefs.h`: `77eb4072ae5da75bec31c4cf6291967e8ecbd6981ece0d47b07dbbabf781782c`.
- Level Zero `ze_api.h`: `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de`.
- Compiler: `c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`; `/usr/bin/c++` SHA-256 `1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769` before/after.
- Four owned WSL PIDs in the receipt were absent after wait.
- Compiler controller SHA-256: `e2a3d181f04d08c428ce68c143936f48e1f606bb25bb1083cb738fe57ed03a4b`.
- An earlier controller attempt failed before any WSL/compiler process started due to a Windows-path resolver mistake; its preserved setup record is under `../cuda_l0_source_compile_20261004T202000Z/preflight_failure.json`. It is not a candidate compile result.
