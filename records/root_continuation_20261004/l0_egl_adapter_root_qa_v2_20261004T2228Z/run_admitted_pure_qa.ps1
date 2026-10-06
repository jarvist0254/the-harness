$ErrorActionPreference = 'Stop'
$root = 'E:\the_harness'
$folder = Join-Path $root 'records\root_continuation_20261004\l0_egl_adapter_root_qa_v2_20261004T2228Z'
$controller = Join-Path $folder 'pure_qa_controller_v2.py'
$tests = Join-Path $folder 'test_adapter_independent_contract_v2.py'
$source = Join-Path $root 'records\factory_runs\20261004\l0_egl_sync_bridge_two_prep_20261004T212837Z\qwen_l0_egl_fence_adapter\source.qwen_untrusted.py'
$providerTests = Join-Path $root 'records\factory_runs\20261004\l0_egl_sync_bridge_two_prep_20261004T212837Z\qwen_l0_egl_fence_adapter\tests_source.qwen_untrusted.txt'
$python = 'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
$admission = Join-Path $folder 'ROOT_PURE_QA_ADMISSION_V2.json'
$sha = { param([string]$path) (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$expected = @{}
$expected[$source] = '99375e8072f22a7103517e0772f327b232dd3134f1f6820039a42a55f37c017c'
$expected[$providerTests] = '0e4372f0c706c2e7f9b5ba8354b4e46b7c70649b2f585e8824ab1c8598014491'
$expected[$tests] = 'eaecf21e7bdd43763b84b74d4d688bab720490e55fae9207b5358ccfb8ff79f2'
$expected[$controller] = '00200b8f71a3677bd79e6b6750b532df7bb420c158324f2d772b96142ecc8002'
$expected[$python] = '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
$expected[$admission] = '22163230760f602e9a9ba1dc7a397a061f05b92093a47f7bed9c910b02fddd0c'
foreach ($path in $expected.Keys) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "missing pinned file: $path" }
    if ((& $sha $path) -ne $expected[$path]) { throw "pin mismatch: $path" }
}
$runDir = Join-Path $folder 'runs\outer_20261004T2240Z'
New-Item -ItemType Directory -Path $runDir | Out-Null
$stdout = Join-Path $runDir 'controller.stdout.bin'
$stderr = Join-Path $runDir 'controller.stderr.bin'
$receiptPath = Join-Path $runDir 'outer_receipt.json'
$argv = @('-I','-B',$controller,'--admission-sha256',$expected[$admission])
$start = [DateTime]::UtcNow
$timer = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $python -ArgumentList $argv -WorkingDirectory $root -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
$ownedPid = $proc.Id
$outerTimeout = $false
$streamOverflow = $false
while (-not $proc.HasExited) {
    $stdoutBytes = if (Test-Path -LiteralPath $stdout) { (Get-Item -LiteralPath $stdout).Length } else { 0 }
    $stderrBytes = if (Test-Path -LiteralPath $stderr) { (Get-Item -LiteralPath $stderr).Length } else { 0 }
    if ($stdoutBytes -gt 131072 -or $stderrBytes -gt 131072) {
        $streamOverflow = $true
        try { $proc.Kill() } catch {}
        break
    }
    if ($timer.Elapsed.TotalSeconds -ge 40) {
        $outerTimeout = $true
        try { $proc.Kill() } catch {}
        break
    }
    Start-Sleep -Milliseconds 100
}
[void]$proc.WaitForExit(5000)
$timer.Stop()
$pidPresent = $false
try { $null = Get-Process -Id $ownedPid -ErrorAction Stop; $pidPresent = $true } catch {}
$exitCode = if ($proc.HasExited) { $proc.ExitCode } else { $null }
$pinsAfter = @{}
$pinsUnchanged = $true
foreach ($path in $expected.Keys) {
    $pinsAfter[$path] = & $sha $path
    if ($pinsAfter[$path] -ne $expected[$path]) { $pinsUnchanged = $false }
}
$stdoutBytes = (Get-Item -LiteralPath $stdout).Length
$stderrBytes = (Get-Item -LiteralPath $stderr).Length
$stdoutText = if ($stdoutBytes -le 131072) { Get-Content -Raw -LiteralPath $stdout } else { '' }
$childSummary = $null
if ($stdoutText) { try { $childSummary = $stdoutText | ConvertFrom-Json } catch {} }
$status = if ($outerTimeout) { 'OUTER_TIMEOUT_OWNED_CONTROLLER_KILLED' } elseif ($streamOverflow) { 'OUTER_STREAM_CAP_OWNED_CONTROLLER_KILLED' } elseif ($exitCode -eq 0 -and -not $pidPresent -and $pinsUnchanged) { 'CONTROLLER_EXIT_ZERO' } elseif ($exitCode -ne $null) { 'CONTROLLER_EXIT_NONZERO' } else { 'CONTROLLER_DRAIN_UNCERTAIN' }
$receipt = [ordered]@{
    status = $status
    command = @($python,'-I','-B',$controller,'--admission-sha256',$expected[$admission])
    admission_sha256 = $expected[$admission]
    pins_before = $expected
    pins_after = $pinsAfter
    pins_unchanged = $pinsUnchanged
    retained_controller_pid = $ownedPid
    process_handle_exited = [bool]$proc.HasExited
    pid_present_at_absence_check = $pidPresent
    exit_code = $exitCode
    outer_timeout_seconds = 40
    outer_timeout = $outerTimeout
    per_stream_cap_bytes = 131072
    stream_overflow = $streamOverflow
    elapsed_seconds = [Math]::Round($timer.Elapsed.TotalSeconds,3)
    started_utc = $start.ToString('o')
    stdout_path = $stdout
    stdout_sha256 = & $sha $stdout
    stdout_bytes = $stdoutBytes
    stderr_path = $stderr
    stderr_sha256 = & $sha $stderr
    stderr_bytes = $stderrBytes
    controller_stdout_json = $childSummary
    provider_tests_in_controller_command = $false
}
[IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 12) + "`n", [Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 6
if ($status -ne 'CONTROLLER_EXIT_ZERO') { exit 1 }
