# Trace Analyst - Windows Setup Script
# Run this in PowerShell as Administrator, or just double-click setup.bat instead

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TRACE ANALYST - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "  Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "  Docker is NOT installed." -ForegroundColor Red
    Write-Host "  Download Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
    Write-Host "  Install it, restart your PC, then run this script again." -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Create backend .env if it doesn't exist
Write-Host "[2/4] Setting up environment files..." -ForegroundColor Yellow
$backendEnv = ".\backend\.env"
if (-not (Test-Path $backendEnv)) {
    @"
MONGO_URL=mongodb://mongodb:27017
DB_NAME=trace_analyst
API_KEY=CHANGE_ME_GENERATE_A_STRONG_RANDOM_SECRET
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=CHANGE_ME_YOUR_GEMINI_API_KEY
GHOSINT_API_KEY=CHANGE_ME_YOUR_GHOSINT_API_KEY
BOSINT_API_KEY=CHANGE_ME_YOUR_BOSINT_API_KEY
SWATTED_API_TOKEN=CHANGE_ME_YOUR_SWATTED_TOKEN
GROK_API_KEY=CHANGE_ME_YOUR_GROK_API_KEY
"@ | Set-Content $backendEnv -Encoding utf8
    Write-Host "  Created backend/.env" -ForegroundColor Green
} else {
    Write-Host "  backend/.env already exists, skipping" -ForegroundColor Gray
}

# 3. Pull / build images
Write-Host "[3/4] Building Docker images (first run takes 3-5 mins)..." -ForegroundColor Yellow
docker-compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Build failed. Check the output above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 4. Start everything
Write-Host "[4/4] Starting all services..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Failed to start. Check the output above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  App:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API:     http://localhost:8001/api/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To stop:   docker-compose down" -ForegroundColor Gray
Write-Host "  To logs:   docker-compose logs -f" -ForegroundColor Gray
Write-Host ""

# Try to open browser
Start-Process "http://localhost:3000"

Read-Host "Press Enter to exit"
