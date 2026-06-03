# Start Cortex — backend + frontend
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "  Created .env — add your ANTHROPIC_API_KEY before continuing." -ForegroundColor Yellow
    Write-Host "  Edit .env, then run this script again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Starting backend (http://localhost:8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run.py"

Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install

Write-Host "Starting frontend (http://localhost:5173)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  Cortex is running." -ForegroundColor Green
Write-Host "  Open http://localhost:5173 in your browser." -ForegroundColor White
Write-Host ""
