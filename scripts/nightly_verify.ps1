<#
.SYNOPSIS
    Thin wrapper around scripts\nightly_verify.py for Windows Task Scheduler (target T7).

.DESCRIPTION
    Resolves the Python 3.10 interpreter that has the project's dependencies, runs the
    nightly verification, and propagates its exit code so a RED nightly is loud.
    Exit codes: 0 = all PASS, 1 = a check FAILED, 2 = the job could not fully run.
    Receipts are written under <repo>\records\nightly\<UTC stamp>\.

.NOTES
    Register the nightly task ONCE from an elevated prompt (not done automatically):

      schtasks /Create /SC DAILY /ST 03:00 /TN "TheHarness\NightlyVerify" ^
        /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\the_harness\scripts\nightly_verify.ps1" ^
        /RL LIMITED

    Inspect / run / remove it with:
      schtasks /Query  /TN "TheHarness\NightlyVerify" /V /FO LIST
      schtasks /Run    /TN "TheHarness\NightlyVerify"
      schtasks /Delete /TN "TheHarness\NightlyVerify" /F
#>

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Script   = Join-Path $PSScriptRoot 'nightly_verify.py'

# The interpreter that has pytest/pyopencl on this host. Fall back to PATH, then to
# the launcher, but never to a different major version silently.
$Candidates = @(
    'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe',
    (Get-Command python -ErrorAction SilentlyContinue).Source
)
$Python = $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $Python) {
    Write-Host "NIGHTLY VERDICT: JOB_ERROR - no usable python.exe found - exit 2"
    exit 2
}

Write-Host "nightly_verify: repo=$RepoRoot python=$Python"

# ErrorActionPreference must NOT be Stop here: a Stop preference turns Write-Error into
# a terminating error, which would abort this script before `exit $Code` and mask the
# difference between exit 1 (a check FAILED) and exit 2 (the job could not run).
$ErrorActionPreference = 'Continue'
& $Python -B $Script --repo-root $RepoRoot @args
$Code = $LASTEXITCODE

if ($Code -ne 0) {
    # Loud failure: the non-zero exit is what Task Scheduler records, and this line is
    # what an operator sees in the task history / redirected output.
    Write-Host ""
    Write-Host "*** NIGHTLY VERIFY WAS RED (exit $Code) ***"
    Write-Host "    Newest receipt: $RepoRoot\records\nightly\"
    Write-Host "    exit 1 = a check FAILED (component regression)"
    Write-Host "    exit 2 = the job could not fully run (infrastructure fault)"
}
exit $Code
