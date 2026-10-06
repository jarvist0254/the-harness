[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Binary,
    [Parameter(Mandatory=$true)][string]$Device,
    [ValidateRange(1024,65535)][int]$Port = 50052
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Binary -PathType Leaf)) { throw "Binary not found: $Binary" }
if ($Device -notmatch '^[A-Za-z0-9_:.,\[\]-]+$') { throw 'Use a device name returned by --list-devices.' }
# Foreground qualification process; leaves no hidden persistent service/firewall rule.
& $Binary --host '127.0.0.1' --port $Port --device $Device
if ($LASTEXITCODE -ne 0) { throw "RPC worker exited with status $LASTEXITCODE" }
