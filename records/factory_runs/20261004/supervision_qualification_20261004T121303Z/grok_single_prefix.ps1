$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$work=Join-Path $root 'grok_single_device';New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
$src=Join-Path $root 'grok_context_padding\llama_logits_context_corrected.cpp'
$sha=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
if($sha -ne '54AD6FD03CADF8B302B4F6705AEC9AB280253277A2F5E00468E59B379CECD2FC'){throw 'source hash mismatch'}
$prompt=Get-Content -Raw -LiteralPath (Join-Path $root 'grok_single_device.prompt.txt')
$prompt+=[Environment]::NewLine+'EXACT CURRENT SOURCE'+[Environment]::NewLine+(Get-Content -Raw -LiteralPath $src)
foreach($f in @('E:\the_harness\records\vulkan_llm_qualification_20261004\contextfix_default.stdout.json','E:\the_harness\records\vulkan_llm_qualification_20261004\contextfix_reverse.stdout.json','E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\include\llama.h','E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\ggml\include\ggml-backend.h')){$prompt+=[Environment]::NewLine+'SOURCE '+$f+[Environment]::NewLine+(Get-Content -Raw -LiteralPath $f)}
$pp=Join-Path $work 'request.txt';$prompt|Set-Content -LiteralPath $pp -Encoding utf8
