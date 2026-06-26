$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogPath = Join-Path $ProjectRoot "outputs\setup_crm_permanent_access.log"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    $line | Tee-Object -FilePath $LogPath -Append
}

function Get-ServerIPv4 {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "169.254*" -and
            $_.IPAddress -ne "127.0.0.1" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Sort-Object InterfaceMetric |
        Select-Object -First 1 -ExpandProperty IPAddress
    if (-not $ip) {
        throw "No active IPv4 address found."
    }
    return $ip
}

$ServerIP = Get-ServerIPv4
Write-Log "CRM server IP: $ServerIP"

try {
    Get-NetConnectionProfile |
        Where-Object { $_.IPv4Connectivity -ne "Disconnected" } |
        Set-NetConnectionProfile -NetworkCategory Private
    Write-Log "Network profile set to Private."
} catch {
    Write-Log "Could not set network profile to Private: $($_.Exception.Message)"
}

$PortRules = @(
    @{ Name = "QT_CRM_MBM Web 80"; Port = 80 },
    @{ Name = "QT_CRM_MBM Web 6090"; Port = 6090 },
    @{ Name = "QT_CRM_MBM Desktop API 6091"; Port = 6091 },
    @{ Name = "Real Estate CRM Web UI 80"; Port = 80 },
    @{ Name = "Real Estate CRM Web UI 6090"; Port = 6090 },
    @{ Name = "Real Estate CRM Desktop API 6091"; Port = 6091 }
)

foreach ($rule in $PortRules) {
    Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule `
        -DisplayName $rule.Name `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $rule.Port `
        -Profile Any | Out-Null
    Write-Log "Firewall allow rule ready: $($rule.Name) TCP $($rule.Port)"
}

Get-NetFirewallRule -DisplayName "CRM Allow ICMPv4 Ping" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule `
    -DisplayName "CRM Allow ICMPv4 Ping" `
    -Direction Inbound `
    -Action Allow `
    -Protocol ICMPv4 `
    -IcmpType 8 `
    -Profile Any | Out-Null
Write-Log "Firewall allow rule ready: ICMPv4 ping."

try {
    Set-Service iphlpsvc -StartupType Automatic
    Start-Service iphlpsvc
    Write-Log "IP Helper service is running."
} catch {
    Write-Log "Could not start IP Helper service: $($_.Exception.Message)"
}

& netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=80 2>$null | Out-Null
& netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=80 connectaddress=127.0.0.1 connectport=6090 | Out-Null
Write-Log "Port 80 forwards to local CRM port 6090."

Write-Log "Listening ports:"
Get-NetTCPConnection -LocalPort 80,6090,6091 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess |
    Format-Table -AutoSize |
    Out-String |
    ForEach-Object { Write-Log $_ }

Write-Host ""
Write-Host "============================================================"
Write-Host "Real Estate CRM Permanent LAN Access Ready"
Write-Host "============================================================"
Write-Host "Try these URLs from staff computers on the SAME office network:"
Write-Host "  http://$ServerIP/"
Write-Host "  http://$ServerIP`:6090/"
Write-Host ""
Write-Host "If staff computers still cannot ping/open this IP, the router"
Write-Host "is blocking device-to-device traffic. Disable Guest Wi-Fi /"
Write-Host "AP Isolation / Client Isolation on the router, or use the"
Write-Host "remote tunnel option."
Write-Host ""
Write-Host "Log file: $LogPath"
