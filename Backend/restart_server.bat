@echo off
echo Stopping existing server...
taskkill /F /FI "WINDOWTITLE eq *Flask*" /T 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *start_server.py*" /T 2>nul
timeout /t 2 /nobreak >nul

echo Starting Flask server...
cd /d "%~dp0"
python start_server.py
pause


