<#
    TAK Device Monitor launcher.
    Starts the backend (if not already running) and opens the dashboard in
    the default browser. Safe to run repeatedly — if the server is already
    up it just (re)opens the dashboard.

    Usage:   .\start.ps1            # start + open dashboard
             .\start.ps1 -NoBrowser # start only, don't open a browser
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
# Health checks must hit 127.0.0.1 explicitly: daphne binds IPv4, but
# "localhost" resolves to IPv6 (::1) first on Windows and would fail the probe.
$checkUrl = "http://127.0.0.1:$Port"
# The browser gets the friendlier localhost URL (it falls back to IPv4 itself).
$url = "http://localhost:$Port"
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

function Test-Server {
    try {
        Invoke-WebRequest "$checkUrl/api/devices" -TimeoutSec 2 -UseBasicParsing | Out-Null
        return $true
    }
    catch { return $false }
}

# 1. First run: create the virtualenv and install dependencies.
if (-not (Test-Path $venvPy)) {
    Write-Host "First run: creating virtualenv and installing dependencies..." -ForegroundColor Cyan
    python -m venv (Join-Path $root ".venv")
    $env:CURL_CA_BUNDLE = ""   # this machine's CA bundle var breaks pip
    & $venvPy -m pip install --upgrade pip | Out-Null
    & $venvPy -m pip install -r (Join-Path $root "requirements.txt")
}

# 2. Open the dashboard once the server answers (runs in the background so
#    the browser launches the moment daphne is ready).
if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($check, $open)
        for ($i = 0; $i -lt 60; $i++) {
            try {
                Invoke-WebRequest "$check/api/devices" -TimeoutSec 2 -UseBasicParsing | Out-Null
                Start-Process $open
                return
            }
            catch { Start-Sleep -Seconds 1 }
        }
    } -ArgumentList $checkUrl, $url | Out-Null
}

# 3. If a server is already running, don't start a second one — the browser
#    job above will still open the dashboard.
if (Test-Server) {
    Write-Host "TAK Device Monitor already running at $url" -ForegroundColor Green
    Write-Host "Opening dashboard..." -ForegroundColor Green
    if (-not $NoBrowser) { Start-Job { param($u) Start-Process $u } -ArgumentList $url | Out-Null }
    return
}

# 4. Start the server in the foreground (Ctrl+C stops it).
$env:CURL_CA_BUNDLE = ""
Write-Host "Starting TAK Device Monitor at $url  (Ctrl+C to stop)" -ForegroundColor Green
Set-Location (Join-Path $root "backend")
& $venvPy -m daphne -b $BindHost -p $Port takbridge.asgi:application
