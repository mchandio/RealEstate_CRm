@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Real Estate CRM - Remote Access Tunnel
echo ============================================================
echo.
echo This opens the CRM for other devices through a temporary HTTPS URL.
echo Keep the tunnel window open while users are working.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_remote_tunnel.ps1"
pause
