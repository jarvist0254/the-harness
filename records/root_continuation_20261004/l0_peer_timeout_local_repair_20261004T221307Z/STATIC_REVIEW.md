# Local finite-wait peer-copy apparatus gate

Original source6185dcf2 and fakebfff2acc are immutable. Nine independent raw-receipt controls measured4PASS/5FAIL before implementation: wrong fenceAPI label, seven pending teardown calls, absent quarantine/no-cleanup semantics, surplus acceptance and58API calls for surplus input. Original raw receipts remain under stub_runs_20261004T220255Z.

The derivative adds only stdlib cstdlib, a tracked unconfirmed submission flag, strict surplus/duplicate flag rejection, explicit execution-vs-fence error attribution and terminal quarantine. Before submission the flag becomes true; only successful finite10second fence completion clears it. Any failed execution or failed fence conservatively ends the disposable process with FAIL1, no LevelZero teardown. It emits resource_state TERMINAL_QUARANTINE, destruction_skipped true, cleanup_verified false and direct_transport_qualified false, flushes streams and calls std::_Exit. No infinite wait/retry or safeGPUdestruction claim.

The official pinned ze_api.h lines7009–7020 distinguish NOT_READY timeout from successful completion. C++ draft support.start.term specifies _Exit omits automatic/static/thread destructors and atexit callbacks. References: https://oneapi-src.github.io/level-zero-spec/level-zero/latest/core/api/apis/fence.html and https://eel.is/c++draft/support.start.term . No direct quotes reproduced.

Process exit and outer-owned-process reaping contain this disposable apparatus; they do not certify GPU reclamation. No real driver/GPU run is admitted. Allocation owner checks, copyqueue selection, full65536byte/16384word comparison, exact corruptionword8192 and normal cleanup/error checks remain intact.

Official-header CPU fake uses hostmalloc only. Added call trace is independent of candidate output and survives explicit flush before _Exit; no destructor summary is required on quarantine. Cases add copy/readback/corruption-stage timeout and duplicateflag. ABI signatures unchanged; no fake enum/header guards. Both sources use only C++stdlib and officialheader; stub defines everycalled LevelZero symbol, no loader or dynamicload calls.

Object compile PASS using pinned GCC13.3/header, source284e6109, no executable linked or run yet. Stub link/import inspection and execution are PENDING_ROOT_ADMISSION. Controller uses the prior retainedWSLclient/innerGNUtimeout bounded pattern (5s+3s kill grace,12souter,128KiB streams) with explicit limitation: Windows client reaping alone does not certify a WSLprocess tree. CPUfake launches no descendants; realGPU execution requires separate containment admission.

Execution pending; noGREENclaim or promotion. Exactdiffs/source/controller/tests/pins are in this folder.
