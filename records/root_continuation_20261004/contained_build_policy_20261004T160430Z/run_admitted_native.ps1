$ErrorActionPreference = 'Stop'
$taskDir = 'E:\the_harness\records\root_continuation_20261004\contained_build_policy_20261004T160430Z'
$fixtureDir = Join-Path $taskDir 'native_fixture_prepared'
$python = 'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
$rootAdmission = Join-Path $taskDir 'ROOT_NATIVE_FIXTURE_ADMISSION.json'
$source = Join-Path $taskDir 'contained_build_supervisor.py'
$driver = Join-Path $fixtureDir 'fixture_driver.py'
$controller = Join-Path $fixtureDir 'fixture_controller.py'
$worker = Join-Path $fixtureDir 'worker.py'
$contract = Join-Path $fixtureDir 'fixture_contract.json'
$preparedAdmission = Join-Path $fixtureDir 'fixture_admission.json'
$outerRoot = Join-Path $taskDir 'native_outer_runs'
$outerRun = Join-Path $outerRoot 'run_001'

$expected = @{
    root_admission = 'cb3dfaa9c23e65638504987ac1e23a2aa845af6854835696ea82143b33d4dd4e'
    source = 'fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3'
    driver = '67cc496dc00e09ba56df6d5cb9a590a62a5a2f87becf0cdfaff51d98b2ac12df'
    controller = '4ec44fbc5277e69f8e6607c794c9c1f3c32cfab1b6f08f64ece9213fcd72fe15'
    worker = '6d9cffd5e7a610f69754c513789d45ed88286a57a79c8c08830b88a9c39efc31'
    contract = 'e28cb0072e69df9e863984ac744e57aa157c4e0f4a44f075335b1d7ea44aecdc'
    prepared_admission = '38dccba35270518c2d282370a76dd7f437a3e0d4e488e075549a15a124d102ba'
    python310 = '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
    baseline = '3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c'
}
$files = [ordered]@{
    root_admission = $rootAdmission
    source = $source
    driver = $driver
    controller = $controller
    worker = $worker
    contract = $contract
    prepared_admission = $preparedAdmission
    python310 = $python
    baseline = 'E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py'
}

function Get-Sha([string]$path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() }
function Get-InputHashes {
    $map = [ordered]@{}
    foreach ($key in $files.Keys) { $map[$key] = Get-Sha $files[$key] }
    return $map
}

if (Test-Path -LiteralPath $outerRun) { throw 'Outer result folder exists; refusing overwrite' }
if (Test-Path -LiteralPath (Join-Path $fixtureDir 'native_runs')) { throw 'Native output already exists; refusing reuse' }
$before = Get-InputHashes
foreach ($key in $expected.Keys) {
    if ($before[$key] -ne $expected[$key]) { throw "Pinned pre-run hash mismatch: $key" }
}
$root = [System.IO.File]::ReadAllText($rootAdmission) | ConvertFrom-Json
$prep = [System.IO.File]::ReadAllText($preparedAdmission) | ConvertFrom-Json
$contractData = [System.IO.File]::ReadAllText($contract) | ConvertFrom-Json
if ($root.authorization -ne 'ROOT_ADMITTED_FIVE_FIXED_NATIVE_CPU_FIXTURES') { throw 'Root admission authorization mismatch' }
if ($root.source_sha256 -ne $expected.source -or $root.driver_sha256 -ne $expected.driver -or
    $root.controller_sha256 -ne $expected.controller -or $root.worker_sha256 -ne $expected.worker -or
    $root.prepared_contract_sha256 -ne $expected.contract -or
    $root.prepared_admission_sha256 -ne $expected.prepared_admission) { throw 'Root admission pins disagree' }
if ($prep.native_cases_started -ne $false -or $prep.source.sha256 -ne $expected.source) { throw 'Prepared admission state/pin invalid' }
if ($contractData.max_workers -ne 4 -or $contractData.max_worker_deadline_seconds -ne 5 -or
    $contractData.fixture_uses_extended_deadline -ne $false -or
    $contractData.build_policy_deadline_ceiling_seconds -ne 600) { throw 'Fixture scope limits changed' }
