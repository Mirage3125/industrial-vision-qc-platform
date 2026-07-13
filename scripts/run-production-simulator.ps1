param(
    [string]$InputDir = "data/processed/neu-det-yolo/images/test",
    [string]$ApiUrl = "http://localhost:8000",
    [string]$Mode = "hybrid",
    [string]$StationId = "station-01",
    [string]$BatchId = "demo-batch-001",
    [double]$Interval = 1,
    [int]$Concurrency = 2,
    [int]$Limit = 10
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }
if (-not (Test-Path (Join-Path $Root $InputDir))) { throw "Input directory not found: $InputDir" }

Push-Location $Root
try {
    python -m scripts.simulate_production_line `
        --input-dir $InputDir `
        --api-url $ApiUrl `
        --mode $Mode `
        --station-id $StationId `
        --batch-id $BatchId `
        --interval $Interval `
        --concurrency $Concurrency `
        --limit $Limit
} finally {
    Pop-Location
}
