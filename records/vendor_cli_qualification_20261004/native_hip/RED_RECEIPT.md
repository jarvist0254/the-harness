# Initial acceptance failure

Before source implementation, `python -B verify_fixture.py` exited 1 with `AssertionError: Native HIP fixture executable is not implemented yet`.

The first implemented hipcc compilation then failed before executable creation: HIP's Clang math wrappers conflict with MSVC 14.51 `cmath` host/device overload declarations. Exact command and errors are retained in `compile.json` and `compile.stderr.log`. No HIP kernel or corruption test was run after this failed compilation. Runtime status: NOT_CHECKED.

Follow-up supersedes that initial runtime status: separate device-only exact-gfx1036 compilation using RTC headers succeeded. The VS18 host module launcher needed explicit __HIP_PLATFORM_AMD__; initial omitted-macro failure is preserved and revision2 compiled. verify_fixture.py passed default zero-error parity and corruption exit1 with one mismatch/error1. See runs.json. Only this one affine fixture is qualified.
