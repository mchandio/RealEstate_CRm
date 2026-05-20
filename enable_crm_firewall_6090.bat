@echo off
setlocal
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Please right-click this file and choose "Run as administrator".
    pause
    exit /b 1
)

echo Configuring Real Estate CRM firewall access...
echo.

netsh advfirewall firewall delete rule name="Real Estate CRM LAN Server 6090" >nul 2>&1
netsh advfirewall firewall add rule name="Real Estate CRM LAN Server 6090" dir=in action=allow protocol=TCP localport=6090 profile=any enable=yes
netsh advfirewall firewall delete rule name="Real Estate CRM Desktop API 6091" >nul 2>&1
netsh advfirewall firewall add rule name="Real Estate CRM Desktop API 6091" dir=in action=allow protocol=TCP localport=6091 profile=any enable=yes

echo.
echo Firewall local-rule policy:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,AllowLocalFirewallRules | Format-Table -AutoSize"
echo.
echo If AllowLocalFirewallRules is False or blank because of Group Policy,
echo Windows may ignore local rules until the PC/admin policy allows them.

echo.
echo Current network profile:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetConnectionProfile | Select-Object Name,InterfaceAlias,NetworkCategory,IPv4Connectivity | Format-Table -AutoSize"
echo.
echo If this is your private office Wi-Fi/LAN, Windows works best when the
echo network profile is Private. Public profile can block office computers.
echo.
set /p MAKE_PRIVATE=Change current connected network profile to Private? [Y/N] 
if /I "%MAKE_PRIVATE%"=="Y" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetConnectionProfile | Where-Object {$_.IPv4Connectivity -ne 'Disconnected'} | Set-NetConnectionProfile -NetworkCategory Private"
    echo Network profile changed to Private.
)

echo.
echo Firewall rules added for Real Estate CRM on TCP ports 6090 and 6091 for all profiles.
echo Client computers should open: http://SERVER-IP:6090
pause
