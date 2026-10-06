$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$jobs=Get-Content -Raw -LiteralPath (Join-Path $root 'launches.json')|ConvertFrom-Json
$watch=[Diagnostics.Stopwatch]::StartNew()
$records=@()
while($watch.Elapsed.TotalSeconds -lt 285){
 $active=0
 foreach($j in $jobs){
  $p=Get-Process -Id $j.pid -ErrorAction SilentlyContinue
  if(!$p){continue}
  # Never terminate an unrelated process after PID reuse.
  if([math]::Abs(($p.StartTime.ToUniversalTime()-[DateTime]::Parse($j.started_utc).ToUniversalTime()).TotalSeconds) -gt 10){continue}
  $active++
  $age=([DateTime]::UtcNow-[DateTime]::Parse($j.started_utc).ToUniversalTime()).TotalSeconds
  if($age -gt $j.outer_deadline_seconds){
   & "$env:SystemRoot\System32\taskkill.exe" /PID $j.pid /T /F 2>&1|Out-File -LiteralPath (Join-Path $root ($j.job+'.cleanup.txt'))
   $records+=@{job=$j.job;pid=$j.pid;status='OWNED_DEADLINE_TREE_STOPPED';utc=[DateTime]::UtcNow.ToString('o')}
  }
 }
 if(!$active){break}
 Start-Sleep -Seconds 5
}
$records|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $root 'watchdog_cleanup.json')
@{seconds=[math]::Round($watch.Elapsed.TotalSeconds,1);ended_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'watchdog_terminal.json')
