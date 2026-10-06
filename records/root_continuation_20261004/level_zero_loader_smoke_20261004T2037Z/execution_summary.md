# Level Zero loader bootstrap smoke

## Outcome

This one-shot bootstrap smoke did **not** reach driver enumeration. The exact pinned `ze_loader.dll` loaded from `E:\the_harness\records\toolchains\level_zero_20261004\runtime_source\build\bin\ze_loader.dll`; `zeInit(GPU_ONLY=1)` returned `2013265921` (`0x78000001`), which the pinned `ze_api.h` names `ZE_RESULT_ERROR_UNINITIALIZED`. The driver-count call was skipped because initialization was not successful. No driver count, driver/device identity, or Intel presence/absence was observed.

The worker status is `INITIALIZATION_ERROR`. It records `vendor_qualification=NOT_PERFORMED` and `p2p_claim=UNPROVEN`. The enum name is from the pinned header; no root cause for the returned code is inferred.

## ABI and containment

Header source: `records/toolchains/level_zero_20261004/sdk/include/level_zero/ze_api.h`, SHA-256 `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de`. It declares `ZE_APICALL` as `__cdecl`, `ZE_INIT_FLAG_GPU_ONLY=ZE_BIT(0)` (1), `zeInit(ze_init_flags_t) -> ze_result_t`, and count-only `zeDriverGet(uint32_t *, ze_driver_handle_t *)` with a nullable optional second parameter. The ctypes worker uses `CDLL` for cdecl and would call `zeDriverGet(&count, NULL)` only after init success.

The loader’s expected and observed SHA-256 is `0838c395a7393c313fdfeff8cea5d08a71ba044dc28f793aa4f7d28f60095162` before and after; the loaded full path matches the pinned path. Source/header/interpreter/supervisor hashes were unchanged before/after. The worker called only `zeInit`; it did not create a device context, allocate memory, create a queue/list, or transfer data.

The trusted supervisor run records worker PID `95692`, exit `1`, `job_active_count=0`, and `drain_proof=CLEANUP`. It reported status `FAILED` / reason `nonzero_exit` because the worker honestly exited 1 after the initialization error. The job cleanup proof is still `CLEANUP`; the worker and controller PIDs were absent after wait; the restart receipt matched. `whole_tree_certificate` is false. The outer controller exited `0` in 0.188 seconds and did not time out.

## Evidence paths

- Outer receipt: `runs/run_20261004T204514Z/outer_receipt.json`.
- Outer controller stdout/stderr: `runs/run_20261004T204514Z/controller.stdout.bin` and `controller.stderr.bin`.
- Supervisor receipt/journal: `supervisor_output/levelzero_loader_smoke_receipt.json` and `supervisor_output/levelzero_loader_smoke.journal`.
- Exact worker JSON and stderr: `supervisor_output/levelzero_probe.stdout.log` and `supervisor_output/levelzero_probe.stderr.log`.
- Root admission: `ROOT_ADMISSION.json`.

No driver installation, PATH/environment mutation, service/session termination, provider call, or second attempt was performed.
