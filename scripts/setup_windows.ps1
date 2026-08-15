$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$Launcher = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $Launcher) {
    & py -3.13 -m venv .venv
} else {
    $Version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($Version.Trim() -ne "3.13") {
        throw "Python 3.13 is required. Current Python: $Version"
    }
    python -m venv .venv
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"
& $Python scripts/quality_gate.py
& $Python -m ruff check src tests scripts
& $Python -m pytest -q

Write-Host ""
Write-Host "Setup and validation completed successfully."
Write-Host "Run the application with:"
Write-Host "  .\.venv\Scripts\python.exe -m tms"
