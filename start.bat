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
        echo API_KEY=trace-analyst-secret-2026
        echo CORS_ORIGINS=http://localhost:3000
        echo GEMINI_API_KEY=AIzaSyBHYg_vCRVgAMEAlaorugEKQ-qFwWFDZOM
        echo GHOSINT_API_KEY=f6426e34ac2f0a6d6ce2ef42a1126293
        echo BOSINT_API_KEY=bosint_7hWCmPaD22U4oVzFsJYnN6-C1vg28uE4l2wBi6F13kg
        echo SWATTED_API_KEY=42h2CBYkixoswQNnUmnL6C7
        echo SWATTED_SESSION_TOKEN=573dc0da20844623fb092f2dcb0777025350fea1f7f6255c1025399c27cafe2
        echo SWATTED_USER_ID=98752428806
        echo SWATTED_CSRF_TOKEN=f0ece390b00afcb8f38c351e9848cf98a568ecabe60ad7f34c3f8820bd0d0697
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
