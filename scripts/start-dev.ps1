param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$ApiBaseUrl = "http://localhost:8000/api/v1",
    [int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Required command not found: $Name"
    }
}

function Assert-Port-Free($Port, $Name) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Fail "$Name port $Port is already in use by PID $($listener.OwningProcess -join ', ')."
    }
}

function Get-LogTail($Path) {
    if (-not (Test-Path $Path)) {
        return ""
    }
    return (Get-Content -Path $Path -Tail 30 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
}

function Wait-Endpoint($Url, $Name, $Process, $OutLog, $ErrLog) {
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            $outTail = Get-LogTail $OutLog
            $errTail = Get-LogTail $ErrLog
            Fail "$Name process exited during startup. stdout: $outTail stderr: $errTail"
        }
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    $outTail = Get-LogTail $OutLog
    $errTail = Get-LogTail $ErrLog
    Fail "$Name did not become reachable at $Url within $StartupTimeoutSeconds seconds. stdout: $outTail stderr: $errTail"
}

function Normalize-ProcessPathEnvironment {
    $variables = [System.Environment]::GetEnvironmentVariables("Process")
    if ($variables.Contains("Path") -and $variables.Contains("PATH")) {
        $pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
        $upperPathValue = [System.Environment]::GetEnvironmentVariable("PATH", "Process")
        if (-not $pathValue) {
            $pathValue = $upperPathValue
        }
        [System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
        [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    }
}

Normalize-ProcessPathEnvironment
Assert-Command python
Assert-Command node
Assert-Command npm.cmd

$PythonCmd = (Get-Command python).Source
$NpmCmd = (Get-Command npm.cmd).Source

if (-not $env:CONDA_PREFIX) {
    Write-Warning "CONDA_PREFIX is not set. Activate the intended Conda environment before starting dev services."
}

Assert-Port-Free $BackendPort "Backend"
Assert-Port-Free $FrontendPort "Frontend"

$env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl
$backendLog = Join-Path $Root "artifacts/dev-backend.out.log"
$backendErrorLog = Join-Path $Root "artifacts/dev-backend.err.log"
$frontendLog = Join-Path $Root "artifacts/dev-frontend.out.log"
$frontendErrorLog = Join-Path $Root "artifacts/dev-frontend.err.log"
New-Item -ItemType Directory -Force -Path (Join-Path $Root "artifacts") | Out-Null

$backend = Start-Process -FilePath $PythonCmd -PassThru -WindowStyle Hidden -WorkingDirectory $Root `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrorLog `
    -ArgumentList @(
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "$BackendPort"
    )

$frontend = Start-Process -FilePath $NpmCmd -PassThru -WindowStyle Hidden `
    -WorkingDirectory (Join-Path $Root "frontend") `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrorLog `
    -ArgumentList @("run", "dev", "--", "--port", "$FrontendPort")

$pidFile = Join-Path $Root "artifacts/dev-processes.json"
@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
    backend_url = "http://127.0.0.1:$BackendPort"
    frontend_url = "http://localhost:$FrontendPort"
} | ConvertTo-Json | Set-Content -Encoding UTF8 $pidFile

Write-Host "Backend starting: http://127.0.0.1:$BackendPort"
Write-Host "Frontend starting: http://localhost:$FrontendPort"
Write-Host "PID file: $pidFile"
Write-Host "Logs: $backendLog ; $backendErrorLog ; $frontendLog ; $frontendErrorLog"

Wait-Endpoint "http://127.0.0.1:$BackendPort/api/v1/health" "Backend" $backend $backendLog $backendErrorLog
Wait-Endpoint "http://localhost:$FrontendPort" "Frontend" $frontend $frontendLog $frontendErrorLog
Write-Host "Backend ready: http://127.0.0.1:$BackendPort"
Write-Host "Frontend ready: http://localhost:$FrontendPort"
