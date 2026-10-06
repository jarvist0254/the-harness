param([Parameter(Mandatory)][ValidateSet('qwen_intel_peer_copy','qwen_intel_nvidia_external_query','qwen_intel_backend_contract','qwen_four_physical_capacity_tests','qwen_vulkan_numeric_state_ledger','qwen_linux_dmabuf_transport')][string]$Job)
. (Join-Path $PSScriptRoot 'provider_common.ps1')
. (Join-Path $PSScriptRoot 'research_artifact.ps1')
$dir=Join-Path $PSScriptRoot $Job
$terminal=Read-StrictJson ([IO.File]::ReadAllText((Join-Path $dir 'terminal.json')))
if($terminal.status-cne'COMPLETE_RESEARCH_STAGED_UNAPPLIED'-or$terminal.finish_reason-cne'stop'-or!$terminal.done-or!$terminal.usage_known-or$terminal.observed_model-cne'qwen3.8-max'){throw 'Complete exact-model final stream and usage required'}
$path=Join-Path $dir 'research.pending_root_qa.json'
$a=Read-StrictJson ([IO.File]::ReadAllText($path));Assert-ResearchArtifact $a
$extension=if($Job-in@('qwen_intel_backend_contract','qwen_four_physical_capacity_tests','qwen_vulkan_numeric_state_ledger')){'.py'}else{'.cpp'}
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
