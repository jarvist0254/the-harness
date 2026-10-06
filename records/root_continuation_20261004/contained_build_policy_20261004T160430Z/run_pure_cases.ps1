param(
    [ValidateSet('boundary', 'legacy44')]
    [string]$Case
)

$ErrorActionPreference = 'Stop'
$rootDir = 'E:\the_harness'
$taskDir = 'E:\the_harness\records\root_continuation_20261004\contained_build_policy_20261004T160430Z'
$python = 'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
$expectedPythonHash = '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
$expectedHashes = @{
    baseline = '3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c'
    candidate = 'fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3'
    boundary_tests = 'c9bbbb16a2f4c4eca94a3bf9abfa530d8222874fd185dcd7fc9a2674658fc11c'
    legacy44_copy = '53d2c3468eecbd6cca0c71b263b9293788123ed8183cc18101ff09d2f800e6e5'
    python310 = $expectedPythonHash
}
$baselinePath = 'E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py'
$candidatePath = Join-Path $taskDir 'contained_build_supervisor.py'
$boundaryPath = Join-Path $taskDir 'test_build_policy_boundaries.py'
$legacyPath = Join-Path $taskDir 'evaluate_revision2_build_candidate.py'
$required = @{
    baseline = $baselinePath
    candidate = $candidatePath
    boundary_tests = $boundaryPath
    legacy44_copy = $legacyPath
    python310 = $python
}

function Get-Sha256([string]$path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
}

function Get-HashSet {
    $set = @{}
    foreach ($key in $required.Keys) { $set[$key] = Get-Sha256 $required[$key] }
    return $set
}

if ((Get-Sha256 $python) -ne $expectedPythonHash) { throw 'Pinned Python 3.10 hash mismatch' }
if ($Case -eq 'boundary') {
    $childArgs = @('-B', '-m', 'unittest', '-v', 'test_build_policy_boundaries')
} else {
    $childArgs = @('-B', 'evaluate_revision2_build_candidate.py')
}

$outDir = Join-Path $taskDir (Join-Path 'pure_runs' $Case)
if (Test-Path -LiteralPath $outDir) { throw 'Output directory already exists; refusing overwrite' }
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$stdoutPath = Join-Path $outDir 'stdout.raw.log'
$stderrPath = Join-Path $outDir 'stderr.raw.log'
$receiptPath = Join-Path $outDir 'run_receipt.json'
$before = Get-HashSet
foreach ($key in $expectedHashes.Keys) {
    if ($before[$key] -ne $expectedHashes[$key]) { throw "Pre-run hash mismatch: $key" }
}
$timer = [System.Diagnostics.Stopwatch]::StartNew()
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $python
$psi.Arguments = [string]::Join(' ', $childArgs)
$psi.WorkingDirectory = $taskDir
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$proc = [System.Diagnostics.Process]::new()
$proc.StartInfo = $psi
$null = $proc.Start()
$stdoutTask = $proc.StandardOutput.ReadToEndAsync()
$stderrTask = $proc.StandardError.ReadToEndAsync()
$childId = $proc.Id
$waited = $proc.WaitForExit(15000)
$timedOut = -not $waited
$killAttempted = $false
$drained = $waited
if ($timedOut) {
    $killAttempted = $true
    try { $proc.Kill() } catch {}
    $drained = $proc.WaitForExit(5000)
}
$timer.Stop()
$exitCode = $null
if ($drained) { $exitCode = $proc.ExitCode }
if ($drained) {
    $stdoutText = $stdoutTask.GetAwaiter().GetResult()
    $stderrText = $stderrTask.GetAwaiter().GetResult()
} else {
    $stdoutText = ''
    $stderrText = 'process did not drain after owned-child timeout cleanup'
}
[System.IO.File]::WriteAllText($stdoutPath, $stdoutText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($stderrPath, $stderrText, [System.Text.UTF8Encoding]::new($false))
$after = Get-HashSet
$stdoutBytes = if (Test-Path -LiteralPath $stdoutPath) { (Get-Item -LiteralPath $stdoutPath).Length } else { 0 }
$stderrBytes = if (Test-Path -LiteralPath $stderrPath) { (Get-Item -LiteralPath $stderrPath).Length } else { 0 }
$pidStillPresent = $false
try { $null = Get-Process -Id $childId -ErrorAction Stop; $pidStillPresent = $true } catch {}
$streamsWithinCap = ($stdoutBytes -le 1048576 -and $stderrBytes -le 1048576)
$pinsUnchanged = $true
foreach ($key in $required.Keys) { if ($before[$key] -ne $after[$key]) { $pinsUnchanged = $false } }
$pass = (-not $timedOut) -and $drained -and ($exitCode -eq 0) -and (-not $pidStillPresent) -and $streamsWithinCap -and $pinsUnchanged
$receipt = [ordered]@{
    case = $Case
    command = @($python) + $childArgs
    cwd = $taskDir
    timeout_seconds = 15
    elapsed_seconds = [Math]::Round($timer.Elapsed.TotalSeconds, 6)
    pid = $childId
    create_no_window = $psi.CreateNoWindow
    timeout_kill_attempted_on_retained_child_only = $killAttempted
    child_drained = $drained
    exit_code = $exitCode
    pid_absent_after_wait = (-not $pidStillPresent)
    stdout_bytes = $stdoutBytes
    stderr_bytes = $stderrBytes
    each_stream_cap_bytes = 1048576
    streams_within_cap = $streamsWithinCap
    hashes_before = $before
    hashes_after = $after
    hashes_unchanged = $pinsUnchanged
    native_supervisor_api_calls = 'NOT_ATTEMPTED'
    native_workers_or_gpu = 'NOT_ATTEMPTED'
    status = if ($pass) { 'PURE_TESTS_PASS' } else { 'PURE_TESTS_FAIL' }
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Write-Output ($receipt | ConvertTo-Json -Depth 8)
if (-not $pass) { exit 1 }
