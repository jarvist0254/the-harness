# Derived F32 GGUF provenance

This file records a separate diagnostic input derived from the pinned Q8_0 model. It does not change or supersede any Q8_0 parity failure.

The input was `records/models/qwen3_06b/Qwen3-0.6B-Q8_0.gguf`, SHA256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`, 639,446,688 bytes. The clean llama.cpp export is commit `0faee5004297c3bcfa40b7bf11750127b8c1fd7d`, archive SHA256 `7B1C763340C17226B4DF928DC34A62150F8D27DECC22AF0CE808EB16BF027872`. The built `llama-quantize.exe` SHA256 is `28d19fcf648406bb7e77dc5afcd4a43867f0ad92550c50409d0c63e8e061f332`.

The command was:

```text
llama-quantize.exe --allow-requantize --pure --max-buffer-size 256 E:\the_harness\records\models\qwen3_06b\Qwen3-0.6B-Q8_0.gguf E:\the_harness\records\models\qwen3_06b_f32_derived\Qwen3-0.6B-Q8_0-dequant-F32.gguf F32 4
```

It completed in 3.909 seconds under the 180-second bound with exit 0. The quantizer dry-run predicted 2,273.75 MiB. The output is 2,390,150,816 bytes, below the enforced 3 GiB ceiling, with SHA256 `bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80`. The original Q8_0 file remained unchanged. E: had approximately 832.5 GB free before the conversion.

A second no-write quantizer dry-run loaded the derived GGUF and reported 310 tensors, `general.file_type=0`, `qwen3.block_count=28`, and `tokenizer.ggml.tokens` length 151,936. All 310 tensor records were `f32`; the requested dry-run output did not exist afterward. No inference was performed with this derived file. The linked Vulkan backend printed device enumeration during quantizer startup; the pinned quantization path dequantizes tensor rows and calls CPU `ggml_quantize_chunk`, with no Vulkan graph execution in the conversion loop.

Exact build, help, dry-run, conversion, and verification logs and process receipts are in `records/vulkan_llm_qualification_20261004/quantizer_build/`. The tool documentation warns that requantizing already quantized tensors can reduce quality compared with converting from F16/F32, so this artifact is a numerical diagnostic fixture only.
