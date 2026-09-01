# SatyaVaani setup -- Windows PowerShell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "=== SatyaVaani setup ===" -ForegroundColor Cyan
python --version
if (-Not (Test-Path .venv)) { Write-Host "-- creating .venv"; python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
Write-Host "-- installing core deps"
pip install -q -r requirements.txt
Write-Host ""
Write-Host "Done. Two terminals:" -ForegroundColor Green
Write-Host "  1)  .\.venv\Scripts\Activate.ps1 ; uvicorn backend.main:app --reload --port 8000"
Write-Host "  2)  cd frontend ; npm install ; npm run dev"
Write-Host ""
Write-Host "No backend yet?  python mocks\mock_server.py"
