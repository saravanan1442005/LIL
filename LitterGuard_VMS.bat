@echo off
title EcoLifyBuddy Workstation
cd /d "%~dp0"

echo ================================================================
echo   EcoLifyBuddy Workstation
echo   Visitor Identification, Activity Tracking, Safer Communities
echo ================================================================
echo Starting AI Engine and Desktop Workstation (Python 3.12)...
echo.

if exist "%~dp0.venv312\Scripts\python.exe" (
    start "" "%~dp0.venv312\Scripts\python.exe" web_server.py
) else (
    start "" py -3.12 web_server.py
)
timeout /t 2 /nobreak >nul
start "" msedge.exe --app=http://127.0.0.1:5000 --window-size=1440,900

exit
