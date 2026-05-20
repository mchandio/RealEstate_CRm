@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Real Estate CRM - LAN Access Repair
echo ============================================================
echo.
echo This opens CRM ports 80, 6090, and 6091 for LocalSubnet only,
echo allows the CRM Python server through Windows Firewall,
echo and sets the active network profile to Private where Windows permits it.
echo.
echo Please approve the Windows administrator prompt.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0tools\repair_lan_access.ps1""'"
echo.
echo After the admin window finishes, try on the other PC:
echo   http://192.168.10.5/
echo.
pause
