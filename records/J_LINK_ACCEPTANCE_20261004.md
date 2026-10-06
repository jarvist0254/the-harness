# J-Link continuation acceptance — 2026-10-04

Accepted scope: a real, bounded Python/OpenCL residual neural workload across the installed NVIDIA RTX 5070 Ti and AMD gfx1036 integrated GPU. Both vendor orders pass independent CPU tensor comparisons. Corruption of actual forwarded activation is detected after all remaining GPU layers execute. Four discrete 8 GB cards and Intel execution are not present; direct P2P, larger-than-one-card LLM capacity and production chassis fit are not qualified.

## Final implementation and evidence

Final `j_link/opencl_executor.py` SHA-256:

`FF13C3783BDA61CF153B1BB58AFB9472BBE9C2404FA056C2816D011E749EA387`

The final GPU-free suite passes 47 tests. Root independently reran the full suite and all four hypothetical profiles, then inspected final-hash raw hardware logs: `root_validation_20261004/receipt.json`. The implementer's final commands, process IDs, RED diagnostic reproduction and results are in `opencl_executor_20261004/final_revision/receipt.md` and adjacent raw logs. All six final hardware-run process IDs were confirmed absent. Earlier pre-Grok and post-Grok revisions remain preserved; their results bind to their own source hashes.

| Final command | Expected exit | Measured result |
|---|---:|---|
| `python -B j_link/opencl_executor.py` | 0 | NVIDIA then AMD; 8 kernels, 8 CPU comparisons, all parity true |
| `python -B j_link/opencl_executor.py --reverse` | 0 | AMD then NVIDIA; 8 kernels, 8 CPU comparisons, all parity true |
| `python -B j_link/opencl_executor.py --inject-corruption` | 1 | Actual vendor-boundary corruption after layer 03; all 8 kernels executed, last 4 comparisons and final parity fail; control detected |

Clean final absolute error: `8.344650268554688e-06`, with `atol=rtol=5e-5`. Corrupted final error: `1.001207709312439`. Eight distinct layer weight/bias hashes, eight initial weight uploads totaling 8,404,992 bytes, two activation uploads, eight diagnostic readbacks totaling 131,072 bytes, and one actual 16,384-byte host-staged context boundary are recorded. Within an owner's stage, activations use resident device ping-pong buffers. Each owner's assigned weights are resident before the first kernel.

The model is `relu(x + x @ W + b)`, eight FP32 layers, width 512, batch 8, seed 103004. Nine MiB per device is an intentional placement policy, not observed free memory. Advertised allocation limits are checked before context/buffer creation; unknown limits return NOT_CHECKED. Runtime allocations still may fail and do not establish physical residency or fresh available VRAM. AMD integrated memory is shared host memory. Every runtime discovery/execution takes place under a 60-second child supervisor; there are no persistent workers or durable recovery claims.

## Requested factory/model work

Actual completed sequence: Qwen/DeepSeek candidate work and independent reviews; Gemini `gemini-3.8-flash-high` substantive review; Grok `grok-4.7-build-fast` corrective code edit; in-house application and tests; root acceptance. Grok supplied four exact replacements and six tests. They fix unknown maximum-allocation admission and first-vendor-boundary corruption. Root reporting, extra supervisor/admission tests and nonfinite diagnostics are attributed separately. The original rejected Qwen MLP source was never executed.

The complete provider receipt is `factory_runs/20261004/gemini_grok_pipeline_20261004T110000/PIPELINE_RECEIPT_20261004T112000.md`. It preserves the failed initial Grok attempt and successful retry, Gemini finding adjudication, and Grok's raw answer/extracted patch. Gemini's PCI-domain claim was contradicted by a live installed-runtime query and was not applied.

The immutable deduplicated ledger `factory_runs/20261004/provider_usage_ledger_FINAL_20261004T112000.json` records 38 attempts and 412,580 reported observed tokens; fourteen rows have unknown usage. Qwen had 22 attempts and 132,785 reported tokens; DeepSeek 9 and 95,386; Gemini 2 and 91,397; Grok 2 and 19,985; GPT-OSS 2 and 73,027. Completed output is distinct from accepted source or completed hardware work. Reported tokens cannot be converted to the monthly dashboard percentage. The latest scoped credential audit recorded zero configured-key matches; owned provider processes ended.

Native Qwen/DeepSeek prompts authorized up to ten children each. Teams were created, but no child launches completed before their deadlines. Direct API calls launched no native children. The task runner performed purposeful bounded jobs; the disabled global Factory queue and unrelated jobs were not revived.

## Four-card integrated design and next qualification

All four hypothetical 8 GB population fixtures fit 24,576 MiB of synthetic blocks within a modeled aggregate budget of 26,624 MiB; the identical workload fails with three cards. These remain PLANNED_NOT_ALLOCATED results. The small executor also has a matched four-versus-three policy regression; its bounded buffers cannot qualify real 8 GB capacity.

The integrated core study repacks all four mounts, with authorized GPU overhang and no appended fourth module. Three upright cards plus one rolled top is a candidate. See `layout_3plus1_concept.svg`/`.png` and `../docs/01_HARNESS_MASTER.md`. Receiver, PSU, card support patches, cable bends and removal interfaces remain unmeasured. This is a visual packing concept, not complete CAD, a fit PASS or a production STL.

`../docs/03_EXPERIMENT_RUNBOOK.md` contains the release test: four unique physical IDs; four-card computation/reverse/corruption; a separate actual-capacity model exceeding one card's measured usable dedicated memory; an optional greater-than-three-card workload proving D is necessary; supported operations and transfer matrix; bounded failure/cancellation/restart controls; fit/load/creep coupons; and simultaneous electrical/thermal qualification. Future results are NOT_CHECKED until that evidence exists.

Current integrity commands, from `E:\the_harness`:

```powershell
python -B -m unittest discover -s j_link/tests -v
python -B scripts/verify_adaptation.py
```

`ADAPTATION_SHA256_20261004.json` hashes the current curated code, documents and evidence. `PACKAGE_SHA256.json` remains the original import baseline. The full imported-file scope audit checked 5,671 entries: seventeen authorized baseline changes, no missing files and no changes outside the allowed adaptation list; recovered sources and pinned repository content remain intact. The manifest is an integrity check, not evidence for unperformed hardware gates.
