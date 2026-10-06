# First Qwen command — preparation only

No provider call has been launched. ROOT must independently author the absolute admission JSON binding batch/job/model/source/prompt before this command is used. Do not construct self-admission from a provider response.

```powershell
pwsh -NoProfile -File 'E:\the_harness\records\factory_runs\20261004\compiler_completion_repair_20261004T173321Z\invoke_owned_adapter.ps1' -Lane Qwen -Job qwen_compiler_completion -AdmissionPath '<ROOT-authored absolute admission JSON>' -SourcePath 'E:\the_harness\records\factory_runs\20261004\compiler_completion_repair_20261004T173321Z\supervisor_snapshot.py' -SourceSha256 fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3 -PromptPath 'E:\the_harness\records\factory_runs\20261004\compiler_completion_repair_20261004T173321Z\qwen_compiler_completion.prompt.txt'
```

Expected complete artifact is `qwen_compiler_completion/adapter.pending_root_qa.json`. Intake checks exact source-string/explanation schema only and never imports/evaluates Python. HTTP240/outer270 seconds, response/stream2MiB, maxcompletion8192 and thinkingfalse remain unchanged. A completion-limit response is rejected, not repaired into a fake complete source. Actual usage and cost are unknown before launch.

Muse native CLI route and safe flags remain NOT_CHECKED by this manager while the separate owner inspects them. Muse/Gemini/Grok prompts and admissions will be built only from actual preceding artifacts, not placeholders. They cannot run candidate sources or substitute test stubs for actual verification. The original natural-drain supervisor and failed attempt remain unchanged.
