param(
    [Parameter(Mandatory=$true)][string]$AdmissionPath,
    [Parameter(Mandatory=$true)][string]$AdmissionSha256
)
$ErrorActionPreference = 'Stop'
$root='E:\the_harness'
$source=Join-Path $root 'records\factory_runs\20261004\l0_compiler_two_prep_v2_20261004T214600Z\qwen_l0_query_measured_repair\source.qwen_untrusted.cpp'
$test=Join-Path $PSScriptRoot 'cpu_fake_contract_v2_pending_root_gate.cpp'
$header=Join-Path $root 'records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h'
$exe=Join-Path $PSScriptRoot 'cpu_fake_contract_v2.exe'
$stdout=Join-Path $PSScriptRoot 'compile.stdout.txt'
$stderr=Join-Path $PSScriptRoot 'compile.stderr.txt'
$receiptPath=Join-Path $PSScriptRoot 'compile_receipt.json'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
if((Sha $source) -ne '27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2'){throw 'candidate hash mismatch'}
if((Sha $test) -ne '9c20b97392dc2b2d076021c6c1e38ceb0c67c12ebd0f0e79acf8a07521f3ab5'){throw 'CPU fake v2 contract hash mismatch'}
if((Sha $header) -ne 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'){throw 'official header hash mismatch'}
if((Sha $AdmissionPath) -ne $AdmissionSha256.ToLowerInvariant()){throw 'admission file hash mismatch'}
$admission=Get-Content -LiteralPath $AdmissionPath -Raw | ConvertFrom-Json
if($admission.action -ne 'CPU_FAKE_COMPILE_LINK_ONLY' -or $admission.candidate_sha256 -ne (Sha $source) -or $admission.contract_sha256 -ne (Sha $test) -or $admission.header_sha256 -ne (Sha $header)){throw 'admission scope or pins mismatch'}
foreach($p in @($exe,$stdout,$stderr,$receiptPath)){if(Test-Path -LiteralPath $p){throw "refuse overwrite: $p"}}
$compilerInfo=(& wsl.exe --exec /usr/bin/sha256sum /usr/bin/c++ 2>&1 | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $compilerInfo -notmatch '^1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769\s+/usr/bin/c\+\+$'){throw 'compiler binary pin mismatch'}
$compilerVersion=(& wsl.exe --exec /usr/bin/c++ --version 2>&1 | Select-Object -First 1).Trim()
if($LASTEXITCODE -ne 0 -or $compilerVersion -ne 'c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0'){throw 'compiler version mismatch'}
$testWsl='/mnt/e/the_harness/records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/cpu_fake_contract_v2_pending_root_gate.cpp'
$sourceWsl='/mnt/e/the_harness/records/factory_runs/20261004/l0_compiler_two_prep_v2_20261004T214600Z/qwen_l0_query_measured_repair/source.qwen_untrusted.cpp'
$headerWsl='/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include/level_zero'
$exeWsl='/mnt/e/the_harness/records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/cpu_fake_contract_v2.exe'
$macro='-DLZQ_ACTUAL_SOURCE_PATH="'+$sourceWsl+'"'
$argv=@('--exec','/usr/bin/timeout','--signal=TERM','--kill-after=5s','85s','/usr/bin/c++','-std=c++17','-Wall','-Wextra','-I',$headerWsl,$macro,$testWsl,'-o',$exeWsl)
$start=[DateTime]::UtcNow; $timer=[Diagnostics.Stopwatch]::StartNew()
$proc=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\wsl.exe') -ArgumentList $argv -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
$ownedPid=$proc.Id; $done=$proc.WaitForExit(90000); $outerKilled=$false
if(-not $done){$outerKilled=$true; try{$proc.Kill()}catch{}; [void]$proc.WaitForExit(5000)}
$timer.Stop(); $alive=$false; try{$null=Get-Process -Id $ownedPid -ErrorAction Stop;$alive=$true}catch{}
$pinsUnchanged=((Sha $source) -eq '27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2') -and ((Sha $test) -eq '9c20b97392dc2b2d076021c6c1e38ceb0c67c12ebd0f0e79acf8a07521f3ab5') -and ((Sha $header) -eq 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de')
$code=if($proc.HasExited){$proc.ExitCode}else{$null}; $exists=Test-Path -LiteralPath $exe -PathType Leaf
$status=if($done -and -not $outerKilled -and $code -eq 0 -and $pinsUnchanged -and -not $alive -and $exists){'CPU_FAKE_COMPILE_LINK_PASS_NOT_EXECUTED'}elseif(-not $done -or $outerKilled){'CPU_FAKE_COMPILE_TIMEOUT'}else{'CPU_FAKE_COMPILE_LINK_FAIL'}
$receipt=[ordered]@{status=$status;scope='CPU_SYNTHETIC_STUB_COMPILE_LINK_ONLY_NO_EXECUTION_NO_LEVEL_ZERO_LOADER';argv=@('wsl.exe')+$argv;candidate_sha256=(Sha $source);contract_sha256=(Sha $test);header_sha256=(Sha $header);admission_sha256=$AdmissionSha256.ToLowerInvariant();pins_unchanged=$pinsUnchanged;owned_wsl_pid=$ownedPid;owned_wsl_exited=[bool]$proc.HasExited;owned_wsl_pid_present_at_check=$alive;outer_killed_owned_wsl=$outerKilled;elapsed_seconds=[math]::Round($timer.Elapsed.TotalSeconds,3);outer_timeout_seconds=90;wsl_timeout_seconds=85;exit_code=$code;binary_path=$exe;binary_bytes=if($exists){(Get-Item -LiteralPath $exe).Length}else{0};stdout_path=$stdout;stdout_sha256=(Sha $stdout);stdout_bytes=(Get-Item -LiteralPath $stdout).Length;stderr_path=$stderr;stderr_sha256=(Sha $stderr);stderr_bytes=(Get-Item -LiteralPath $stderr).Length;binary_executed=$false;level_zero_runtime_calls=$false;native_gpu_calls=$false}
[IO.File]::WriteAllText($receiptPath,($receipt|ConvertTo-Json -Depth 6)+"`n",[Text.UTF8Encoding]::new($false))
$receipt|ConvertTo-Json -Depth 6
if($status -ne 'CPU_FAKE_COMPILE_LINK_PASS_NOT_EXECUTED'){exit 1}
$compilerVersion=(& wsl.exe --exec /usr/bin/c++ --version 2>&1 | Select-Object -First 1).Trim()
if($LASTEXITCODE -ne 0 -or $compilerVersion -ne 'c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0'){throw 'compiler version mismatch'}
$testWsl='/mnt/e/the_harness/records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/cpu_fake_contract_v2_pending_root_gate.cpp'
$headerWsl='/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include/level_zero'
$exeWsl='/mnt/e/the_harness/records/root_continuation_20261004/l0_query_measured_repair_cpu_fake_v2_20261004T2305Z/cpu_fake_contract_v2.exe'
$macro='-DLZQ_ACTUAL_SOURCE_PATH="'+$sourceWsl+'"'
$argv=@('--exec','/usr/bin/timeout','--signal=TERM','--kill-after=5s','85s','/usr/bin/c++','-std=c++17','-Wall','-Wextra','-I',$headerWsl,$macro,$testWsl,'-o',$exeWsl)
$start=[DateTime]::UtcNow; $timer=[Diagnostics.Stopwatch]::StartNew()
$proc=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\wsl.exe') -ArgumentList $argv -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
$ownedPid=$proc.Id; $done=$proc.WaitForExit(90000); $outerKilled=$false
if(-not $done){$outerKilled=$true; try{$proc.Kill()}catch{}; [void]$proc.WaitForExit(5000)}
$timer.Stop(); $alive=$false; try{$null=Get-Process -Id $ownedPid -ErrorAction Stop;$alive=$true}catch{}
$pinsUnchanged=((Sha $source) -eq '27d560b3f73dd830b68de9aac3316d7b8510c0218d54704156e273929ce23fe2') -and ((Sha $test) -eq '9c20b97392dc2b2d076021c6c1e38ceb0c67c12ebd0f0e79acf8a07521f3ab5') -and ((Sha $header) -eq 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de')
$code=if($proc.HasExited){$proc.ExitCode}else{$null}; $exists=Test-Path -LiteralPath $exe -PathType Leaf
$status=if($done -and -not $outerKilled -and $code -eq 0 -and $pinsUnchanged -and -not $alive -and $exists){'CPU_FAKE_COMPILE_LINK_PASS_NOT_EXECUTED'}elseif(-not $done -or $outerKilled){'CPU_FAKE_COMPILE_TIMEOUT'}else{'CPU_FAKE_COMPILE_LINK_FAIL'}
$receipt=[ordered]@{status=$status;scope='CPU_SYNTHETIC_STUB_COMPILE_LINK_ONLY_NO_EXECUTION_NO_LEVEL_ZERO_LOADER';argv=@('wsl.exe')+$argv;candidate_sha256=(Sha $source);contract_sha256=(Sha $test);header_sha256=(Sha $header);admission_sha256=$AdmissionSha256.ToLowerInvariant();pins_unchanged=$pinsUnchanged;owned_wsl_pid=$ownedPid;owned_wsl_exited=[bool]$proc.HasExited;owned_wsl_pid_present_at_check=$alive;outer_killed_owned_wsl=$outerKilled;elapsed_seconds=[math]::Round($timer.Elapsed.TotalSeconds,3);outer_timeout_seconds=90;wsl_timeout_seconds=85;exit_code=$code;binary_path=$exe;binary_bytes=if($exists){(Get-Item -LiteralPath $exe).Length}else{0};stdout_path=$stdout;stdout_sha256=(Sha $stdout);stdout_bytes=(Get-Item -LiteralPath $stdout).Length;stderr_path=$stderr;stderr_sha256=(Sha $stderr);stderr_bytes=(Get-Item -LiteralPath $stderr).Length;binary_executed=$false;level_zero_runtime_calls=$false;native_gpu_calls=$false}
[IO.File]::WriteAllText($receiptPath,($receipt|ConvertTo-Json -Depth 6)+"`n",[Text.UTF8Encoding]::new($false))
$receipt|ConvertTo-Json -Depth 6
if($status -ne 'CPU_FAKE_COMPILE_LINK_PASS_NOT_EXECUTED'){exit 1}
