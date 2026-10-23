@echo off
title EcoLifyBuddy - AI CCTV Intelligence System
cd /d "%~dp0"

echo ================================================================
echo   EcoLifyBuddy - AI CCTV Intelligence System
echo   Visitor Identification, Activity Tracking, Safer Communities
echo ================================================================
echo Starting AI Engine and Web Dashboard (Python 3.12)...
echo.

if exist "%~dp0.venv312\Scripts\python.exe" (
    "%~dp0.venv312\Scripts\python.exe" app.py
) else (
    echo [!] .venv312 not found. Create it with:
    echo     py -3.12 -m venv .venv312
    echo     .venv312\Scripts\python.exe -m pip install -r requirements.txt
    py -3.12 app.py
)

pause