if ($prep.fixture_hashes_sha256.'fixture_driver.py' -ne $expected.driver -or
    $prep.fixture_hashes_sha256.'fixture_controller.py' -ne $expected.controller -or
    $prep.fixture_hashes_sha256.'worker.py' -ne $expected.worker -or
    $prep.fixture_hashes_sha256.'fixture_contract.json' -ne $expected.contract) { throw 'Prepared fixture pins disagree' }
if ($prep.run_command[0] -ne $python -or $prep.run_command[1] -ne $driver -or $prep.run_command[2] -ne '--run') { throw 'Prepared run command mismatch' }

New-Item -ItemType Directory -Path $outerRun -Force | Out-Null
$stdoutPath = Join-Path $outerRun 'driver_stdout.raw.log'
$stderrPath = Join-Path $outerRun 'driver_stderr.raw.log'
$receiptPath = Join-Path $outerRun 'outer_receipt.json'
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $python
$psi.Arguments = '-B fixture_driver.py --run'
$psi.WorkingDirectory = $fixtureDir
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$clock = [System.Diagnostics.Stopwatch]::StartNew()
$proc = [System.Diagnostics.Process]::new()
$proc.StartInfo = $psi
$null = $proc.Start()
$driverId = $proc.Id
$stdoutTask = $proc.StandardOutput.ReadToEndAsync()
$stderrTask = $proc.StandardError.ReadToEndAsync()
$finished = $proc.WaitForExit(45000)
$timeoutKill = $false
$drained = $finished
if (-not $finished) {
    $timeoutKill = $true
    try { $proc.Kill() } catch {}
    $drained = $proc.WaitForExit(8000)
}
$clock.Stop()
$exitCode = $null
if ($drained) { $exitCode = $proc.ExitCode }
if ($drained) {
    $stdoutText = $stdoutTask.GetAwaiter().GetResult()
    $stderrText = $stderrTask.GetAwaiter().GetResult()
} else {
    $stdoutText = ''
    $stderrText = 'driver did not drain after owned-child timeout cleanup'
}
[System.IO.File]::WriteAllText($stdoutPath, $stdoutText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($stderrPath, $stderrText, [System.Text.UTF8Encoding]::new($false))
$after = Get-InputHashes
$samePins = $true
foreach ($key in $expected.Keys) { if ($before[$key] -ne $after[$key]) { $samePins = $false } }
$outBytes = (Get-Item -LiteralPath $stdoutPath).Length
$errBytes = (Get-Item -LiteralPath $stderrPath).Length
$streamsWithinCap = ($outBytes -le 2097152 -and $errBytes -le 2097152)
$driverPresent = $false
try { $null = Get-Process -Id $driverId -ErrorAction Stop; $driverPresent = $true } catch {}
$receipt = [ordered]@{
    authorization_sha256 = $expected.root_admission
    authorization = 'ROOT_ADMITTED_FIVE_FIXED_NATIVE_CPU_FIXTURES'
    command = @($python, '-B', 'fixture_driver.py', '--run')
    working_directory = $fixtureDir
    outer_deadline_seconds = 45
    elapsed_seconds = [Math]::Round($clock.Elapsed.TotalSeconds, 6)
    driver_pid = $driverId
    create_no_window = $psi.CreateNoWindow
    driver_finished = $finished
    timeout_kill_attempted_on_retained_driver_only = $timeoutKill
    driver_drained = $drained
    driver_exit_code = $exitCode
    driver_pid_absent_after_wait = (-not $driverPresent)
    stdout_bytes = $outBytes
    stderr_bytes = $errBytes
    each_stream_cap_bytes = 2097152
    streams_within_cap = $streamsWithinCap
    input_hashes_before = $before
    input_hashes_after = $after
    input_hashes_unchanged = $samePins
    native_fixture_status = if ($finished -and $drained -and $exitCode -eq 0 -and $streamsWithinCap -and $samePins -and -not $driverPresent) { 'DRIVER_RETURNED_ZERO' } else { 'DRIVER_EXECUTION_INCOMPLETE_OR_FAILED' }
    note = 'Root-admitted exact five-case CPU fixture only; no build/GPU/provider/global queue use.'
}
[System.IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 8
if ($receipt.native_fixture_status -ne 'DRIVER_RETURNED_ZERO') { exit 1 }
