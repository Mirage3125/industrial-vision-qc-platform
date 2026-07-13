param(
    [Parameter(Position = 0)]
    [ValidateSet("run", "migrate", "seed", "classical", "test", "lint", "format", "format-check", "typecheck", "check")]
    [string]$Command = "run"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

switch ($Command) {
    "run" { python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 }
    "migrate" { python -m alembic upgrade head }
    "seed" { python -m scripts.seed_database }
    "classical" {
        if (-not $args[0]) { throw "Usage: .\scripts.ps1 classical <image-or-directory>" }
        python -m scripts.run_classical_vision $args[0]
    }
    "test" { python -m pytest }
    "lint" { python -m ruff check . }
    "format" { python -m black . }
    "format-check" { python -m black --check . }
    "typecheck" { python -m mypy }
    "check" {
        python -m ruff check .
        python -m black --check .
        python -m mypy
        python -m pytest
    }
}
