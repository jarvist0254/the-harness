[CmdletBinding()]
param([string]$Destination = 'E:\the_harness')
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$target = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
if ($source -ieq $target) { Write-Host "Already installed at $target"; exit 0 }
if ($target.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Destination must not be inside the extracted source directory.'
}
$drive = [IO.Path]::GetPathRoot($target)
if (-not (Test-Path -LiteralPath $drive)) { throw "Drive is unavailable: $drive" }
$files = @(Get-ChildItem -LiteralPath $source -Recurse -File -Force)
$pending = @()
foreach ($file in $files) {
    $relative = $file.FullName.Substring($source.Length).TrimStart('\')
    $out = Join-Path $target $relative
    $ancestor = Split-Path -Parent $out
    while ($ancestor -and $ancestor.Length -ge $target.Length) {
        if ((Test-Path -LiteralPath $ancestor) -and -not (Test-Path -LiteralPath $ancestor -PathType Container)) {
            throw "Destination parent is a file: $ancestor"
        }
        $ancestor = Split-Path -Parent $ancestor
    }
    if (Test-Path -LiteralPath $out) {
        if (-not (Test-Path -LiteralPath $out -PathType Leaf)) { throw "Destination conflict: $out" }
        $a = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $b = (Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash
        if ($a -ne $b) { throw "Existing file differs; resolve before copying: $out" }
    } else { $pending += [pscustomobject]@{Source=$file.FullName; Target=$out} }
}
foreach ($item in $pending) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $item.Target) -Force | Out-Null
    Copy-Item -LiteralPath $item.Source -Destination $item.Target
}
Write-Host "Installed $($pending.Count) new files at $target; identical files retained."
Write-Host 'Next: python .\scripts\verify_package.py; then scripts\audit_local_projects.ps1'
