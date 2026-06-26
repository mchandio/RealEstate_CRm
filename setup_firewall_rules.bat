@echo off
REM Real Estate CRM Firewall Configuration
echo Adding firewall rules for Real Estate CRM...

REM Add rule for port 6090 (Web UI)
netsh advfirewall firewall add rule name="Real Estate CRM LAN Server 6090" dir=in action=allow protocol=TCP localport=6090 profile=public,private,domain enable=yes > nul
echo ✓ Added firewall rule for port 6090

REM Add rule for port 6091 (Desktop API)
netsh advfirewall firewall add rule name="Real Estate CRM Desktop API 6091" dir=in action=allow protocol=TCP localport=6091 profile=public,private,domain enable=yes > nul
echo ✓ Added firewall rule for port 6091

echo.
echo Firewall rules are now active!
echo.
