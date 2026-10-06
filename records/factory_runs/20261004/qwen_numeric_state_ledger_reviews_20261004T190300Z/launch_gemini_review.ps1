param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = $PSScriptRoot
$agy = 'C:\Users\thoma\AppData\Local\agy\bin\agy.exe'
$promptPath = Join-Path $root 'gemini_prompt.txt'
$schemaPath = Join-Path $root 'gemini_schema.json'
$inputsPath = Join-Path $root 'inputs.json'
$sourceHash = '6DFB6A72A1310D23CF435C73F32DCD0B6A57B85CEF774C9A47C8748CE3E68DC1'
$promptHash = '29EE001AB9446917FD24C213DDD88819C79F952371E661ED517EBF71A228B793'
$schemaHash = (Get-FileHash -LiteralPath $schemaPath -Algorithm SHA256).Hash.ToUpperInvariant()
$inputMap = Get-Content -LiteralPath $inputsPath -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $root 'candidate.snapshot.py') -Algorithm SHA256).Hash -ne $sourceHash) { throw 'candidate source pin mismatch' }
if ((Get-FileHash -LiteralPath $promptPath -Algorithm SHA256).Hash -ne $promptHash) { throw 'prompt pin mismatch' }
if ((Get-Item -LiteralPath $promptPath).Length -gt 262144) { throw 'prompt exceeds 256 KiB' }
if (!(Test-Path -LiteralPath $agy -PathType Leaf)) { throw 'pinned agy executable missing' }
$agyHash = (Get-FileHash -LiteralPath $agy -Algorithm SHA256).Hash.ToUpperInvariant()
$before = [ordered]@{}
foreach ($item in $inputMap.PSObject.Properties) {
    if ($null -eq $item.Value.PSObject.Properties['original']) { continue }
    $sourcePath = [string]$item.Value.original
    $expectedHash = [string]$item.Value.sha256
    if (!(Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "input missing: $($item.Name)" }
    $actual = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($actual -ne $expectedHash) { throw "input pin mismatch: $($item.Name)" }
    $before[$sourcePath] = $actual
}
$localPins = [ordered]@{
    'candidate.snapshot.py' = $sourceHash
    'gemini_prompt.txt' = $promptHash
    'gemini_schema.json' = $schemaHash
    'inputs.json' = (Get-FileHash -LiteralPath $inputsPath -Algorithm SHA256).Hash.ToUpperInvariant()
    'agy.exe' = $agyHash
}
$admission = [ordered]@{
    authority = 'ROOT-delegated isolated provider-only code review; no source mutation or execution'
    lane = 'Gemini'
    model = 'gemini-3.8-flash-high'
    source_sha256 = $sourceHash
    prompt_sha256 = $promptHash
    schema_sha256 = $schemaHash
    exact_inputs = $before
    local_pins = $localPins
    limits = @{ deadline_seconds = 240; captured_bytes_per_stream = 2097152; max_prompt_bytes = 262144 }
    tools_requested = 'none; source context fully embedded'
    source_execution = $false
    provider_edit = $false
}
$admissionPath = Join-Path $root 'ROOT_GEMINI_REVIEW_ADMISSION.json'
if (Test-Path -LiteralPath $admissionPath) { throw 'immutable admission already exists' }
[IO.File]::WriteAllText($admissionPath,($admission | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
$psi = [Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $agy
$psi.WorkingDirectory = $root
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
foreach ($arg in @('--model','gemini-3.8-flash-high','--mode','plan','--sandbox','--new-project','--disable-slash-commands','--output-format','json','--print-timeout','210s','--json-schema',$schemaPath,'--print',[IO.File]::ReadAllText($promptPath))) { [void]$psi.ArgumentList.Add($arg) }
$proc = [Diagnostics.Process]::new()
$proc.StartInfo = $psi
$sw = [Diagnostics.Stopwatch]::StartNew()
$cts = [Threading.CancellationTokenSource]::new()
$streams = @()
$tasks = @($null,$null)
$mem = @([IO.MemoryStream]::new(),[IO.MemoryStream]::new())
$buf = @([byte[]]::new(16384),[byte[]]::new(16384))
$done = @($false,$false)
$started = $false
$outerKilled = $false
$capExceeded = $false
$drainUnknown = $false
$pipeError = $false
$exitCode = $null
$lastBeat = 0.0
$state = 'NOT_ACCEPTED'
$usage = 'UNKNOWN'
$modelUsage = 'UNKNOWN'
$parseError = $null
try {
    [void]$proc.Start()
    $started = $true
    [IO.File]::WriteAllText((Join-Path $root 'gemini_launch.json'),(@{model='gemini-3.8-flash-high';pid=$proc.Id;start_utc=$proc.StartTime.ToUniversalTime().ToString('o');source_sha256=$sourceHash;prompt_sha256=$promptHash;schema_sha256=$schemaHash;agy_sha256=$agyHash;deadline_seconds=240;per_stream_cap_bytes=2097152;execution=$false;provider_edit=$false}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $streams = @($proc.StandardOutput.BaseStream,$proc.StandardError.BaseStream)
    for ($i=0; $i -lt 2; $i++) { $tasks[$i] = $streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token) }
    while ($true) {
        if (!$proc.HasExited -and ($sw.Elapsed.TotalSeconds -ge 240 -or $capExceeded)) {
            $proc.Kill($true)
            $outerKilled = $true
        }
        for ($i=0; $i -lt 2; $i++) {
            if ($done[$i] -or !$tasks[$i].IsCompleted) { continue }
            try { $n = $tasks[$i].GetAwaiter().GetResult() } catch { $pipeError=$true; $done[$i]=$true; continue }
            if ($n -eq 0) { $done[$i]=$true; continue }
            $room = 2097152 - [int]$mem[$i].Length
            if ($n -gt $room) {
                if ($room -gt 0) { $mem[$i].Write($buf[$i],0,$room) }
                $capExceeded = $true
                $done[$i] = $true
            } else {
                $mem[$i].Write($buf[$i],0,$n)
                $tasks[$i] = $streams[$i].ReadAsync($buf[$i],0,$buf[$i].Length,$cts.Token)
            }
        }
        if ($proc.HasExited) {
            if ($done[0] -and $done[1]) { break }
            if ($sw.Elapsed.TotalSeconds -ge 245) { $drainUnknown=$true; break }
        }
        if ($sw.Elapsed.TotalSeconds -ge 240 -and $proc.HasExited) { $drainUnknown=$true; break }
        if ($sw.Elapsed.TotalSeconds - $lastBeat -ge 15) {
            $lastBeat=$sw.Elapsed.TotalSeconds
            @{utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=[math]::Round($lastBeat,1);pid=$proc.Id;status='RUNNING';stdout_bytes=$mem[0].Length;stderr_bytes=$mem[1].Length}|ConvertTo-Json -Compress|Add-Content -LiteralPath (Join-Path $root 'gemini_progress.jsonl')
        }
        Start-Sleep -Milliseconds 100
    }
    if ($proc.HasExited) { $exitCode=$proc.ExitCode } else { $drainUnknown=$true }
} catch {
    $pipeError=$true
    $parseError=$_.Exception.GetType().Name
} finally {
    if ($started -and !$proc.HasExited) {
        try { $proc.Kill($true); $outerKilled=$true; if (!$proc.WaitForExit(5000)) { $drainUnknown=$true } } catch { $drainUnknown=$true }
    }
    $cts.Cancel()
    foreach ($s in $streams) { if ($s) { $s.Dispose() } }
    $cts.Dispose()
    $stdout=[Text.Encoding]::UTF8.GetString($mem[0].ToArray())
    $stderr=[Text.Encoding]::UTF8.GetString($mem[1].ToArray())
    foreach ($m in $mem) { $m.Dispose() }
}
$privateUrl = ($stdout -match 'https?://[^\s"<>]*[?@]' -or $stderr -match 'https?://[^\s"<>]*[?@]')
$stdoutBytes = [Text.Encoding]::UTF8.GetByteCount($stdout)
$stderrBytes = [Text.Encoding]::UTF8.GetByteCount($stderr)
$stdoutHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($stdout)))
$stderrHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($stderr)))
if ($privateUrl) { $stdout='REFUSED_PRIVATE_URL_OUTPUT'; $stderr='REFUSED_PRIVATE_URL_OUTPUT' }
[IO.File]::WriteAllText((Join-Path $root 'gemini_stdout.json'),$stdout,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'gemini_stderr.txt'),$stderr,[Text.UTF8Encoding]::new($false))
if (!$outerKilled -and !$capExceeded -and !$drainUnknown -and !$pipeError -and !$privateUrl -and $exitCode -eq 0) {
    try {
        $outer = $stdout | ConvertFrom-Json
        $usage = if ($null -ne $outer.usage) { $outer.usage } else { 'UNKNOWN' }
        $modelUsage = if ($null -ne $outer.modelUsage) { $outer.modelUsage } else { 'UNKNOWN' }
        if ($null -ne $outer.structured_output) { $review = $outer.structured_output } else { $answer = $outer.response; if ($answer -isnot [string]) { $answer = $answer | ConvertTo-Json -Depth 40 }; $review = $answer | ConvertFrom-Json }
        $expectedKeys = @($review.PSObject.Properties.Name | Sort-Object) -join ','
        if ($expectedKeys -ne 'findings,safety_checks,verdict' -or $review.findings -isnot [array] -or $review.safety_checks -isnot [array] -or $review.verdict -isnot [string]) { throw 'review schema mismatch' }
        foreach ($f in $review.findings) {
            if ((@($f.PSObject.Properties.Name | Sort-Object) -join ',') -ne 'exact_source,minimal_fix,reason,region') { throw 'finding schema mismatch' }
        }
        [IO.File]::WriteAllText((Join-Path $root 'gemini_review.pending_root_qa.json'),($review | ConvertTo-Json -Depth 40),[Text.UTF8Encoding]::new($false))
        $state = 'COMPLETE_REVIEW_STAGED_UNADJUDICATED'
    } catch { $state='PARSE_OR_SCHEMA_ERROR'; $parseError=$_.Exception.GetType().Name }
} elseif ($outerKilled) { $state='OWNED_DEADLINE_OR_LOG_CAP_TERMINATION' }
$after=[ordered]@{}
foreach ($sourcePath in $before.Keys) { $after[$sourcePath]=(Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToUpperInvariant() }
$unchanged=$true
foreach ($sourcePath in $before.Keys) { if ($after[$sourcePath] -ne $before[$sourcePath]) { $unchanged=$false } }
if (!$unchanged) { $state='INPUT_PIN_CHANGED' }
$terminal=[ordered]@{model='gemini-3.8-flash-high';pid=if($started){$proc.Id}else{$null};exit_code=$exitCode;elapsed_seconds=[math]::Round($sw.Elapsed.TotalSeconds,2);status=$state;outer_killed=$outerKilled;log_cap_exceeded=$capExceeded;pipe_error=$pipeError;drain_unknown=$drainUnknown;private_url_output_refused=$privateUrl;stdout_bytes=$stdoutBytes;stderr_bytes=$stderrBytes;stdout_sha256=$stdoutHash;stderr_sha256=$stderrHash;usage=$usage;model_usage=$modelUsage;tool_calls='UNKNOWN';subagents='UNKNOWN';input_pins_unchanged=$unchanged;input_pins_after=$after;credential_saved=$false;provider_edit=$false;source_execution=$false;parse_error_type=$parseError}
[IO.File]::WriteAllText((Join-Path $root 'gemini_terminal.json'),($terminal | ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$proc.Dispose()
Get-Content -LiteralPath (Join-Path $root 'gemini_terminal.json')
if ($state -ne 'COMPLETE_REVIEW_STAGED_UNADJUDICATED') { exit 2 }

