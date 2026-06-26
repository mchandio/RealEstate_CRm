@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Real Estate CRM - Permanent LAN Access Setup
echo ============================================================
echo.
echo This will:
echo   - Allow CRM ports 80, 6090, and 6091 in Windows Firewall
echo   - Allow ping to this CRM server
echo   - Forward http://SERVER-IP/ to CRM port 6090
echo   - Set the active Windows network profile to Private
echo.
echo Please approve the Administrator prompt.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0tools\setup_crm_permanent_access.ps1""'"

echo.
echo After it finishes, try from a staff computer:
echo   http://192.168.10.5/
echo   http://192.168.10.5:6090/
echo.
pause
