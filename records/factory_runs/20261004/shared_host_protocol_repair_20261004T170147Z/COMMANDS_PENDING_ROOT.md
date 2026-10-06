# Prepared commands — do not run without ROOT binding

No provider job has launched. The first command is exact except for ROOT's independently authored admission receipt path. It reads credentials only inside the admitted child at launch. Do not create a self-admission.

```powershell
pwsh -NoProfile -File 'E:\the_harness\records\factory_runs\20261004\shared_host_protocol_repair_20261004T170147Z\invoke_owned_protocol.ps1' -Lane Qwen -Job qwen_shared_host_protocol -AdmissionPath '<ROOT-authored absolute admission JSON>' -SourcePath 'E:\the_harness\records\factory_runs\20261004\shared_host_protocol_repair_20261004T170147Z\source_snapshot.cpp' -SourceSha256 21a0379e778bdb8c31e5da7774410b59236e2b6f72a87eaf1b68ff584a666815 -PromptPath 'E:\the_harness\records\factory_runs\20261004\shared_host_protocol_repair_20261004T170147Z\qwen_shared_host_protocol.prompt.txt'
```

Expected artifact is `qwen_shared_host_protocol/protocol.pending_root_qa.json`, subject to actual complete response, strict schema and search matches. REFUSED is an honest protocol outcome, not a helper failure or fake patch. HTTP/auth/timeout/partial/schema failures retain their raw terminal state and usage if reported.

After actual Qwen completion, build a fresh compact Gemini prompt and bind its actual artifact/source hashes in a new ROOT receipt. Use the same wrapper with `-Lane Gemini -Job gemini_shared_host_review`, actual source artifact as SourcePath and its SHA256; final PromptPath is `gemini_shared_host_review.prompt.txt`. That file does not yet exist. It must contain sufficient actual source and review context under 24000 UTF16 characters; no named unreadable file or live-tree access is a substitute. Gemini returns review JSON, not execution approval.

After actual Gemini completion and ROOT adjudication, build the Grok prompt file and use `-Lane Grok -Job grok_shared_host_edit`, with actual Qwen artifact source pin and a fresh ROOT receipt. Final PromptPath is `grok_shared_host_edit.prompt.txt`; it does not yet exist. Grok may preserve a justified refusal. Do not force a paid cosmetic edit if no meaningful finding remains.

Models are fixed in the wrapper: qwen3.8-max, gemini-3.8-flash-medium and grok-4.7-build-fast. Timeouts are240/270 HTTP/outer for Qwen,210/240 provider/outer for Gemini and300 outer for Grok; caps2MiB. Tokens/Credits/billing are unknown before actual work. No native child agents, candidate execution, source application, compilation or GPU work is authorized by these commands or this preparation.
