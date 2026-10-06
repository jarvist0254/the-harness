# Isolated F32 staging build preparation

**NONEXECUTING PREPARATION ONLY.** No source files copied, candidate applied, configure/build process launched, native supervisor imported, GPU operation performed or dependency downloaded. Scripts received AST syntax checks only, not operational tests. Actual Grok candidate and root admission pins remain pending.

Proposed isolated root: `E:\the_harness\records\build_vulkan_fp32_staging_20261004T155932Z`, with `source/`, `build/`, and `evidence/`. The original global checkout, pinned clean tree and original build are read-only inputs and are never patched. No install target or global PATH change.

## Copy and patch admission

`prepare_derived.py --admission <root-admission.json> --admission-sha256 <trusted-root-hash>` requires an exact caller-supplied admission hash and a strict root record. Its fields are candidate, candidate_sha256, derived_cpp_sha256, exact_regions, output_root, plan_sha256 and authorization=`ROOT_BUILD_PREPARATION_ADMITTED`. This is a proposed normalized handoff schema, not a claim that a provider has already supplied it. Root must normalize the actual immutable Grok candidate/patch and bind this plan before use.

The candidate is full ggml-vulkan.cpp bytes. The helper verifies the3685-entry manifest SHA `CA13617B…34A5EC6A`, every source byte size/hash and confined unique manifest path before creating a new tree. It copies only manifest-listed files, rechecks source and copied bytes/hashes, then accepts the candidate only when exactly three line-diff regions lie inside original lines6270–6552. Exact region fields include old/new line bounds and old/new byte hashes. New lines must preserve the source EOL convention. No global replace or newline normalization is used. Every other copied file must still match the clean manifest. Failed partial work is preserved; the destination must be absent, so the helper refuses an unchanged retry.

It records copied and derived manifests, actual admission, toolchain/baseline pins and configure/build commands. Toolchain and original five DLL hashes are checked before and after preparation. Free disk must exceed twice source-byte total plus8GiB. This is a bounded preparation gate, not a guarantee of build success.

## Build command and dependency reasoning

`build_DRAFT.cmd` records exact commands but is not admitted to run. Release/Ninja with existing VS18 MSVC and official copied Vulkan SDK uses explicit include/import-library/glslc and SPIRV-Headers package paths. Existing GGML BOOL settings are retained except explicit cache/testing changes: CPU/Vulkan/RPC ON, native OFF, shared ON, backend dynamic loading OFF. Cache launcher disabled; OpenMP/LLAMAFILE/AVX/AVX2 and other pinned CPU choices retained. No-FetchContent flags and OPENMP_FETCH OFF prohibit opportunistic dependency fetching.

LLAMA app/server/tools/tests/examples/common/MTMD/UI/SSL/subprocess builds are disabled. Build targets are `ggml ggml-vulkan --parallel4`. In pinned ggml/src/CMakeLists.txt, the non-dynamic backend helper links enabled CPU/RPC/Vulkan backends publicly to ggml (381–397), each linked to ggml-base. Thus these targets should produce all five fresh runtime DLLs: ggml,ggml-base,ggml-cpu,ggml-rpc,ggml-vulkan. The target graph, not an old-file copy, must establish that they were built. Vulkan shader-generator ExternalProject still compiles many shaders; its cost may hit the600-second deadline. No internal test or CPU-result-check runtime is enabled.

## Containment controller dependency

`build_controller_DRAFT.py --runtime-admission <root-record.json> --runtime-admission-sha256 <trusted-root-hash>` requires exact root plan/controller/variant/command hashes and pure-controls/native-admission fields. The variant is Luna's pending BUILD_ONLY derivative of accepted3CB1 source, with exactly one validation-limit edit60→600. Its exact hash is pending; no native import or process launch occurred in this preparation task.

The controller runs two separately contained stages: configure60seconds and build600seconds, log limit128KiB per stream, at most4buildjobs, heartbeat15seconds. It calls the root-admitted variant using kill_on_close; that variant assigns a suspended child before resume. It requires PROCESS_COMPLETED, CLEANUP, job_active_count0, assigned/resumed root with exit0, no log overflow and an independent bounded tasklist PID-absence receipt after each stage. Any failure stops before the next stage. Existing accepted supervisor and policy files remain untouched.

A background heartbeat writes current stage/time/status to a fresh evidence file every15seconds; heartbeat durability failure requests cancellation through the admitted supervisor. Compiler descendants remain inside the variant's Job; this is a fixed compiler-workload accounting gate, not certification of arbitrary controller-loss recovery or all possible workloads. Actual44pure/boundary controls, root native admission and variant hash are required before execution. The controller received AST checks only and needs root review/testing; no prepared helper can self-admit.

The initial2MiB request was explicitly withdrawn by ROOT in favor of128KiB. The old data-only request draft is retained as `controller_request_withdrawn_2MiB.py` and must not execute. `progress.json` reports the current preparation-only state. Configure/build commands are emitted separately by the preparation helper; `build_DRAFT.cmd` is reference text only.

## ABI and future measurement gates

Capture compiler/CMake/Ninja/glslc/SDK-header/config/source/all-five-DLL hashes before/after, exact commands/caches, complete capped streams and ownership/drain receipts. Compare new DLL exported/imported symbols and architecture against original interfaces. Same commit/public headers and shared settings make loading the existing AD449 operator executable plausible, not guaranteed. Before a future run, copy by hash the exact fresh DLLs into a new runtime directory and observe actual loaded paths through the retained child handle. The old D903 model fixture may likewise load fresh ggml DLLs with its unchanged original llama DLL/other runtime dependencies, but all dependencies must be explicitly bound; this plan does not rebuild the full server or claim reproducible binaries.

Baseline RED source/executable, native assertion history and six-case failure receipts remain immutable. First test the unchanged operator against fresh libraries under separately admitted GPU supervision; fixed six-case values/tolerance/reference remain unchanged. Only after numerical baseline passes should the root consider model baseline and later reverse/corruption experiments. No four-card/P2P/VRAM-pool/production claim follows from a successful build.
