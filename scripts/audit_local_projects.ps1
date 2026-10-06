[CmdletBinding()]
param(
    [string[]]$Roots = @('E:\je_horizon', 'E:\python_gpu'),
    [string]$OutputDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'records\local_audit')
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$skip = @('.git','.venv','venv','node_modules','__pycache__','build','dist','.next','site-packages')
$symbols = '(?i)(pyre|gpu|vram|backend|reserve|reservation|admission|resume|detach|checkpoint|crossover|parity|queue|worker|device|scheduler)'
$report = @()
foreach ($root in $Roots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        $report += [pscustomobject]@{root=$root; status='UNAVAILABLE'; files=@()}; continue
    }
    $queue = New-Object 'System.Collections.Generic.Queue[string]'
    $queue.Enqueue((Get-Item -LiteralPath $root).FullName)
    $files = @(); $repos = @(); $errors = @(); $count = 0
    while ($queue.Count -gt 0 -and $count -lt 25000) {
        $dir = $queue.Dequeue()
        try { $entries = @(Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop) }
        catch { $errors += $dir; continue }
        if (Test-Path -LiteralPath (Join-Path $dir '.git')) {
            $commit = $null
            if (Get-Command git -ErrorAction SilentlyContinue) {
                $commit = (& git -C $dir rev-parse HEAD 2>$null | Select-Object -First 1)
            }
            $repos += [pscustomobject]@{path=$dir; commit=$commit}
        }
        foreach ($entry in $entries) {
            $count++
            if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            if ($entry.PSIsContainer) {
                if ($skip -notcontains $entry.Name) { $queue.Enqueue($entry.FullName) }; continue
            }
            $isSource = $entry.Extension -in @('.py','.ps1','.toml','.json','.yaml','.yml','.ini','.cfg')
            $isInstruction = $entry.Name -in @('AGENTS.md','requirements.txt')
            if (-not ($isSource -or $isInstruction) -or $entry.Length -gt 2097152) { continue }
            if ($entry.Name -match '(?i)(secret|credential|token|\.env|oauth|private.key)') { continue }
            $hits = @()
            if ($entry.Extension -in @('.py','.ps1')) {
                try {
                    $lineNumber = 0
                    foreach ($line in [IO.File]::ReadLines($entry.FullName)) {
                        $lineNumber++
                        # Symbol identifiers only; never copy matched source lines/values.
                        if ($line -match '^\s*(?:async\s+)?(?:def|class|function)\s+([A-Za-z_][A-Za-z0-9_-]*)') {
                            $name = $Matches[1]
                            if ($name -match $symbols) { $hits += [pscustomobject]@{line=$lineNumber; symbol=$name} }
                        }
                    }
                } catch { $errors += $entry.FullName }
            }
            if ($hits.Count -gt 0 -or $entry.Name -match $symbols -or $isInstruction -or $entry.Name -in @('pyproject.toml','requirements.txt')) {
                $files += [pscustomobject]@{path=$entry.FullName; bytes=$entry.Length;
                    modified_utc=$entry.LastWriteTimeUtc.ToString('o'); symbols=$hits}
            }
        }
    }
    $report += [pscustomobject]@{root=$root; status='SCANNED'; entries_seen=$count;
        bounded_scan_truncated=($queue.Count -gt 0); repositories=$repos; files=$files; unreadable_paths=$errors}
}
$path = Join-Path $OutputDirectory 'source_candidates.json'
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Read-only source candidate report written: $path"
Write-Host 'This lists metadata and symbols; source inspection and AGENTS.md review are still required.'
