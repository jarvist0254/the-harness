# D3D12 cross-adapter smoke receipt — 2026-10-04

The immutable provider artifact remains unchanged: `records/factory_runs/20261004/d3d12_pro_nonthinking_20261004T101008434Z/d3d12_crossadapter_buffer.cpp`.

Before editing the copied candidate, provider SHA-256 was `51F76B108904F9498BF3A4B633FC7EBBAD83128B29C05356B4F13472C240ADAA`; its byte-identical copy was verified. Final candidate SHA-256: `D487428BDEBF9028B323739FC60AD3F3905B1B74E3D2E1FF7DB0834D473EF281`. Candidate: `j_link/d3d12_smoke.cpp`.

The bounded copy edits require actual hardware adapters with vendor IDs NVIDIA `0x10DE` and AMD `0x1002`; retain the first mismatch while comparing all 262144 bytes; compare injected corruption against the original pattern; report `SPEC_REQUIRED_L0_SYSTEM_MEMORY_NOT_RESIDENCY_MEASURED`; and emit requested heap flags/properties plus returned heap properties when resource creation succeeds. The failure path reports decimal and hexadecimal HRESULT and exits nonzero. No API algorithm or synchronization sequence was changed.

## Build

Visual Studio 18 Community Developer Command Prompt 18.6.2, x64; `WindowsSDKVersion=10.0.26100.0`. `d3d12.lib` and `dxgi.lib` linked successfully to `d3d12_smoke.exe`.

- Final compile/link process PID 80180, exit 0, under 180 seconds.
- Exact wrapper: `compile_candidate.cmd`.
- Captured output: `candidate_compile.stdout.log`, `candidate_compile.stderr.log`.

## Runtime

Both runs used CREATE_NO_WINDOW, separate stdout/stderr logs, and a 60-second process bound. They selected these actual vendor-ID/LUID pairs (no WARP): NVIDIA `0x10DE`, LUID `0x00000005b22912d7`; AMD `0x1002`, LUID `0x000000000001a52e`.

- Default: PID 75248, exit 1. JSON status `FAIL`; `CreateCommittedResource SHARED|SHARED_CROSS_ADAPTER` returned `0x80070057` (`E_INVALIDARG`).
- `--inject-corruption`: PID 47300, exit 1, same resource-creation HRESULT before the copy/readback/compare path.

Requested heap type was DEFAULT; requested CPU page and pool preference were UNKNOWN; requested flags were decimal 33 (`SHARED|SHARED_CROSS_ADAPTER`). Classification is `SPEC_REQUIRED_L0_SYSTEM_MEMORY_NOT_RESIDENCY_MEASURED`; this is not a physical residency measurement. The resource was not created, so returned heap properties, bytes compared, and parity are `NOT_CHECKED`. The corruption negative control was not reached. No retry, driver change, P2P claim, or dedicated-VRAM-pool claim was made.

Runtime stdout/stderr: `default.stdout.log`, `default.stderr.log`, `inject_corruption.stdout.log`, `inject_corruption.stderr.log`. The original provider compile/link logs and wrappers are retained separately as `compile.stdout.log`, `compile.stderr.log`, `compile_provider.cmd`, `link.stdout.log`, `link.stderr.log`, `link_provider.cmd`.
