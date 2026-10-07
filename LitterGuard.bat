@echo off
title ECOLIFEBUDDY Surveillance Workstation v4.2 Pro - District 4
cd /d "%~dp0"

echo ================================================================
echo   ECOLIFEBUDDY Surveillance Workstation v4.2 Pro
echo   District 4 Clean Surveillance Control Room
echo ================================================================
echo Starting Surveillance Engine and Desktop Workstation...
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" web_server.py
) else (
    start "" py -3.14 web_server.py
)
timeout /t 2 /nobreak >nul
start "" msedge.exe --app=http://127.0.0.1:5000 --window-size=1440,900

exit
