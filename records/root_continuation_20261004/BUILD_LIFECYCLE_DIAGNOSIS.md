# FP32 candidate build: lifecycle investigation

The isolated FP32 staging candidate has not been qualified on the GPU. Three contained compiler attempts preserve their original results. No failed admission or result has been changed into a pass.

| Attempt | Change | Actual result |
| --- | --- | --- |
| 1 | Original isolated commands; configure deadline 60 seconds | Configure supervisor TIMEOUT, command exit 0, final Job active count 0 after cleanup; build not started. CMake detected an empty host architecture because the restricted child environment omitted PROCESSOR_ARCHITECTURE. |
| 2 | Child-local PROCESSOR_ARCHITECTURE=AMD64, fresh build_attempt2; configure deadline 120 seconds | Correct AMD64/x86/AVX2 configuration generated, but configure supervisor TIMEOUT; command exit 0 and cleanup recorded. Build not started. |
| 3 | Child-local VSCMD_SKIP_SENDTELEMETRY=1 before vcvars, same correct build_attempt2 | Configure completed in 7.359 seconds. Build wrote all five DLLs and logged all 357 Ninja steps, including both final links. The root command exited 0, while the supervisor remained active until its 600-second TIMEOUT. Final Job active count 0 and CLEANUP were recorded. Controller exited 1 and generated no fresh DLL manifest. No GPU run. |

ROOT read the installed Visual Studio VsDevCmd.bat lines 249–257. It starts background PowerShell telemetry when VSCMD_SKIP_SENDTELEMETRY is empty. Its SHA256 was a7815e85d636828e5cf70fe4235b11fcb41750896a4d2d60756b43bacaf4f0b2. Suppressing that child launch was consistent with the configure drain succeeding; the cached configuration also differed, so this is not a controlled proof that telemetry was its sole cause. No Visual Studio file or global environment was modified.

The build's root command PID 81552 was observed absent while the controller still reported RUNNING. The original Ninja log placed the final links around 77 seconds. The root command's absence and successful link log do not identify which descendant remained in the Job. Generated MSVC compile rules include /FS. Microsoft documents its use of MSPDBSRV for serialized PDB writes; MSPDBSRV remains a hypothesis until an owned-Job member trace observes it.

Attempt-3 evidence: [outer receipt and copied controller evidence](fp32_derived_build_plan_20261004T155932Z/outer_compile_attempt3_20261004T1703Z/outer_receipt.json). Receipt SHA256 ce909fd8a3585eedede6a57007981b40016cf5f815f3e4c685df7ea06babec6d. Earlier attempts and all source/admission hashes remain preserved. This compiler result does not validate the candidate's numerical behavior, ABI, real model parity, four cards or direct peer DMA.

A fresh diagnostic attempt is being prepared to observe Job members through the owned Job handle, with bounded read-only image queries. It must preserve the completion and cleanup policy. No further unchanged deadline retry is planned.

Primary documentation read on 2026-10-04: [QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject), [Job process ID list](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list), and [MSVC /FS](https://learn.microsoft.com/en-us/cpp/build/reference/fs-force-synchronous-pdb-writes?view=msvc-170).
