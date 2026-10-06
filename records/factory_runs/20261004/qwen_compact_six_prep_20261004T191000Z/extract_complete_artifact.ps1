param([Parameter(Mandatory)][ValidateSet('qwen_l0_query','qwen_l0_peer_copy','qwen_directed_receipt','qwen_four_capacity','qwen_cuda_dmabuf_export','qwen_fp32_adjudication')][string]$Job)
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'research_artifact.ps1')
$dir=Join-Path $PSScriptRoot $Job
$terminal=Read-StrictJson ([IO.File]::ReadAllText((Join-Path $dir 'terminal.json')))
if($terminal.status-cne'COMPLETE_RESEARCH_STAGED_UNAPPLIED'-or$terminal.finish_reason-cne'stop'-or!$terminal.done-or!$terminal.usage_known-or$terminal.observed_model-cne'qwen3.8-max'){throw 'Complete exact-model final stream and usage required'}
$path=Join-Path $dir 'research.pending_root_qa.json'
$a=Read-StrictJson ([IO.File]::ReadAllText($path));Assert-ResearchArtifact $a
$extension=if($Job-in@('qwen_directed_receipt','qwen_four_capacity','qwen_fp32_adjudication')){'.py'}else{'.cpp'}
$outputs=@()
foreach($part in @('source','tests_source')){
 if(!$a.$part.Length){continue}
 $file=Join-Path $dir ($part+'.qwen_untrusted'+$(if($part-ceq'source'){$extension}else{'.txt'}))
 if(Test-Path -LiteralPath $file){throw 'Refusing immutable extraction overwrite'}
 [IO.File]::WriteAllText($file,$a.$part,[Text.UTF8Encoding]::new($false))
 $outputs+=@{field=$part;path=$file;chars=$a.$part.Length;sha256=(Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant()}
}
Save-NewJson (Join-Path $dir 'EXTRACTION_ONLY_RECEIPT.json') @{job=$Job;artifact_sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();provider_status=$a.status;files=$outputs;action='Exact JSON source-string extraction only';candidate_parsed_imported_compiled_executed=$false;provider_tests_executed=$false;root_admission=$false}
@{job=$Job;artifact_sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();provider_status=$a.status;files=$outputs}|ConvertTo-Json -Depth 6
