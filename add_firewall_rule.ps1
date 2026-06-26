# Add firewall rule for Real Estate CRM port 6090
netsh advfirewall firewall delete rule name="Real Estate CRM LAN Server 6090" 2>$null
netsh advfirewall firewall add rule name="Real Estate CRM LAN Server 6090" dir=in action=allow protocol=TCP localport=6090 profile=any enable=yes
Write-Host "Firewall rule for port 6090 added successfully"

# Also add rule for port 6091 (Desktop API)
netsh advfirewall firewall delete rule name="Real Estate CRM Desktop API 6091" 2>$null
netsh advfirewall firewall add rule name="Real Estate CRM Desktop API 6091" dir=in action=allow protocol=TCP localport=6091 profile=any enable=yes
Write-Host "Firewall rule for port 6091 added successfully"

# Change network profile to Private for better LAN sharing
Get-NetConnectionProfile | Where-Object {$_.IPv4Connectivity -ne 'Disconnected'} | Set-NetConnectionProfile -NetworkCategory Private
Write-Host "Network profile set to Private"
