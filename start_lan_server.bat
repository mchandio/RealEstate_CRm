@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment not found.
    echo Run: py -3.14 -m venv .venv
    echo Then: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

set API_HOST=0.0.0.0
set API_PORT=6090

echo Starting Real Estate CRM LAN server on all network adapters, port 6090...
echo If some computers cannot connect, run enable_crm_firewall_6090.bat as administrator.
echo.
".venv\Scripts\python.exe" run_lan_server.py
pause
