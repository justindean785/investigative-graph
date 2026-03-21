# Start MongoDB in Docker (requires Docker Desktop).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
docker compose up -d
Write-Host ""
Write-Host "MongoDB: mongodb://127.0.0.1:27017" -ForegroundColor Green
Write-Host "backend/.env: MONGO_URL=mongodb://127.0.0.1:27017  DB_NAME=trace_analyst"
Write-Host "Stop: docker compose down"
