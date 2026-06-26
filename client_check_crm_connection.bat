@echo off
setlocal
set SERVER_IP=192.168.10.5
set SERVER_PORT=6090

echo ============================================================
echo Real Estate CRM - Client Connection Check
echo ============================================================
echo.
echo This file should be run on the STAFF / REMOTE computer.
echo CRM server: http://%SERVER_IP%:%SERVER_PORT%
echo.

echo [1] Client network address:
ipconfig | findstr /i "IPv4 Gateway Subnet"
echo.

echo [2] Ping CRM server:
ping %SERVER_IP% -n 4
echo.

echo [3] Test CRM web port:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Test-NetConnection %SERVER_IP% -Port %SERVER_PORT%"
echo.

echo [4] Open CRM in browser:
echo http://%SERVER_IP%:%SERVER_PORT%
echo.
pause
