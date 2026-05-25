# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: PowerShell script to start both the FastAPI backend and Vite frontend in development mode.
#              Sets up a Python virtual environment for the backend if it doesn't exist.
#              Launches each in a new terminal window where possible. 

# Determine project root
$root = Split-Path -Parent $PSScriptRoot

# Determine the backend directory and paths to the Python virtual environment executables
$backendDir = Join-Path $root "backend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$venvPip = Join-Path $backendDir ".venv\Scripts\pip.exe"

# Create the Python virtual environment (if it doesn't exist) and install the backend dependencies
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv (Join-Path $backendDir ".venv")
    & $venvPip install -e "$backendDir" --quiet
}

# Define the command to start the backend server
$backendCmd = @"
`$env:PYTHONUNBUFFERED = '1'
Set-Location '$backendDir'
& '$venvPython' -m uvicorn app.main:app --reload --port 8000
"@

# Start the backend server in a new terminal window
Write-Host "Starting the backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Determine the frontend directory
$frontendDir = Join-Path $root "frontend"

# Install dependencies for the frontend
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install --prefix $frontendDir
}
# Define the command to start the frontend server
$frontendCmd = @"
Set-Location '$frontendDir'
npm run dev
"@

# Start the frontend server in a new terminal window
Write-Host "Starting the frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Display instructions to the user
Write-Host ""
Write-Host "Both servers are running in their respective terminals:" -ForegroundColor White
Write-Host "Backend  (Python/uvicorn): http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend (Vite): http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close either window to stop that server..." -ForegroundColor Gray
