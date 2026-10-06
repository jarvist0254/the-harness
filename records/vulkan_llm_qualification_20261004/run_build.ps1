$ErrorActionPreference = 'Stop'
$e = 'E:\the_harness\records\vulkan_llm_qualification_20261004'
$cmd = Join-Path $e 'build_targets.cmd'
$out = Join-Path $e 'build_targets.stdout.log'
$err = Join-Path $e 'build_targets.stderr.log'
$p = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/c',('"'+$cmd+'"')) -PassThru -WindowStyle Hidden -WorkingDirectory $e -RedirectStandardOutput $out -RedirectStandardError $err
$childPid = $p.Id
$start = [DateTime]::UtcNow
$deadline = $start.AddMinutes(20)
while (-not $p.HasExited -and [DateTime]::UtcNow -lt $deadline) {
  if ($p.WaitForExit(30000)) { break }
  $elapsed = [int]([DateTime]::UtcNow - $start).TotalSeconds
  Write-Output "BUILD_RUNNING pid=$childPid elapsed_seconds=$elapsed"
  Get-Content -LiteralPath $out -Tail 6 -ErrorAction SilentlyContinue
  Get-Content -LiteralPath $err -Tail 4 -ErrorAction SilentlyContinue
}
if (-not $p.HasExited) { $p.Kill($true); $p.WaitForExit(); $status = 'TIMEOUT_1200S' } else { $p.WaitForExit(); $status = "EXIT_$($p.ExitCode)" }
[ordered]@{pid=$childPid;status=$status;elapsed_seconds=[int]([DateTime]::UtcNow - $start).TotalSeconds;stdout=$out;stderr=$err;command=$cmd} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $e 'build_targets.json') -Encoding UTF8
Write-Output (Get-Content -LiteralPath (Join-Path $e 'build_targets.json') -Raw)
Get-Content -LiteralPath $out -Tail 30
Get-Content -LiteralPath $err -Tail 18
