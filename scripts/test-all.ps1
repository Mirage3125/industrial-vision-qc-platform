$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "npm.cmd not found" }

Push-Location $Root
try {
    python -m pytest
    python -m ruff check .
    python -m mypy
    Push-Location (Join-Path $Root "frontend")
    try {
        npm.cmd run lint
        npm.cmd run typecheck
        npm.cmd run build
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}
