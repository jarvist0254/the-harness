$ErrorActionPreference = 'Stop'
$root = 'E:\the_harness'
$outDir = Join-Path $root 'records\root_continuation_20261004\l0_query_measured_repair_object_qa_20261004T2228Z'
$source = Join-Path $root 'records\factory_runs\20261004\l0_compiler_two_prep_v2_20261004T214600Z\qwen_l0_query_measured_repair\source.qwen_untrusted.cpp'
$providerTests = Join-Path $root 'records\factory_runs\20261004\l0_compiler_two_prep_v2_20261004T214600Z\qwen_l0_query_measured_repair\tests_source.qwen_untrusted.txt'
$header = Join-Path $root 'records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h'
$expected = @{}
$expected[$source] = '27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2'
$expected[$providerTests] = 'df49c5aa406c27a9d1cee14ded78804ef95551a0eac703635c9268bb13f06ac8'
$expected[$header] = 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'
function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
foreach ($path in @($source, $providerTests, $header)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "missing pinned input: $path" }
    if ((Get-Sha256 $path) -ne $expected[$path]) { throw "input hash mismatch: $path" }
}
$compilerInfo = (& wsl.exe --exec /usr/bin/sha256sum /usr/bin/c++ 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $compilerInfo -notmatch '^1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769\s+/usr/bin/c\+\+$') { throw 'compiler binary pin mismatch' }
$compilerVersion = (& wsl.exe --exec /usr/bin/c++ --version 2>&1 | Select-Object -First 1).Trim()
if ($LASTEXITCODE -ne 0 -or $compilerVersion -ne 'c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0') { throw 'compiler version mismatch' }
$sourceWsl = '/mnt/e/the_harness/records/factory_runs/20261004/l0_compiler_two_prep_v2_20261004T214600Z/qwen_l0_query_measured_repair/source.qwen_untrusted.cpp'
$headerWsl = '/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include/level_zero'
$objectWsl = '/mnt/e/the_harness/records/root_continuation_20261004/l0_query_measured_repair_object_qa_20261004T2228Z/query_candidate.o'
$stdout = Join-Path $outDir 'compile.stdout.txt'
$stderr = Join-Path $outDir 'compile.stderr.txt'
$receiptPath = Join-Path $outDir 'compile_receipt.json'
foreach ($path in @($stdout, $stderr, $receiptPath, (Join-Path $outDir 'query_candidate.o'))) {
    if (Test-Path -LiteralPath $path) { throw "refusing to overwrite evidence/output: $path" }
}
$argv = @('--exec','/usr/bin/timeout','--signal=TERM','--kill-after=5s','85s','/usr/bin/c++','-std=c++17','-Wall','-Wextra','-I', $headerWsl, '-c', $sourceWsl, '-o', $objectWsl)
$started = [DateTime]::UtcNow
$timer = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\wsl.exe') -ArgumentList $argv -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
$ownedPid = $proc.Id
$completed = $proc.WaitForExit(90000)
$outerKilled = $false
if (-not $completed) {
    $outerKilled = $true
    try { $proc.Kill() } catch {}
    [void]$proc.WaitForExit(5000)
}
$timer.Stop()
$pinsAfter = @{}
foreach ($path in @($source, $providerTests, $header)) { $pinsAfter[$path] = Get-Sha256 $path }
$pinsBeforeAfterMatch = $true
foreach ($path in @($source, $providerTests, $header)) { if ($pinsAfter[$path] -ne $expected[$path]) { $pinsBeforeAfterMatch = $false } }
$alive = $false
try { $null = Get-Process -Id $ownedPid -ErrorAction Stop; $alive = $true } catch {}
$stdoutHash = Get-Sha256 $stdout
$stderrHash = Get-Sha256 $stderr
$exitCode = if ($proc.HasExited) { $proc.ExitCode } else { $null }
$objectPath = Join-Path $outDir 'query_candidate.o'
$objectExists = Test-Path -LiteralPath $objectPath -PathType Leaf
$status = if ($completed -and -not $outerKilled -and $exitCode -eq 0 -and $pinsBeforeAfterMatch -and -not $alive -and $objectExists) { 'OBJECT_COMPILE_PASS' } elseif (-not $completed -or $outerKilled) { 'OBJECT_COMPILE_TIMEOUT_OUTER_KILLED_OWNED_WSL' } else { 'OBJECT_COMPILE_FAIL' }
$receipt = [ordered]@{
    status = $status
    scope = 'CXX_OBJECT_ONLY_NO_LINK_NO_EXECUTION_NO_PROVIDER_TESTS'
    argv = @('wsl.exe','--exec','/usr/bin/timeout','--signal=TERM','--kill-after=5s','85s','/usr/bin/c++','-std=c++17','-Wall','-Wextra','-I',$headerWsl,'-c',$sourceWsl,'-o',$objectWsl)
    compiler = $compilerVersion
    compiler_sha256 = '1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769'
    source_path = $source; source_sha256_before = $expected[$source]; source_sha256_after = $pinsAfter[$source]
    provider_tests_path = $providerTests; provider_tests_sha256_before = $expected[$providerTests]; provider_tests_sha256_after = $pinsAfter[$providerTests]; provider_tests_executed = $false
    header_path = $header; header_sha256_before = $expected[$header]; header_sha256_after = $pinsAfter[$header]
    pins_unchanged = $pinsBeforeAfterMatch
    outer_wsl_pid = $ownedPid; outer_wsl_exited = [bool]$proc.HasExited; outer_wsl_still_present_at_check = $alive; outer_killed_owned_wsl = $outerKilled
    outer_elapsed_seconds = [math]::Round($timer.Elapsed.TotalSeconds,3); started_utc = $started.ToString('o'); wsl_timeout_seconds = 85; outer_timeout_seconds = 90
    exit_code = $exitCode; object_path = $objectPath; object_exists = $objectExists; object_bytes = if ($objectExists) { (Get-Item -LiteralPath $objectPath).Length } else { 0 }
    stdout_path = $stdout; stdout_sha256 = $stdoutHash; stdout_bytes = (Get-Item -LiteralPath $stdout).Length
    stderr_path = $stderr; stderr_sha256 = $stderrHash; stderr_bytes = (Get-Item -LiteralPath $stderr).Length
    candidate_executed = $false; level_zero_runtime_calls = $false; native_gpu_calls = $false
}
$json = $receipt | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($receiptPath, $json + "`n", [Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 4
if ($status -ne 'OBJECT_COMPILE_PASS') { exit 1 }
