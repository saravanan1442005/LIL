@echo off
title ECOLIFEBUDDY AI - Smart Litter Detection System
cd /d "%~dp0"

echo ================================================================
echo   ECOLIFEBUDDY AI - Smart Litter Detection System
echo ================================================================
echo Starting Surveillance Engine and Web Dashboard...
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" app.py
) else (
    py -3.14 app.py
)

pause
