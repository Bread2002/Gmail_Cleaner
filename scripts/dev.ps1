# Gmail Cleaner — start both backend and frontend for local development
# Usage: .\scripts\dev.ps1   (run from the project root or the scripts\ folder)
# Requirements: Python 3.11+, Node 18+
#
# Opens two separate PowerShell windows so you can see live logs from each server.
# Close either window or press Ctrl+C in it to stop that process.

$root = Split-Path -Parent $PSScriptRoot

# ── Backend ──────────────────────────────────────────────────────────────────
$backendDir = Join-Path $root "backend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$venvPip = Join-Path $backendDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv (Join-Path $backendDir ".venv")
    & $venvPip install -e "$backendDir" --quiet
}

$backendCmd = @"
`$env:PYTHONUNBUFFERED = '1'
Set-Location '$backendDir'
Write-Host 'FastAPI backend starting on http://localhost:8000' -ForegroundColor Green
& '$venvPython' -m uvicorn app.main:app --reload --port 8000
"@

Write-Host "Opening backend window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# ── Frontend ─────────────────────────────────────────────────────────────────
$frontendDir = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install --prefix $frontendDir
}

$frontendCmd = @"
Set-Location '$frontendDir'
Write-Host 'Vite frontend starting on http://localhost:5173' -ForegroundColor Cyan
npm run dev
"@

Write-Host "Opening frontend window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Two terminal windows have been opened:" -ForegroundColor White
Write-Host "  Backend  (Python/uvicorn): http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend (Vite):           http://localhost:5173" -ForegroundColor Cyan
Write-Host "  API docs:                  http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Close either window to stop that server." -ForegroundColor Gray
