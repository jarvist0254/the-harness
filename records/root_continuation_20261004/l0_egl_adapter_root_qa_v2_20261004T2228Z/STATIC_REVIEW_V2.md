# Pure adapter QA packet, revision 2

This folder is a separate revision. The first packet at `l0_egl_adapter_root_qa_20261004T2214Z` remains unchanged.

The independent suite keeps success-order evidence separate from end-to-end readiness. Its ordering control checks only that producer completion wait precedes the host signal, direct transport is not qualified, and the default export path does not reach EGL import. The descriptor negative control still requires a usable nonnegative sync-file FD and requires malformed/missing export to stop before the EGL callback. It does not make a fabricated descriptor valid to satisfy a positive baseline.

The runner invokes the isolated Python child as `python.exe -I -B <independent_tests>`. `-B` explicitly suppresses bytecode output despite isolated mode ignoring `PYTHONDONTWRITEBYTECODE`. The runner records EOF per pipe, reader-thread completion, and reader exceptions. It reports `PURE_QA_PASSED` only when the retained child exited with code 0, both readers reached EOF and joined without error, and there was no timeout or stream overflow. Otherwise it records failure or incomplete capture.

The source and provider-test files remain hash-pinned provenance inputs; the provider tests are not executed. Candidate import occurs only in the separately admitted child. The controller has a 20-second child deadline, five-second process wait, and up to five seconds per stream-reader join. Root should account for that outer bound when granting any pure-QA admission.

Current state: static preparation only; no candidate import, provider test, or GPU/native call has occurred.
