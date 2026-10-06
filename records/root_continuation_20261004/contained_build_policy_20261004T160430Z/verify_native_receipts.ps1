$ErrorActionPreference = 'Stop'
$taskDir = 'E:\the_harness\records\root_continuation_20261004\contained_build_policy_20261004T160430Z'
$fixtureDir = Join-Path $taskDir 'native_fixture_prepared'
$runRoot = Join-Path $fixtureDir 'native_runs\native_20261004T162557Z'
$outerReceipt = Join-Path $taskDir 'native_outer_runs\run_001\outer_receipt.json'
$expectedSource = 'fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3'
$expectedDriver = '67cc496dc00e09ba56df6d5cb9a590a62a5a2f87becf0cdfaff51d98b2ac12df'
$expectedController = '4ec44fbc5277e69f8e6607c794c9c1f3c32cfab1b6f08f64ece9213fcd72fe15'
$expectedWorker = '6d9cffd5e7a610f69754c513789d45ed88286a57a79c8c08830b88a9c39efc31'
$expectedPython = '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
$definitions = [ordered]@{
    natural = @{ status = 'PROCESS_COMPLETED'; reason = ''; workers = 4 }
    nonzero = @{ status = 'FAILED'; reason = 'nonzero_exit'; workers = 1 }
    timeout = @{ status = 'TIMEOUT'; reason = 'deadline'; workers = 1 }
    cancel = @{ status = 'CANCELLED'; reason = 'cancelled'; workers = 1 }
    overflow = @{ status = 'FAILED'; reason = 'LOG_LIMIT'; workers = 1 }
}

function Is-Absent([int]$pidValue) {
    try { $null = Get-Process -Id $pidValue -ErrorAction Stop; return $false } catch { return $true }
}

