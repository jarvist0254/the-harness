# MSVC auxiliary-process research

Date: 2026-10-04. This is source/documentation research plus inspection of one preserved build attempt. No compiler rerun, source edit, telemetry setting change, process termination, install, or GPU operation was performed for this note.

## Findings

Microsoft documents that `/FS` serializes PDB writes through `MSPDBSRV.EXE`, and that `/MP` enables `/FS` by default. The local generated Ninja file has `/MP` in 158 rules and no literal `/FS`, `/Zi`, or `/ZI`; the project’s `ggml-vulkan/CMakeLists.txt` adds `/MP`. The local Release cache uses `/O2 /Ob2 /DNDEBUG`. Thus MSPDBSRV involvement is plausible from the documented `/MP` default, while a PDB-writing cause is not established because the inspected Release flags do not show `/Zi` or `/ZI`.

The local attempt-3 supervisor result is `TIMEOUT` with `failure_reason=deadline`, despite its captured build stdout reaching `[357/357] Linking CXX shared library bin\ggml-vulkan.dll` and `[357/357] Linking CXX shared library bin\ggml.dll`. The worker record reports exit code 0, but the controller rejected the stage result/cleanup, so this is not a successful build receipt. At the root’s earlier point observation, `vctip.exe` and `mspdbsrv.exe` were still present after compiler work; at my later exact process check, neither was present. This bounded observation does not prove which child held a job or pipe open, or that either process caused the timeout.

The contained build supervisor waits for the root command and job active-process count, then waits for stdout/stderr reader threads to reach EOF before it can report `PROCESS_COMPLETED`; on deadline it records `TIMEOUT` and runs job cleanup. A descendant retaining inherited pipe handles or remaining in the job could therefore explain why a complete-looking build transcript does not yield a completed supervisor status. This remains a hypothesis, not a diagnosed cause.

Microsoft-owned BuildXL source calls `VCTIP.EXE` the VC++ Technology Improvement Program telemetry uploader and classifies its breakaway setting as unsafe: an escaped child is unobserved and may survive its parent. That evidence argues against treating breakaway or a blind process kill as a safe containment repair. `VSCMD_SKIP_SENDTELEMETRY=1` was already applied to the child build environment; the observed build still timed out. No documented, safe child-only VCTIP suppression switch was found in this bounded search. Do not infer that no such switch exists.

CMake’s `CMAKE_USER_MAKE_RULES_OVERRIDE` is documented as a last resort, loaded after the built-in compiler/platform modules but before their information is consumed, and it affects `try_compile()`/`try_run()` too. CMake’s current Windows-MSVC language modules add `/FS` for MSVC 18+, while this build’s generated Ninja rules do not contain literal `/FS`. Any future rule experiment needs to inspect the exact generated command lines rather than assume an override will remove a flag or solve this timeout.

## Source-backed next diagnostic, not executed

If root chooses to continue, the least-confounded build-only diagnostic is a fresh disposable generated build tree with the same pinned sources, toolchain, Release optimization/defines, target, and containment, changing only whether `/MP` is emitted (and therefore its documented implicit `/FS` behavior). Keep it inside the harness records tree, preserve the old attempt, compare actual generated command lines and the supervisor’s separate process/job/pipe-drain status. This would test the `/MP`/PDB path; it would not prove or suppress VCTIP specifically. A separate VCTIP hypothesis requires an official, documented child-only control or instrumentation of the exact process tree, not breakaway or arbitrary termination. No new attempt is authorized by this note.

## Evidence locations and pins

- Attempt-3 supervisor evidence: `records/root_continuation_20261004/fp32_derived_build_plan_20261004T155932Z/outer_compile_attempt3_20261004T1703Z/controller_evidence/`
- Build stdout: `build.stdout.log` (34,757 bytes); stderr empty.
- Raw stage status: `build_result_copy.json` (`TIMEOUT`, deadline; worker PID 81552, exit 0, job active count 0, drain proof `CLEANUP`). The controller’s final result is `controller_result.json`; it rejects the stage as incomplete. These distinct statuses must remain distinct.
- Preserved compile target: `ggml` and `ggml-vulkan`, `--parallel 4`; no GPU execution was part of this attempt.
- This note makes no claim of a successful Vulkan build, a live VCTIP/MSPDB process, or a root cause.

## Primary sources

- Microsoft Learn, [`/FS (Force Synchronous PDB Writes)`](https://learn.microsoft.com/en-us/cpp/build/reference/fs-force-synchronous-pdb-writes?view=msvc-170): `/FS` routes PDB writes through MSPDBSRV; `/MP` enables `/FS` by default.
- Microsoft BuildXL, [`visualCpp.dsc`](https://github.com/microsoft/BuildXL/blob/main/Public/Sdk/Experimental/Msvc/VisualCpp/visualCpp.dsc): identifies VCTIP as the telemetry uploader and documents its use as a breakaway process.
- Microsoft BuildXL, [process breakaway safety](https://github.com/microsoft/BuildXL/blob/main/Documentation/Wiki/Advanced-Features/Process-breakaway.md): explains that breakaway processes become unobserved and can outlive the containing build.
- CMake, [`CMAKE_USER_MAKE_RULES_OVERRIDE`](https://cmake.org/cmake/help/latest/variable/CMAKE_USER_MAKE_RULES_OVERRIDE.html): last-resort compiler/platform information override and scope across try-compile/run.
- CMake upstream, [Windows-MSVC-C.cmake](https://github.com/Kitware/CMake/blob/master/Modules/Platform/Windows-MSVC-C.cmake) and [Windows-MSVC-CXX.cmake](https://github.com/Kitware/CMake/blob/master/Modules/Platform/Windows-MSVC-CXX.cmake): the MSVC platform modules that set the language-specific `/FS` rule variable.
