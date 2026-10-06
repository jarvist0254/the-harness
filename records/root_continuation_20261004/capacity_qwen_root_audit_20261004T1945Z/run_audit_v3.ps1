$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=$PSScriptRoot
$python='C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
$test=Join-Path $root 'capacity_independent_audit_v3.py'
$source='E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\qwen_four_capacity\source.qwen_untrusted.py'
$expectedSource='7005C1FC83A4A9901E30CF8E705DBE5961DC1010C645E963BB08EC75A7808267'
$expectedTest='440245BF69E5FDE1F2D68C94797F971C068D2D3A87FFE6DA5E0AFD2DE394329E'
$pythonHash=(Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToUpperInvariant()
$sourceBefore=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToUpperInvariant()
$testBefore=(Get-FileHash -LiteralPath $test -Algorithm SHA256).Hash.ToUpperInvariant()
if($sourceBefore -ne $expectedSource -or $testBefore -ne $expectedTest){throw 'prelaunch source/test pin mismatch'}
$psi=[Diagnostics.ProcessStartInfo]::new()
$psi.FileName=$python
$psi.WorkingDirectory=$root
$psi.UseShellExecute=$false
$psi.CreateNoWindow=$true
$psi.RedirectStandardOutput=$true
$psi.RedirectStandardError=$true
[void]$psi.ArgumentList.Add($test)
[void]$psi.ArgumentList.Add($source)
$proc=[Diagnostics.Process]::new();$proc.StartInfo=$psi
$sw=[Diagnostics.Stopwatch]::StartNew();$started=$false;$killed=$false;$unknown=$false;$exitCode=$null;$stdout='';$stderr=''
try{
 [void]$proc.Start();$started=$true
 $pidOwned=$proc.Id
 $outTask=$proc.StandardOutput.ReadToEndAsync()
 $errTask=$proc.StandardError.ReadToEndAsync()
 while(!$proc.HasExited -and $sw.Elapsed.TotalSeconds -lt 30){Start-Sleep -Milliseconds 100}
 if(!$proc.HasExited){$proc.Kill($true);$killed=$true;if(!$proc.WaitForExit(5000)){$unknown=$true}}
 if($proc.HasExited){$exitCode=$proc.ExitCode}else{$unknown=$true}
 try{$stdout=$outTask.GetAwaiter().GetResult()}catch{$unknown=$true}
 try{$stderr=$errTask.GetAwaiter().GetResult()}catch{$unknown=$true}
}catch{$stderr=$_.Exception.ToString()}
finally{if($started -and !$proc.HasExited){try{$proc.Kill($true);$killed=$true;if(!$proc.WaitForExit(5000)){$unknown=$true}}catch{$unknown=$true}}}
$stdoutBytes=[Text.Encoding]::UTF8.GetByteCount($stdout);$stderrBytes=[Text.Encoding]::UTF8.GetByteCount($stderr)
[IO.File]::WriteAllText((Join-Path $root 'stdout.attempt3.raw.json'),$stdout,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'stderr.attempt3.raw.log'),$stderr,[Text.UTF8Encoding]::new($false))
$sourceAfter=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToUpperInvariant()
$testAfter=(Get-FileHash -LiteralPath $test -Algorithm SHA256).Hash.ToUpperInvariant()
$pythonAfter=(Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToUpperInvariant()
$pidAbsent=$true
if($started){try{Get-Process -Id $pidOwned -ErrorAction Stop|Out-Null;$pidAbsent=$false}catch{$pidAbsent=$true}}
$status='FAIL'
if($exitCode -eq 0 -and !$killed -and !$unknown -and $stdoutBytes -le 2097152 -and $stderrBytes -le 2097152 -and $sourceAfter -eq $expectedSource -and $testAfter -eq $expectedTest -and $pythonAfter -eq $pythonHash -and $pidAbsent){$status='COMPLETED'}
$receipt=[ordered]@{status=$status;pid=if($started){$pidOwned}else{$null};exit_code=$exitCode;elapsed_seconds=[math]::Round($sw.Elapsed.TotalSeconds,4);timeout_seconds=30;owned_process_killed=$killed;drain_unknown=$unknown;pid_absent_after=$pidAbsent;stdout_bytes=$stdoutBytes;stderr_bytes=$stderrBytes;stdout_sha256=(Get-FileHash -LiteralPath (Join-Path $root 'stdout.attempt3.raw.json') -Algorithm SHA256).Hash.ToUpperInvariant();stderr_sha256=(Get-FileHash -LiteralPath (Join-Path $root 'stderr.attempt3.raw.log') -Algorithm SHA256).Hash.ToUpperInvariant();stream_cap_bytes=2097152;source_sha256_before=$sourceBefore;source_sha256_after=$sourceAfter;test_sha256_before=$testBefore;test_sha256_after=$testAfter;python_path=$python;python_sha256_before=$pythonHash;python_sha256_after=$pythonAfter;candidate_execution='pure validator import/calls only';native_calls=0;gpu_calls=0;provider_calls=0}
$rp=Join-Path $root 'run_receipt_attempt3.json';[IO.File]::WriteAllText($rp,($receipt|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false));$proc.Dispose();Get-Content -LiteralPath $rp
if($status -ne 'COMPLETED'){exit 2}
