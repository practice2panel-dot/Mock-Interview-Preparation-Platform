@echo off
echo ========================================
echo   Interview Project - Starting Services
echo ========================================
echo.

echo [1/4] Checking if Python is installed...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)
echo ✅ Python found

echo.
echo [2/4] Checking if Node.js is installed...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed or not in PATH
    echo Please install Node.js and try again
    pause
    exit /b 1
)
echo ✅ Node.js found

echo.
echo [3/4] Starting Backend Server...
cd Backend
echo Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1
echo Creating sample database tables...
python create_sample_tables.py
echo Starting Flask API server on http://localhost:5000...
start "Backend Server" cmd /k "python start_server.py"
cd ..

echo.
echo [4/4] Starting Frontend Server...
cd frontend
echo Installing Node.js dependencies...
npm install >nul 2>&1
echo Starting React development server on http://localhost:3000...
start "Frontend Server" cmd /k "npm start"
cd ..

echo.
echo ========================================
echo   🚀 Both services are starting!
echo ========================================
echo.
echo Backend API:  http://localhost:5000
echo Frontend App: http://localhost:3000
echo.
echo Press any key to exit this launcher...
pause >nul