$suite = [System.IO.File]::ReadAllText((Join-Path $runRoot 'suite_receipt.json')) | ConvertFrom-Json
$outer = [System.IO.File]::ReadAllText($outerReceipt) | ConvertFrom-Json
$caseResults = @()
$allPass = $true
foreach ($caseName in $definitions.Keys) {
    $path = Join-Path (Join-Path $runRoot $caseName) 'outer_case_receipt.json'
    $r = [System.IO.File]::ReadAllText($path) | ConvertFrom-Json
    $s = $r.supervisor
    $expect = $definitions[$caseName]
    $workers = @($s.workers)
    $logs = $s.logs
    $pids = @($workers | ForEach-Object { [int]$_.pid })
    $currentPidsAbsent = $true
    foreach ($pidValue in $pids) { if (-not (Is-Absent $pidValue)) { $currentPidsAbsent = $false } }
    $naturalMarkers = $true
    if ($caseName -eq 'natural') {
        foreach ($worker in $workers) {
            $logProperty = $logs.PSObject.Properties[$worker.worker_id]
            if ($null -eq $logProperty) { $naturalMarkers = $false; continue }
            $log = $logProperty.Value
            if ($worker.exit_code -ne 0 -or -not $worker.assigned -or -not $worker.resumed -or
                $log.stdout.Trim() -ne ($worker.worker_id + ':stdout') -or
                $log.stderr.Trim() -ne ($worker.worker_id + ':stderr')) { $naturalMarkers = $false }
        }
    }
    $overflowControl = $true
    if ($caseName -eq 'overflow') {
        $workerId = $workers[0].worker_id
        $logProperty = $logs.PSObject.Properties[$workerId]
        if ($null -eq $logProperty) { $overflowControl = $false }
        else { $log = $logProperty.Value }
        if ($null -ne $logProperty) { $overflowControl = ($log.stdout_overflow -eq $true -and $log.stdout_bytes -eq 1024) }
    }
    $expectedWorkerExit = $null
    if ($caseName -eq 'nonzero') { $expectedWorkerExit = ($workers.Count -eq 1 -and $workers[0].exit_code -eq 3) }
    $corePass = (
        $r.case_id -eq $caseName -and
        $r.controller_exit_code -eq 0 -and
        $r.controller_timeout -eq $false -and
        $r.controller_pid_absent_after_wait -eq $true -and
        $r.worker_pids_absent_after_cleanup -eq $true -and
        $currentPidsAbsent -and
        $r.capture_limit_ok -eq $true -and
        $r.source_and_runtime_hashes_unchanged -eq $true -and
        $r.source_and_runtime_hashes_before.source -eq $expectedSource -and
        $r.source_and_runtime_hashes_after.source -eq $expectedSource -and
        $r.source_and_runtime_hashes_before.driver -eq $expectedDriver -and
        $r.source_and_runtime_hashes_after.driver -eq $expectedDriver -and
        $r.source_and_runtime_hashes_before.controller -eq $expectedController -and
        $r.source_and_runtime_hashes_after.controller -eq $expectedController -and
        $r.source_and_runtime_hashes_before.worker -eq $expectedWorker -and
        $r.source_and_runtime_hashes_after.worker -eq $expectedWorker -and
        $r.source_and_runtime_hashes_before.interpreter -eq $expectedPython -and
        $r.source_and_runtime_hashes_after.interpreter -eq $expectedPython -and
        $r.source_and_runtime_hashes_before.contract -eq 'e28cb0072e69df9e863984ac744e57aa157c4e0f4a44f075335b1d7ea44aecdc' -and
        $r.source_and_runtime_hashes_after.contract -eq 'e28cb0072e69df9e863984ac744e57aa157c4e0f4a44f075335b1d7ea44aecdc' -and
        $r.source_and_runtime_hashes_before.admission -eq '38dccba35270518c2d282370a76dd7f437a3e0d4e488e075549a15a124d102ba' -and
        $r.source_and_runtime_hashes_after.admission -eq '38dccba35270518c2d282370a76dd7f437a3e0d4e488e075549a15a124d102ba' -and
        $s.status -eq $expect.status -and
        $s.failure_reason -eq $expect.reason -and
        $s.drain_proof -eq 'CLEANUP' -and
        $s.whole_tree_certificate -eq $false -and
        $s.job_active_count -eq 0 -and
        $workers.Count -eq $expect.workers -and
        $r.restart_matches -eq $true -and
        $r.restart_commit_verified -eq $true -and
        $r.restart_receipt.run_id -eq $s.run_id -and
        $r.restart_receipt.status -eq $s.status -and
        $r.restart_receipt.failure_reason -eq $s.failure_reason -and
        $r.restart_receipt.drain_proof -eq $s.drain_proof -and
        $r.restart_receipt.reattach -eq $false -and
        $r.restart_receipt.replay -eq $false
    )
    foreach ($worker in $workers) {
        if (-not $worker.assigned -or -not $worker.resumed) { $corePass = $false }
    }
    if ($caseName -eq 'natural' -and -not $naturalMarkers) { $corePass = $false }
    if ($caseName -eq 'nonzero' -and -not $expectedWorkerExit) { $corePass = $false }
    if ($caseName -eq 'overflow' -and -not $overflowControl) { $corePass = $false }
    if (-not $corePass) { $allPass = $false }
    $caseResults += [ordered]@{
        case = $caseName
        recomputed_expected_status = $expect.status
        recomputed_expected_reason = $expect.reason
        observed_status = $s.status
        observed_reason = $s.failure_reason
        controller_exit = $r.controller_exit_code
        controller_pid = $r.controller_pid
        controller_pid_absent_after_wait = $r.controller_pid_absent_after_wait
        worker_pids = $pids
        worker_pid_absence_recorded = $r.worker_pids_absent_after_cleanup
        worker_pids_absent_at_verification_time = $currentPidsAbsent
        worker_exit_codes = @($workers | ForEach-Object { $_.exit_code })
        assigned_and_resumed = @($workers | ForEach-Object { $_.assigned -and $_.resumed })
        job_active_count = $s.job_active_count
        drain_proof = $s.drain_proof
        restart_matches = $r.restart_matches
        restart_commit_verified = $r.restart_commit_verified
        whole_tree_certificate = $s.whole_tree_certificate
        natural_marker_parity = if ($caseName -eq 'natural') { $naturalMarkers } else { 'NOT_APPLICABLE' }
        overflow_limit_control = if ($caseName -eq 'overflow') { $overflowControl } else { 'NOT_APPLICABLE' }
        recorded_accepted_type = $r.accepted.GetType().Name
        recorded_accepted_value_used_for_verdict = $false
        independently_recomputed_case_pass = $corePass
    }
}

