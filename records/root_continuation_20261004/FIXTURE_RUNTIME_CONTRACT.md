# Source-only fixture runtime helper

`fixture_runtime.py` is prepared for ROOT review. It has not been imported, parsed by Python, executed, or admitted for a native run. It does not classify numerical output as PASS/FAIL, apply source changes, rebuild libraries or retry a failed workload.

The runner accepts one absolute `--admission` JSON path under `records/root_continuation_20261004` and required `--admission-sha256` supplied externally by ROOT. The hash is checked before JSON reading and again in the post-process input-pin checks. Revision 1 is preserved as `fixture_runtime_revision1.py`, SHA256 `40146a9a10f575aaaa2f024203e6891a22a5b5a75681443ff78606697f5662a6`. The exact object keys are:

- `schema`: integer 1; `adjudicator`: ROOT; `launch`: boolean true.
- `fixture`: operator or model. Immutable executable/source hashes are embedded in the runner. Operator deadline is exactly 30 seconds; model deadline exactly 60 seconds.
- `helper`, `python`, `source`, `executable`, `system_loader`: objects with exactly `{path, sha256, bytes}`. SHA256 is lowercase hexadecimal; bytes a positive integer. Helper pins this actual file, Python pins `sys.executable`. Source/executable hashes must equal the embedded unchanged fixture pins.
- `dlls`: five objects of that same pin shape. Exact names are ggml-base.dll, ggml-cpu.dll, ggml-rpc.dll, ggml-vulkan.dll and ggml.dll; all five source paths must share one ROOT-selected fresh build folder. ROOT separately verifies ABI/source provenance. All copies and origins are hashed before/after.
- `supporting_dlls`: an empty list for operator; exactly one same-pin-shape object named llama.dll for model. ROOT binds the old same-commit llama.dll explicitly. It is copied, pinned before/after and required to be observed at the exact runtime path/hash. Unlisted llama/ggml module fallback is refused. This preparation did not invoke dumpbin or independently verify executable imports.
- `model`: null for operator; for model, the F32-derived GGUF pin with SHA256 `bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80`, bytes 2390150816. ROOT must independently match model argument to this path.
- `runtime_dir`: absolute, new direct descendant somewhere inside the root-continuation phase; its parent must already exist. Existing runtime folders are refused.
- `arguments`: exact ROOT-reviewed argv list excluding executable. No shell, discovery or automatic fallback. ROOT must preserve the expected fixture options and numerical gates.
- `timeout_seconds`: exact fixture bound; `stream_limit_bytes`: exactly 2097152 per stream.
- `child_flags`: exactly the four GGML_VK_DISABLE_F16/FUSION/COOPMAT/COOPMAT2 values `1`. Only these environment modifications occur in the child.
- `parent_runtime_environment`: exact current `relevant_environment()` mapping, including present GGML_VK_* names and explicit Vulkan/backend loader variables. Missing versus null must match; no global environment mutation.

The system loader path is exactly C:\Windows\System32\vulkan-1.dll. Other pinned artifacts live within E:\the_harness, except the pinned existing Python executable. The admission is a trusted local ROOT artifact, not cryptographic authorization.

The owned Popen handle is retained for process kill, wait, module enumeration and module-path lookup. No PID reattachment occurs. Concurrent readers cap each stream at 2 MiB and report overflow/error as integrity failure. Five actual local ggml DLL paths/hashes and the model's supporting llama.dll must be observed while the child lives; an observed Vulkan loader must match its pin. Startup/exit module-query races do not fabricate observations. If sampling misses modules, integrity is refused/unknown. The single shared pipe-drain budget is five seconds. Python and external admission pins are included in before/after receipts.

Raw stdout/stderr, input/copy hash checks, loaded-module observations, exit/reap state, parent-environment equality and full-JSON parse status are preserved. A recorded child exit zero or parsed JSON is not inference acceptance. ROOT must independently adjudicate raw numerical results. The generic helper does not provide arbitrary descendant containment or authenticated capture provenance.

Preparation changes only the helper and this contract. ROOT separately admits each exact run after source review, DLL ABI review and admission pins. No runtime folder, native process or GPU workload has been created by this preparation.
