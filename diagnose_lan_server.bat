@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Real Estate CRM LAN Diagnostics
echo ============================================================
echo.

echo Server IP addresses:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' } | Select-Object InterfaceAlias,IPAddress,PrefixLength,AddressState | Format-Table -AutoSize"

echo.
echo Network profile:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetConnectionProfile | Select-Object Name,InterfaceAlias,NetworkCategory,IPv4Connectivity | Format-Table -AutoSize"

echo.
echo Port 6090 listener:
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 6090 -ErrorAction SilentlyContinue; if ($c) { $c | Select-Object LocalAddress,LocalPort,State,OwningProcess | Format-Table -AutoSize } else { Write-Host 'Port 6090 is NOT listening. Start the CRM server first.' }"

echo.
echo Firewall rule:
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=Get-NetFirewallRule -DisplayName 'Real Estate CRM LAN Server 6090' -ErrorAction SilentlyContinue; if ($r) { $r | Select-Object DisplayName,Enabled,Direction,Action,Profile | Format-Table -AutoSize; $r | Get-NetFirewallPortFilter | Select-Object Protocol,LocalPort | Format-Table -AutoSize } else { Write-Host 'Firewall rule is missing. Run enable_crm_firewall_6090.bat as administrator.' }"

echo.
echo Firewall profile policy:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,AllowLocalFirewallRules | Format-Table -AutoSize"

echo.
echo Client computer test:
echo   1. Make sure client is on the same office Wi-Fi/LAN, not Guest Wi-Fi.
echo   2. Make sure mobile data/VPN is off while testing the local 192.168.x.x URL.
echo   3. On client PowerShell, run:
echo      Test-NetConnection SERVER-IP -Port 6090
echo   4. Browser URL:
echo      http://SERVER-IP:6090
echo.
echo If ping works but port test fails, run enable_crm_firewall_6090.bat as administrator.
echo If ping fails too, router/client isolation or different subnet is blocking LAN devices.
echo.
pause
