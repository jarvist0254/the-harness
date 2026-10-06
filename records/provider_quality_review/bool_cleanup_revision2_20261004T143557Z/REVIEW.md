# Revision 2 independent mock gate

Revision 2 exact SHA `3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c` passes all 44 controls. The same tests on previous revision SHA `4d8272aa5dbc330e4199b216bd9b3fd3d240c2c8d1c59e223e37d249c936f663` fail 4 cases, confirming discrimination of the new shutdown behavior. Zero errors and zero forbidden native/process calls in both runs. Exact source hashes checked before and after.

Four new direct tests use signaled wait 0, running wait 258, raised/invalid pre-wait, and job BOOL integer zero. Signaled root skips redundant termination and preserves exit code 3; uncertain pre-wait remains UNKNOWN_DRAIN despite best-effort termination and later successful wait; job BOOL zero remains uncertain even after root exit.

No implementation edits, promotion, native fixtures, worker processes, or GPUs were performed. This is mock-only qualification; root retains native admission.
