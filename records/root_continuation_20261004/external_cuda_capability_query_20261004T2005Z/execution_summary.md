# CUDA driver capability inventory — execution receipt

This is a CUDA Driver API attribute inventory, not a memory-sharing or P2P experiment. The binary called `cuInit`, then queried device count, identity, and the listed attributes. It did not create a CUDA context, allocate GPU memory, create an export handle, transfer data, or launch a kernel. Every result labels P2P `UNPROVEN`.

Root explicitly admitted compilation and one subsequent inventory query, conditional on compile exit 0 and unchanged source/header/library pins. The per-phase admission receipts are `ROOT_COMPILE_ADMISSION.json` and `ROOT_QUERY_ADMISSION.json`.

## Build and provenance

- Source SHA-256: `d22e00d620d17edf1d6ab0271c977e02b480a92bc75074e41df77a263bc8c9f2`.
- Controller SHA-256: `9bd42551d8d231200edc2aadf3b264698c2f3b31c30be4c176de39ffafd5bbb6`.
- CUDA headers: `cuda.h` `7a79d67ca888061b1dfbe4739b51ad64f85a2f3ad874947ce09b2c635b4c7072`; `cudaTypedefs.h` `77eb4072ae5da75bec31c4cf6291967e8ecbd6981ece0d47b07dbbabf781782c`.
- CUDA Driver library `/usr/lib/wsl/lib/libcuda.so.1`: `00d5773a96ab7e18d087880b8ce02741863da15c487b434999f7932f3cbe1383` before and after.
- Compiler `/usr/bin/c++`: c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, SHA-256 `1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769` before and after.
- Binary SHA-256: `51e3bc833f97dd8de57dac17ad7ba7c03abe71ba0b2645c715a520ce7d4a7ec4`.
- Exact argument vectors are in `command_plan.json`; both used `wsl.exe --exec` without a shell.
- `c++` compile exit 0 in 1.219 seconds; stdout/stderr were empty. WSL client PID 51884 exited and was reaped.
- Query process exit 1 in 0.39 seconds; stdout is the raw JSON at `E:\the_harness\records\root_continuation_20261004\external_cuda_capability_query_20261004T2005Z\runs\query_20261004T202756Z\03_query.stdout.bin` and stderr is empty. WSL client PID 34988 exited and was reaped. Worker timeout bounds were 85s+5s kill grace for compile and 30s+5s kill grace for query; neither timed out.
- Source, headers, compiler, runtime library, and query executable hashes matched before/after checks. Full raw hash commands, stdout/stderr, per-process PIDs, return codes, and elapsed times are retained in the two `runs` directories.

## Raw query interpretation

CUDA Driver reported version `13010` and one device: `NVIDIA GeForce RTX 5070 Ti`, UUID `ba8e88c40d93ed2d3c78901e812e103c`. Its attribute results were:

- `DMA_BUF_SUPPORTED`: API result `0`, value `0`.
- `HOST_ALLOC_DMA_BUF_SUPPORTED`: API result `0`, value `0`.
- `DMA_BUF_MMAP_SUPPORTED`: API result `1`, value field `0`. The API returned numeric code `1` for this query.
- `GPU_DIRECT_RDMA_SUPPORTED`: API result `0`, value `0`.
- `GPU_DIRECT_RDMA_WITH_CUDA_VMM_SUPPORTED`: API result `0`, value `0`.

The source therefore reported `QUERY_ERROR` and exited 1 because one attribute query returned code 1; the other listed attributes returned code 0 with value 0. The controller recorded this raw query outcome successfully. No further interpretation of code 1 is asserted here. CUDA enumeration only reported an NVIDIA device; this query does not speak to AMD visibility or cross-vendor import.