$driverAbsentNow = Is-Absent ([int]$outer.driver_pid)
$outerPass = ($outer.authorization -eq 'ROOT_ADMITTED_FIVE_FIXED_NATIVE_CPU_FIXTURES' -and
    $outer.driver_exit_code -eq 0 -and $outer.driver_finished -eq $true -and
    $outer.driver_drained -eq $true -and $outer.driver_pid_absent_after_wait -eq $true -and
    $driverAbsentNow -and $outer.streams_within_cap -eq $true -and
    $outer.input_hashes_unchanged -eq $true -and $outer.input_hashes_before.source -eq $expectedSource -and
    $outer.input_hashes_after.source -eq $expectedSource)
$allPass = $allPass -and $outerPass -and ($caseResults.Count -eq 5)
$receipt = [ordered]@{
    status = if ($allPass) { 'ROOT_REVIEW_READY_FIVE_NATIVE_CASES_MET' } else { 'NATIVE_CASE_REVIEW_FAIL_OR_INCOMPLETE' }
    classification = 'NATIVE_CPU_FIXTURE_ONLY_NOT_PRODUCTION_ADMISSION'
    root_admission_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $taskDir 'ROOT_NATIVE_FIXTURE_ADMISSION.json')).Hash.ToLowerInvariant()
    source_sha256 = $expectedSource
    driver_sha256 = $expectedDriver
    controller_sha256 = $expectedController
    worker_sha256 = $expectedWorker
    interpreter_sha256 = $expectedPython
    driver_outer = [ordered]@{
        pid = $outer.driver_pid
        current_absent = $driverAbsentNow
        elapsed_seconds = $outer.elapsed_seconds
        exit_code = $outer.driver_exit_code
        stdout_bytes = $outer.stdout_bytes
        stderr_bytes = $outer.stderr_bytes
        source_runtime_pins_unchanged = $outer.input_hashes_unchanged
    }
    cases = $caseResults
    note = 'The driver accepted field is recorded only by JSON type. Verdict is independently recomputed from each raw case receipt; list-valued accepted fields were not coerced.'
    limitations = @('point-in-time PID checks only','whole_tree_certificate remains false','resource high-water unmeasured','no build, GPU, provider, or global queue admission')
}
$jsonPath = Join-Path $taskDir 'native_fixture_prepared\qualification_review_ready.json'
$mdPath = Join-Path $taskDir 'native_fixture_prepared\qualification_review_ready.md'
[System.IO.File]::WriteAllText($jsonPath, ($receipt | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
$lines = @(
    '# Build-policy supervisor native fixture — root review data',
    '',
    ('Status: `{0}`.' -f $receipt.status),
    'This records the root-admitted five-case CPU-only fixture. It is not production admission.',
    '',
    '| Case | Status / reason | Worker exits | Assigned/resumed | Job active | Drain | Restart | PIDs absent | Recomputed |',
    '|---|---|---|---|---:|---|---|---|---|'
)
foreach ($case in $caseResults) {
    $lines += ('| {0} | {1} / {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} |' -f $case.case,$case.observed_status,$case.observed_reason,(@($case.worker_exit_codes) -join ','),(@($case.assigned_and_resumed) -join ','),$case.job_active_count,$case.drain_proof,$case.restart_matches,($case.worker_pids_absent_at_verification_time -and $case.controller_pid_absent_after_wait),$case.independently_recomputed_case_pass)
}
$lines += @('', 'Worker PIDs were also rechecked after the run using process enumeration; this is a point-in-time absence check. `whole_tree_certificate` remains false. Driver `accepted` values were not used as proof; raw case conditions were recomputed independently.', '', 'The overflow control observed `LOG_LIMIT` with 1,024 captured stdout bytes and overflow flagged; the worker exited 1 after the bounded pipe closed. This is recorded as an observed fixture side effect, not normalized to exit 0.')
[System.IO.File]::WriteAllLines($mdPath, $lines, [System.Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 10
if (-not $allPass) { exit 1 }
