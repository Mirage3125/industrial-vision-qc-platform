$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidFile = Join-Path $Root "artifacts/dev-processes.json"

function Stop-IfRunning($PidValue, $Name) {
    if (-not $PidValue) { return }
    $process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping $Name PID $PidValue"
        Stop-Process -Id $PidValue -Force
    }
}

if (Test-Path $pidFile) {
    $state = Get-Content $pidFile -Raw | ConvertFrom-Json
    Stop-IfRunning $state.backend_pid "backend"
    Stop-IfRunning $state.frontend_pid "frontend"
    Remove-Item $pidFile -Force
} else {
    Write-Warning "PID file not found: $pidFile"
}
