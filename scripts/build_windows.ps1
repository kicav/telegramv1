$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
$env:PYTHONPATH = (Join-Path $RepoRoot "src")

python scripts/quality_gate.py
python -m ruff check src tests scripts
python -m pytest -q

if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force
}

python -m nuitka `
  --standalone `
  --enable-plugin=pyside6 `
  --windows-console-mode=disable `
  --assume-yes-for-downloads `
  --include-package=tms `
  --include-package=telethon `
  --include-package=openpyxl `
  --include-data-file="src/tms/storage/schema.sql=tms/storage/schema.sql" `
  --output-dir=dist `
  --output-filename=TelegramMigrationStudio.exe `
  scripts/windows_entry.py

Write-Host ""
Write-Host "Windows standalone build completed under dist/."
