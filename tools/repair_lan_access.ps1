$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$outputsDir = Join-Path $projectRoot "outputs"
$logPath = Join-Path $outputsDir "repair_lan_access.log"
New-Item -ItemType Directory -Force -Path $outputsDir | Out-Null
"Starting CRM LAN access repair: $(Get-Date)" | Set-Content -LiteralPath $logPath -Encoding UTF8

function Write-RepairLog([string]$message) {
    $message | Tee-Object -FilePath $logPath -Append
}

$pythonCandidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

try {
    Get-NetConnectionProfile |
        Where-Object { $_.IPv4Connectivity -ne "Disconnected" } |
        Set-NetConnectionProfile -NetworkCategory Private
    Write-RepairLog "Network profile set to Private."
} catch {
    Write-RepairLog "Network profile could not be changed: $($_.Exception.Message)"
}

$portRules = @(
    @{ Name = "Real Estate CRM Web UI 80"; Port = "80"; Description = "Allow local network devices to open CRM Web UI on standard HTTP port" },
    @{ Name = "Real Estate CRM Web UI 6090"; Port = "6090"; Description = "Allow local network devices to open CRM Web UI on LAN port" },
    @{ Name = "Real Estate CRM Desktop API 6091"; Port = "6091"; Description = "Allow local network devices to reach CRM desktop API" }
)

foreach ($rule in $portRules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Set-NetFirewallRule -Enabled True -Action Allow -Profile Any | Out-Null
        $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $rule.Port | Out-Null
        $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet | Out-Null
        Write-RepairLog "Updated port rule: $($rule.Name)"
    } else {
        New-NetFirewallRule `
            -DisplayName $rule.Name `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $rule.Port `
            -RemoteAddress LocalSubnet `
            -Profile Any `
            -Description $rule.Description | Out-Null
        Write-RepairLog "Created port rule: $($rule.Name)"
    }
}

foreach ($pythonPath in $pythonCandidates) {
    $ruleName = "Real Estate CRM Python Server - $([IO.Path]::GetFileName((Split-Path -Parent $pythonPath)))"
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Set-NetFirewallRule -Enabled True -Action Allow -Profile Any | Out-Null
        $existing | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $pythonPath | Out-Null
        $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet | Out-Null
        Write-RepairLog "Updated program rule: $ruleName -> $pythonPath"
    } else {
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Action Allow `
            -Program $pythonPath `
            -RemoteAddress LocalSubnet `
            -Profile Any `
            -Description "Allow local network devices to reach the CRM Python web server" | Out-Null
        Write-RepairLog "Created program rule: $ruleName -> $pythonPath"
    }
}

try {
    Get-NetFirewallRule -DisplayGroup "Network Discovery" -ErrorAction SilentlyContinue |
        Set-NetFirewallRule -Enabled True -Profile Any | Out-Null
    Write-RepairLog "Network Discovery firewall group enabled."
} catch {
    Write-RepairLog "Network Discovery group could not be enabled: $($_.Exception.Message)"
}

Write-RepairLog "Final listeners:"
Get-NetTCPConnection -LocalPort 80,6090,6091 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess |
    Format-Table -AutoSize |
    Out-String |
    Tee-Object -FilePath $logPath -Append

Write-RepairLog "SUCCESS"
