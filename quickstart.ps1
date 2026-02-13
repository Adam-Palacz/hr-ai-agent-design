# Quick start script for Recruitment AI (PowerShell)
# Run from project root: .\quickstart.ps1

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host '=== Recruitment AI – Quick Start (PowerShell) ===' -ForegroundColor Cyan
Write-Host ''

# Python check
$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $python = 'python' }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $python = 'python3' }
if (-not $python) {
    Write-Host 'Python not found. Install Python 3.11+ and try again.' -ForegroundColor Red
    exit 1
}
Write-Host 'Using: $python' -ForegroundColor Green

# Virtual environment
$venvPath = Join-Path $ProjectRoot 'venv'
if (-not (Test-Path $venvPath)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    & $python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'Activating venv...' -ForegroundColor Yellow
$activateScript = Join-Path $venvPath 'Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    Write-Host 'venv activation script not found at $activateScript' -ForegroundColor Red
    exit 1
}
. $activateScript

# Dependencies
Write-Host 'Installing dependencies...' -ForegroundColor Yellow
pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Dependencies OK.' -ForegroundColor Green

# .env
$envPath = Join-Path $ProjectRoot '.env'
$envExample = Join-Path $ProjectRoot '.env.example'
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envPath
        Write-Host ''
        Write-Host 'Created .env from .env.example. Please edit .env and set AZURE_OPENAI_API_KEY and other variables.' -ForegroundColor Yellow
        Write-Host 'Then run this script again to start the app.' -ForegroundColor Yellow
        exit 0
    }
    Write-Host '.env not found. Create .env with at least AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host 'Starting application...' -ForegroundColor Cyan
Write-Host 'Open http://localhost:5000 when ready.' -ForegroundColor Green
Write-Host ''
& $python app.py
