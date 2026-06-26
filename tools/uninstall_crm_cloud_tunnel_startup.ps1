$ErrorActionPreference = "SilentlyContinue"

$taskName = "Real Estate CRM Cloud Tunnel"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "Removed scheduled task: $taskName"
