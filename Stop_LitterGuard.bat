@echo off
title Stop ECOLIFEBUDDY AI
echo ================================================================
echo   Stopping ECOLIFEBUDDY AI Surveillance Engine...
echo ================================================================
echo.

powershell -Command "$conns = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue; if ($conns) { foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } }; Write-Host 'ECOLIFEBUDDY AI server on port 5000 stopped.'"

echo.
echo Server stopped successfully.
timeout /t 2 >nul
exit
