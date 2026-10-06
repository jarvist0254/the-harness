# Peer-copy CPU fake static ABI gate

This gate admits only local CPU execution of `peer_copy_cpu_fake`, a synthetic executable linked from the candidate object and `fake_level_zero.o`. It does not admit the real Level Zero loader, a GPU API call, or a hardware claim.

Inputs are pinned in `compile_receipt.json` and `stub_build_20261004T215946Z/receipt.json`: candidate source `6185dcf242e4c847544c07455468119d67fae35d5aaf341ebaa8d14a0b920aa6`, candidate object `6a186a6893f550741c7a4dea208d9b95bcf412c9dacf333034b44203aa5177d4`, fake stub source `bfff2acc383607b74fbca4e288f0dfff3ac99d3297f3f9947cca867b5c92353f`, official Level Zero header `c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de`, GCC `/usr/bin/c++` 13.3.0 `1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769`.

Both the app object and fake API definitions were compiled against that same official `ze_api.h`. The candidate directly references 24 `ze*` entry points; `fake_level_zero.cpp` defines those same symbols with declarations matching the included header. C++ compilation and static link succeeded. `readelf -d` on the generated test executable lists only `libstdc++.so.6`, `libgcc_s.so.1`, and `libc.so.6`; it does not list `libze_loader` or a vendor runtime. Thus the executable cannot resolve these calls through the installed Level Zero loader.

The fake runtime supplies two synthetic Intel-tagged handles and CPU `malloc` storage only. It returns `ZE_RESULT_NOT_READY` (header value 1) for the selected first fence wait in timeout mode and retains an explicit `pending` flag until a successful wait. The teardown hooks report every destroy/free while pending. This is a control-flow probe: it does not model a real device queue or prove a real allocation remains active asynchronously.

The bounded cases are: successful uniform fill→copy→readback and full comparison; one-word injected corruption; both directed peer queries unavailable and no allocation/context; fence timeout with event evidence for teardown-before-completion; a cleanup `zeMemFree` error; invalid UUID CLI; and observation of a surplus CLI argument. Each executable invocation uses WSL `timeout` plus a retained Windows process handle. This admission is restricted to these CPU-only scenarios.

## Source finding before synthetic run

The timeout branch is a real candidate safety concern: `zeFenceHostSynchronize` can return `ZE_RESULT_NOT_READY`; the caller passes that result to `emit_fail`, which immediately calls `destroy_tracker`. `destroy_tracker` destroys fences, lists, queues, allocations, and context without a completion retry/drain. The CPU fake can demonstrate that this code path invokes teardown while its synthetic queue is pending. It cannot determine how an actual driver handles those releases, so this remains a driver-safety gap rather than a measured hardware result.

The CLI parser consumes the first two non-injection strings as UUIDs and ignores additional arguments. The surplus-argument case is deliberately recorded as an observation, not treated as hardware correctness.
