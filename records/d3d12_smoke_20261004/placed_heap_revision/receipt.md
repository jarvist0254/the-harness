# Placed-heap D3D12 smoke revision — 2026-10-04

Immutable placed-heap provider source SHA-256: `3FE59BFD39340487043ED4E217AD4738542911576FDF4B22530F4B38E1E90877`.
Provider patch JSON SHA-256: `1481BB4E76B9283A07A2AF224179E0E98C7880005DE6AF859EC00A44E868F0`. Both exact replacement hunks matched once and were applied to the staged copy. The first changes `CreateHeap` to the SDK `D3D12_HEAP_DESC` signature; the second creates the consumer placed resource from the opened shared heap.

Prior candidate SHA-256: `D487428BDEBF9028B323739FC60AD3F3905B1B74E3D2E1FF7DB0834D473EF281`; preserved as `d3d12_smoke_prior_revision.cpp`. Final candidate SHA-256: `E022677AF806BD041AC9A63C3E4F98E6E437F5A2F10A53CEB0188F2002FD2FA6`; staged copy SHA-256: `E022677AF806BD041AC9A63C3E4F98E6E437F5A2F10A53CEB0188F2002FD2FA6`. The staged candidate was copied byte-for-byte to `j_link/d3d12_smoke.cpp`.

The patch's 65536 alignment fallback was removed. The candidate calls `GetResourceAllocationInfo` on both devices, validates nonzero/valid size and alignment, requires producer and consumer results to match, and uses their returned size/alignment in `D3D12_HEAP_DESC`. HRESULT failures report `FAIL` and exit 1; missing adapter capability or allocation incompatibility reports `NOT_CHECKED` and exits 2. Adapter selection requires hardware NVIDIA `0x10DE` and AMD `0x1002` vendor IDs, with software adapters filtered out.

The runtime JSON records the required classification `SPEC_REQUIRED_L0_SYSTEM_MEMORY_NOT_RESIDENCY_MEASURED`, adapter vendor IDs/LUIDs, requested heap properties/flags, and the returned heap description. This records the API's L0 requirement and returned descriptor; it does not measure physical residency or claim P2P/dedicated-VRAM placement.

## Build

VS 18 Community Developer Command Prompt 18.6.2, x64, `WindowsSDKVersion=10.0.26100.0`; linked `d3d12.lib` and `dxgi.lib`.

- Compile/link PID 60652: exit 0.
- Command wrapper: `compile_placed_heap_revision.cmd`.
- Output logs: `compile.stdout.log`, `compile.stderr.log`.

## Runtime

Both cases ran with CREATE_NO_WINDOW, captured stdout/stderr, and a 60-second process bound. Both selected NVIDIA LUID `0x00000005b22912d7` and AMD LUID `0x000000000001a52e`.

- Default PID 12560: exit 0, JSON `PASS`, 944 ms, all 262144 bytes matched.
- `--inject-corruption` PID 33236: exit 1, JSON `FAIL`, 612 ms, all 262144 bytes inspected, first mismatch offset 12345.

Both results report requested size 262144, alignment 65536, flags 33 (`SHARED|SHARED_CROSS_ADAPTER`) and returned size 262144, alignment 65536, type 1 (`DEFAULT`), CPU page property 0 (`UNKNOWN`), memory pool preference 0 (`UNKNOWN`), flags 33. These are the returned D3D12 heap descriptor fields, not a physical residency probe.

Runtime stdout/stderr: `default.stdout.log`, `default.stderr.log`, `inject_corruption.stdout.log`, `inject_corruption.stderr.log`.
