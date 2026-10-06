$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$j=Get-Content -Raw -LiteralPath (Join-Path $r 'llama_logits_launches.json')|ConvertFrom-Json
while($true){$p=Get-Process -Id $j.pid -ErrorAction SilentlyContinue;if(!$p){break};$start=[DateTime]::Parse($j.started_utc).ToUniversalTime();if([math]::Abs(($p.StartTime.ToUniversalTime()-$start).TotalSeconds)-gt10){break};if(([DateTime]::UtcNow-$start).TotalSeconds-gt270){& "$env:SystemRoot\System32\taskkill.exe" /PID $j.pid /T /F 2>&1|Out-File -LiteralPath (Join-Path $r 'llama_logits.cleanup.txt');break};Start-Sleep -Seconds 5}
@{ended_utc=[DateTime]::UtcNow.ToString('o');owned_pid=$j.pid}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $r 'llama_logits_watchdog_terminal.json')

