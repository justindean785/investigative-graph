@echo off
echo.
echo ========================================
echo   TRACE ANALYST - Quick Start
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker is NOT installed.
    echo  Download it from: https://www.docker.com/products/docker-desktop/
    echo  Install, restart PC, then run this again.
    pause
    exit /b 1
)

REM Create backend .env if missing
if not exist "backend\.env" (
    echo Creating backend\.env...
    (
        echo MONGO_URL=mongodb://mongodb:27017
        echo DB_NAME=trace_analyst
        echo API_KEY=CHANGE_ME_GENERATE_A_STRONG_RANDOM_SECRET
        echo CORS_ORIGINS=http://localhost:3000
        echo GEMINI_API_KEY=CHANGE_ME_YOUR_GEMINI_API_KEY
        echo GHOSINT_API_KEY=CHANGE_ME_YOUR_GHOSINT_API_KEY
        echo BOSINT_API_KEY=CHANGE_ME_YOUR_BOSINT_API_KEY
        echo SWATTED_API_TOKEN=CHANGE_ME_YOUR_SWATTED_TOKEN
        echo GROK_API_KEY=CHANGE_ME_YOUR_GROK_API_KEY
    ) > backend\.env
)

echo Building and starting services (first run: 3-5 mins)...
docker-compose up -d --build

if %errorlevel% neq 0 (
    echo.
    echo Failed to start. See output above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Started!
echo   Open: http://localhost:3000
echo ========================================
echo.
start http://localhost:3000
pause
