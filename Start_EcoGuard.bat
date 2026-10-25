@echo off
title EcoLifyBuddy - AI CCTV Intelligence System
cd /d "%~dp0"

echo ================================================================
echo   EcoLifyBuddy - AI CCTV Intelligence System
echo   Visitor Identification, Activity Tracking, Safer Communities
echo ================================================================
echo Starting AI Engine and Web Dashboard (Python 3.12)...
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

"%PYTHON_EXE%" app.py

pause
