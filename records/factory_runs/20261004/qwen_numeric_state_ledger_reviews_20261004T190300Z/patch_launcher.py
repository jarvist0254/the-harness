from pathlib import Path
import re
p=Path(r'E:\the_harness\records\factory_runs\20261004\qwen_numeric_state_ledger_reviews_20261004T190300Z\launch_gemini_review.ps1')
s=p.read_text(encoding='utf-8-sig')
repls={
"'gemini_prompt_compact.txt'":"'gemini_prompt.txt'",
"'inputs_compact.json'":"'inputs.json'",
'9DD1DED681BC25F639AF50DDD06F31E72983DC2F0ED0B5856F3492C5742574A8':'29EE001AB9446917FD24C213DDD88819C79F952371E661ED517EBF71A228B793',
'0E5292D39A9D9AFB0D8787904F51D3815C3723694E44F4AB964D8E6BD6E0F564':'6DFB6A72A1310D23CF435C73F32DCD0B6A57B85CEF774C9A47C8748CE3E68DC1',
"'ROOT_GEMINI_REVIEW_ADMISSION_COMPACT.json'":"'ROOT_GEMINI_REVIEW_ADMISSION.json'",
"'gemini_launch_attempt2.json'":"'gemini_launch.json'",
"'gemini_progress_attempt2.jsonl'":"'gemini_progress.jsonl'",
"'gemini_stdout_attempt2.json'":"'gemini_stdout.json'",
"'gemini_stderr_attempt2.txt'":"'gemini_stderr.txt'",
"'gemini_review_attempt2.pending_root_qa.json'":"'gemini_review.pending_root_qa.json'",
"'gemini_terminal_attempt2.json'":"'gemini_terminal.json'",
}
for a,b in repls.items(): s=s.replace(a,b)
pat=r"        \$answer = \$outer\.response\r?\n        if \(\$answer -isnot \[string\]\) \{ \$answer = \$answer \| ConvertTo-Json -Depth 40 \}\r?\n        \$review = \$answer \| ConvertFrom-Json"
new="        if ($null -ne $outer.structured_output) { $review = $outer.structured_output } else { $answer = $outer.response; if ($answer -isnot [string]) { $answer = $answer | ConvertTo-Json -Depth 40 }; $review = $answer | ConvertFrom-Json }"
s2,n=re.subn(pat,new,s)
if n!=1: raise SystemExit(f'response parse span count {n}')
p.write_text(s2,encoding='utf-8')
print('written',len(s2))
