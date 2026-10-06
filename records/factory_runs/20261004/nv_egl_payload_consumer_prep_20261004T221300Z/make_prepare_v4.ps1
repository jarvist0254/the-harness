$p=Join-Path $PSScriptRoot 'prepare_packet_v2.ps1'
$s=[IO.File]::ReadAllText($p)
$fixed=@'
$selected=@($gl|Where-Object{($_ -match '^typedef\s' -and $_ -notmatch '\(GL_APIENTRYP PFN') -or $_ -match '^#define\s+GL_'})
'@
$s=[regex]::Replace($s,'(?m)^\$selected=.*$', [Text.RegularExpressions.MatchEvaluator]{param($m) $fixed})
$s=$s.Replace('v2','v4').Replace('V2','V4')
$out=Join-Path $PSScriptRoot 'prepare_packet_v4.ps1'
if(Test-Path -LiteralPath $out){throw 'immutable v4 exists'}
[IO.File]::WriteAllText($out,$s,[Text.UTF8Encoding]::new($false))
& $out
