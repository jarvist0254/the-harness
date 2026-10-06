# Isolated provider evidence

Live Factory and PyRe were not edited or started. Provider original source is experimental and is not accepted product code. Parent reviewed and modified apparatus revisions have separate compile and hardware receipts.

## Native Qwen / DeepSeek terminal batches

User authorized up to 10 child agents per terminal batch. Isolated settings specified agents.team.maxTeammates=10, maxSubagentDepth=1, and disabled managed auto-memory, auto-dream, auto-skill and team-memory. Each prompt requested three useful independent read-only teammates, with permission to use at most ten. No ten-worker execution is claimed.

Pinned actual installed CLI: C:\Users\thoma\.qwen\updates\npm\8f26e68d15de80a6\versions\0.24.7\node_modules\@qwen-code\qwen-code\cli.js. The global bootstrap normally selects this managed installation; changing QWEN_HOME caused initial attempts to fall back to global 0.22.2, which rejected --advisor. The corrected launcher pins 0.24.7 and keeps credentials only in process environment.

Both final v6 processes finished with exit 55 after approximately 255 seconds against a configured 240-second CLI wall limit and 270-second outer whole-tree deadline. Status: TEAM_CREATED_NO_CHILDREN. No accepted independent child reviews. No retries after the final batch.

| Batch | Exact model in init | PID | Team | Child members |
|---|---|---:|---|---:|
| native_qwen_teams_20261004T102800/qwen38_batch_v6 | qwen3.8-flash | 52696 | harness-review-batch-v6 | 0 |
| native_qwen_teams_20261004T102800/deepseek_batch_v6 | deepseek-v4-flash-0731 | 86952 | deepseek-v6-isolated-review | 0 |

Actual successful team_create tool events: Qwen call_647bf89ce2824be5b62f6fe8; DeepSeek call_513232a977914617b46159e4. Team config.json members arrays were empty at completion; stdout contains no agent launch event. Actual child model IDs and child PIDs are NOT_CHECKED because no child was launched. Teams use in-process workers, not necessarily independent OS processes.

Two precise CLI limitations were observed: --bare returns a hardcoded minimal tool set and hides native Agent/Team tools; --safe-mode ignores --core-tools, while explicit --exclude-tools filtered file/shell/web tools. Final init exposed native agent/team coordination along with several built-in administrative tools. No file edits, shell commands, MCP calls, scheduled jobs, worktree mutations or memory writes occurred in the final batches. Earlier bare DeepSeek attempted four reads, all denied by non-interactive plan mode; no fabricated review was accepted.

The terminal also warned that global model.generationConfig timeout/maxRetries/extra_body were ignored for provider catalog entries. Future scoped runs must place those values in the selected modelProviders.openai[].generationConfig. Current batch did not establish the cause of the provider latency or prove a child-agent capability failure; it established actual team creation followed by the wall deadline before child launches.

All owned native PIDs were absent after completion; no descendants of final PIDs remained. Early stdin-handoff probes were stopped only by their verified owned PIDs. stdout.jsonl, stderr.txt, launch_metadata.json and terminal.json remain in each batch directory. Individual early failures remain preserved.

## Useful source artifacts and exact patches

- DeepSeek Pro completed D3D12 source: d3d12_pro_nonthinking_20261004T101008434Z/d3d12_crossadapter_buffer.cpp. Original source had defects; it is not a passing hardware receipt.
- Independent Qwen D3D12 review: qwen_independent_work_20261004T102000/d3d12_review/review.json. Original-pattern corruption finding was confirmed. Several other review claims were false and rejected, including ROW_MAJOR buffer claims and flags supposedly not cleared.
- Qwen placed-heap revision: qwen_placed_heap_repair_20261004T102700/repair/d3d12_placed_heap_correction.cpp. It introduced an invalid CreateHeap signature and remained rejected until a narrow patch.
- Exact D3D12 signature/error patch: qwen_heap_signature_patch_20261004T103700/repair/answer.json. Both old substrings were verified to match the generated placed-heap revision. CreateHeap uses D3D12_HEAP_DESC. The suggested alignment fallback is a review point, not hardware evidence.
- Exact Vulkan forwarding/version patch: qwen_vulkan_flow_patch_20261004T103800/repair/answer.json. Both old substrings were verified to match qwen_vulkan_repair_20261004T103000/repair/vulkan_two_device_correction.cpp. It preserves actual A readback bytes for B upload, keeps original-pattern comparison, and removes the optional core-1.1 group diagnostic from the 1.0 application.
- Qwen architecture review: architecture_max_nonthinking_20261004T101055904Z/architecture_review.json. Advisory only. Its claim that explicit PyRe multiple-device selection means sequential allocations on the same device is wrong. Backend branch removal and blanket hardware-validation claims were rejected.

Kimi returned HTTP403 AccessDenied.Unpurchased. qwen3-coder-plus Coding Plan endpoint returned HTTP405 restricting access to coding agents; no bypass or authentication attempt occurred. GPT-OSS routes were partial after provider deadlines and were not accepted as genuine completed independent routing. Gemini canary had no complete response. Grok catalog was unauthenticated; no Grok login was attempted.

## Usage and credential audit

Immutable final snapshot: provider_usage_ledger_20261004T103603703Z.json. It records 30 terminal/request receipts, 256472 observed tokens, and 13 receipts with usage unavailable. Startup failures may have no inference; killed and timeout calls may have billed usage absent from local output. This is an observed subtotal, not a complete billing total.

API prompt/completion tokens, CLI counts, provider dashboard monthly units, percentages and reset dates are different quantities. No token-to-quota conversion is asserted. Every provider-original product_accepted field is false; independently modified and tested apparatus is evaluated in its own receipts.

credential_persistence_audit_20261004T103600.json checked 209 text artifacts against configured credential values without printing values. Zero configured credential value matches and zero credential-file names were found. HTTP authorization headers were constructed only in process memory, not persisted in request JSON or logs. This check covers the bounded harness evidence directory and configured values, not every possible secret on the host.
