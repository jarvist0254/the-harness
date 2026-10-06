# Sixth scoped provider batch

Qwen3.8-Max generated the targeted FP32 staging patch, Gemini3.8-Flash-Medium reviewed the exact patch, and Grok4.7-Build-Fast simplified region three and corrected the rationale. Patches remain unapplied and pending ROOT quality admission. No candidate tests, compiler or GPU execution occurred in this batch.

Three paid jobs reported 89,186 tokens: Qwen 11,992; Gemini 54,292; Grok 22,902. Grok reported one internal model call; other internal call counts are not reported. Native child agents: zero. The original oversized Gemini command failed locally before child/provider launch and is excluded.

The five immutable prior batches plus this batch contain 50 jobs, 2,604,386 observed tokens and two jobs with unknown usage. Qwen: 21 jobs / 394,235 observed + one unknown; Gemini: 12 / 1,377,614; Grok: 17 / 832,537 + one unknown. Tokens are not ModelStudio Credits or per-job billing evidence.

See USAGE_FINAL_SIXTH.json, CLOSED_RECEIPT.json, GROK_TEXT_MATCH_GATE.json, GROK_TEXT_MATCH_LF_SUPPLEMENT.json and SECRET_PROCESS_AUDIT_SIXTH.json. Literal multiline match counts preserve source CRLF versus JSON LF; LF-normalized data-only comparisons each match once. No source replacement was performed.

The audit checked three configured secret strings in memory: zero matches, no credential-named files and all owned wrapper/worker PIDs absent. It does not claim coverage of unknown secrets or external logs. ROOT adjudication must be recorded separately; previous receipts remain immutable. The full four-card/model qualification goal remains open.
