$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root "tools\start_crm_cloud_tunnel.ps1"
$taskName = "Real Estate CRM Cloud Tunnel"

if (-not (Test-Path -LiteralPath $script)) {
    throw "Tunnel script was not found at $script"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts Real Estate CRM web access through a Cloudflare tunnel at Windows logon." `
    -Force | Out-Null

Write-Host "Installed scheduled task: $taskName"
Write-Host "It will start the CRM tunnel automatically at Windows logon."
