$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$outputs = Join-Path $root "outputs"
$pidFile = Join-Path $outputs "crm_tunnel.pid.txt"
$serverPidFile = Join-Path $outputs "crm_web.pid.txt"
$serverUrlFile = Join-Path $outputs "crm_web.url.txt"
$urlFile = Join-Path $outputs "crm_tunnel.url.txt"

function Stop-CrmBackendProcess {
    param($Process)
    if ($Process -and [string]$Process.CommandLine -match "backend\.main:app") {
        Stop-Process -Id $Process.ProcessId -Force
        Write-Host "Stopped CRM web server PID $($Process.ProcessId)"
    }
}

function Get-UrlPort {
    param([string]$Url)
    try {
        $uri = [Uri]$Url
        return $uri.Port
    } catch {
        return $null
    }
}

function Get-ListenerProcess {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) {
        return $null
    }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)"
}

if (Test-Path -LiteralPath $pidFile) {
    $pidText = Get-Content -LiteralPath $pidFile | Select-Object -First 1
    if ($pidText -match '^\d+$') {
        Stop-Process -Id ([int]$pidText) -Force
        Write-Host "Stopped CRM tunnel PID $pidText"
    }
}

Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "cloudflared.exe" -and $_.CommandLine -match "tunnel" -and $_.CommandLine -match "127\.0\.0\.1:(6090|609[2-9]|610[0-9])|localhost:(6090|609[2-9]|610[0-9])" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force
        Write-Host "Stopped CRM tunnel PID $($_.ProcessId)"
    }

if (Test-Path -LiteralPath $serverPidFile) {
    $serverPid = Get-Content -LiteralPath $serverPidFile | Select-Object -First 1
    if ($serverPid -match '^\d+$') {
        $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid"
        Stop-CrmBackendProcess $serverProcess
    }
}

$serverPort = $null
if (Test-Path -LiteralPath $serverUrlFile) {
    $serverUrl = Get-Content -LiteralPath $serverUrlFile | Select-Object -First 1
    $serverPort = Get-UrlPort $serverUrl
}

if ($serverPort) {
    Stop-CrmBackendProcess (Get-ListenerProcess -Port $serverPort)
    Get-CimInstance Win32_Process |
        Where-Object {
            [string]$_.CommandLine -match "backend\.main:app" -and
            [string]$_.CommandLine -match "--port\s+$serverPort(\s|$)"
        } |
        ForEach-Object {
            try {
                Stop-Process -Id $_.ProcessId -Force
                Write-Host "Stopped CRM web server PID $($_.ProcessId)"
            } catch {
            }
        }
}

Remove-Item -LiteralPath $pidFile, $serverPidFile, $serverUrlFile, $urlFile -Force
