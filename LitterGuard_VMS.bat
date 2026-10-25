@echo off
title EcoLifyBuddy Workstation
cd /d "%~dp0"

echo ================================================================
echo   EcoLifyBuddy Workstation
echo   Visitor Identification, Activity Tracking, Safer Communities
echo ================================================================
echo Starting AI Engine and Desktop Workstation (Python 3.12)...
echo.

set "PYTHON_EXE=%~dp0.venv312\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [!] No project Python environment was found.
    echo     Create one with: python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

start "" "%PYTHON_EXE%" web_server.py
timeout /t 2 /nobreak >nul
start "" msedge.exe --app=http://127.0.0.1:5000 --window-size=1440,900

exit
