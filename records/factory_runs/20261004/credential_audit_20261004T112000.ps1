$ErrorActionPreference='Stop'
$base=$PSScriptRoot
$values=[Collections.Generic.List[string]]::new()
$settings=Get-Content -Raw -LiteralPath 'C:\Users\thoma\.qwen\settings.json'|ConvertFrom-Json
foreach($p in $settings.env.PSObject.Properties){if($p.Value -is [string] -and $p.Value.Length -ge 12){$values.Add($p.Value)}}
function CollectTokenValues($o){
 if($null -eq $o){return}
 if($o -is [string]){return}
 foreach($p in $o.PSObject.Properties){
  if($p.Name -match '(?i)token|secret|password|api.?key' -and $p.Value -is [string] -and $p.Value.Length -ge 12){$values.Add($p.Value)}
  elseif($p.Value -is [System.Collections.IEnumerable] -and $p.Value -isnot [string]){foreach($item in $p.Value){CollectTokenValues $item}}
  elseif($p.Value -is [pscustomobject]){CollectTokenValues $p.Value}
 }
}
$authPath='C:\Users\thoma\.grok\auth.json'
if(Test-Path -LiteralPath $authPath){CollectTokenValues (Get-Content -Raw -LiteralPath $authPath|ConvertFrom-Json)}
$files=@(Get-ChildItem -LiteralPath $base -Recurse -File|Where-Object {$_.Extension -in @('.json','.jsonl','.txt','.md','.ps1','.cpp','.py','.toml')})
$hits=0;$hitFiles=@()
foreach($f in $files){$s=[IO.File]::ReadAllText($f.FullName);$matched=$false;foreach($v in $values){if($s.Contains($v)){$matched=$true;break}};if($matched){$hits++;$hitFiles+=$f.FullName}}
$credentialNames=@($files|Where-Object {$_.Name -match '^(auth\.json|\.env|credentials.*)$'}|ForEach-Object {$_.FullName})
$pids=@(46804,38600,41304,77632,25688)
$alive=@(foreach($ownedPid in $pids){if(Get-Process -Id $ownedPid -ErrorAction SilentlyContinue){$ownedPid}})
$r=@{scope=$base;utc=[DateTime]::UtcNow.ToString('o');text_files_checked=$files.Count;credential_values_checked_count=$values.Count;configured_credential_matches=$hits;matching_file_paths=$hitFiles;credential_named_files=$credentialNames;owned_pids_checked=$pids;owned_pids_still_alive=$alive;secret_values_printed=$false;secret_values_saved=$false;limitations='Checks exact configured Qwen environment credential strings and Grok token/key fields. No claim about every possible unknown credential or external log.'}
$out=Join-Path $base 'credential_persistence_audit_20261004T112000.json'
$r|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $out -Encoding utf8
$r|ConvertTo-Json -Depth 8
