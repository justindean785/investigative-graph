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
API_KEY=trace-analyst-secret-2026
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=AIzaSyBHYg_vCRVgAMEAlaorugEKQ-qFwWFDZOM
GHOSINT_API_KEY=f6426e34ac2f0a6d6ce2ef42a1126293
BOSINT_API_KEY=bosint_7hWCmPaD22U4oVzFsJYnN6-C1vg28uE4l2wBi6F13kg
SWATTED_API_KEY=42h2CBYkixoswQNnUmnL6C7
SWATTED_SESSION_TOKEN=573dc0da20844623fb092f2dcb0777025350fea1f7f6255c1025399c27cafe2
SWATTED_USER_ID=98752428806
SWATTED_CSRF_TOKEN=f0ece390b00afcb8f38c351e9848cf98a568ecabe60ad7f34c3f8820bd0d0697
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
