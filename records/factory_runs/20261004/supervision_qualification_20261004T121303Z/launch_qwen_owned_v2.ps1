$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$jobs=@(@('supervisor_v2','qwen3.8-max','contained_supervisor.py'),@('validator_v2','qwen3.8-flash','qualification_validator.py'))
$owned=@()
try{
 foreach($j in $jobs){$si=[Diagnostics.ProcessStartInfo]::new((Get-Command pwsh).Source);$si.WorkingDirectory=$root;$si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
 foreach($a in @('-NoProfile','-File',(Join-Path $root 'provider_job_v2.ps1'),'-Job',$j[0],'-Model',$j[1],'-Artifact',$j[2])){$si.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::new();$p.StartInfo=$si;$watch=[Diagnostics.Stopwatch]::StartNew();$p.Start()|Out-Null
 $owned+=@{job=$j[0];model=$j[1];process=$p;clock=$watch;stdout=$p.StandardOutput.ReadToEndAsync();stderr=$p.StandardError.ReadToEndAsync();killed=$false;finished=$false}
 }
 @($owned|ForEach-Object {@{job=$_.job;model=$_.model;pid=$_.process.Id;observed_process_start_utc=$_.process.StartTime.ToUniversalTime().ToString('o');outer_deadline_seconds=270;identity='retained System.Diagnostics.Process handle; no PID lookup';clock='Stopwatch monotonic'}})|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'qwen_owned_launches_v2.json')
 while(@($owned|Where-Object {!$_.finished}).Count){foreach($o in $owned){if($o.finished){continue};if(!$o.process.HasExited-and$o.clock.Elapsed.TotalSeconds-ge270){$o.process.Kill($true);$o.killed=$true};if($o.process.WaitForExit(0)){$o.process.WaitForExit();$out=$o.stdout.GetAwaiter().GetResult();$err=$o.stderr.GetAwaiter().GetResult();$overflow=$out.Length-gt1048576-or$err.Length-gt1048576;if($out.Length-gt1048576){$out=$out.Substring(0,1048576)};if($err.Length-gt1048576){$err=$err.Substring(0,1048576)};$out|Set-Content -LiteralPath (Join-Path $root ($o.job+'.launcher_stdout.txt'));$err|Set-Content -LiteralPath (Join-Path $root ($o.job+'.launcher_stderr.txt'));@{job=$o.job;pid=$o.process.Id;exit_code=$o.process.ExitCode;seconds=[math]::Round($o.clock.Elapsed.TotalSeconds,2);outer_killed=$o.killed;log_overflow=$overflow;identity='retained process object'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root ($o.job+'.outer_terminal.json'));$o.finished=$true}};Start-Sleep -Milliseconds 500}
}finally{foreach($o in $owned){if(!$o.process.HasExited){$o.process.Kill($true);$o.process.WaitForExit()};$o.process.Dispose()}}

