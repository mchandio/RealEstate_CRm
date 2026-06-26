param(
    [string]$LocalUrl = "http://127.0.0.1:6090",
    [int]$StartupWaitSeconds = 45
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$cloudflared = Join-Path $root "tools\cloudflared.exe"
$downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$outputs = Join-Path $root "outputs"
$outLog = Join-Path $outputs "crm_tunnel.out.log"
$errLog = Join-Path $outputs "crm_tunnel.err.log"
$urlFile = Join-Path $outputs "crm_tunnel.url.txt"
$pidFile = Join-Path $outputs "crm_tunnel.pid.txt"
$serverPidFile = Join-Path $outputs "crm_web.pid.txt"
$serverUrlFile = Join-Path $outputs "crm_web.url.txt"
$serverOutLog = $null
$serverErrLog = $null

function Test-CrmHealth {
    param([string]$Url = $LocalUrl)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$Url/api/health" -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-UrlPort {
    param([string]$Url)
    try {
        $uri = [Uri]$Url
    } catch {
        throw "Invalid local CRM URL: $Url"
    }
    if ($uri.Port -gt 0) {
        return $uri.Port
    }
    if ($uri.Scheme -eq "https") {
        return 443
    }
    return 80
}

function New-CrmLocalUrl {
    param([int]$Port)
    return "http://127.0.0.1:$Port"
}

function Get-ListenerProcess {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) {
        return $null
    }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
}

function Test-ProjectUvicornProcess {
    param($Process)
    if (-not $Process) {
        return $false
    }
    $commandLine = [string]$Process.CommandLine
    return $commandLine -match "backend\.main:app"
}

function Stop-ProjectWebServerOnPort {
    param([int]$Port)
    $process = Get-ListenerProcess -Port $Port
    if (-not (Test-ProjectUvicornProcess $process)) {
        return $false
    }
    Stop-Process -Id $process.ProcessId -Force
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-ListenerProcess -Port $Port)) {
            return $true
        }
    }
    return $true
}

function Find-FreeCrmPort {
    param([int]$PreferredPort)
    if (-not (Get-ListenerProcess -Port $PreferredPort)) {
        return $PreferredPort
    }
    foreach ($port in 6092..6109) {
        if (-not (Get-ListenerProcess -Port $port)) {
            return $port
        }
    }
    throw "No free CRM web port found between 6092 and 6109."
}

function Resolve-CrmServerUrl {
    $requestedPort = Get-UrlPort $LocalUrl
    if (Stop-ProjectWebServerOnPort -Port $requestedPort) {
        return (New-CrmLocalUrl -Port $requestedPort)
    }

    $listener = Get-ListenerProcess -Port $requestedPort
    if (-not $listener) {
        return $LocalUrl
    }

    $fallbackPort = Find-FreeCrmPort -PreferredPort 6092
    Write-Host "Port $requestedPort is already used by $($listener.Name) PID $($listener.ProcessId)."
    Write-Host "Starting a dedicated remote CRM web server on port $fallbackPort."
    return (New-CrmLocalUrl -Port $fallbackPort)
}

function Start-CrmWebServer {
    param([string]$Url = $LocalUrl)

    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python environment not found at $python"
    }

    $port = Get-UrlPort $Url
    $oldEnv = @{
        API_HOST = $env:API_HOST
        API_PORT = $env:API_PORT
        CRM_DB_PATH = $env:CRM_DB_PATH
        DATABASE_URL = $env:DATABASE_URL
    }
    try {
        $env:API_HOST = "0.0.0.0"
        $env:API_PORT = [string]$port
        $env:CRM_DB_PATH = Join-Path $root "real_estate_crm.db"
        $env:DATABASE_URL = "sqlite:///$($root.Replace('\','/'))/real_estate_crm.db"
        $process = Start-Process `
            -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", [string]$port) `
            -WorkingDirectory $root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $serverOutLog `
            -RedirectStandardError $serverErrLog `
            -PassThru
        Set-Content -LiteralPath $serverPidFile -Value $process.Id
        Set-Content -LiteralPath $serverUrlFile -Value $Url
    } finally {
        foreach ($name in $oldEnv.Keys) {
            if ($null -eq $oldEnv[$name]) {
                Remove-Item -LiteralPath "Env:\$name" -ErrorAction SilentlyContinue
            } else {
                Set-Item -LiteralPath "Env:\$name" -Value $oldEnv[$name]
            }
        }
    }
}

function Save-CrmServerProcess {
    param([int]$Port, [string]$Url)
    $process = Get-ListenerProcess -Port $Port
    if (Test-ProjectUvicornProcess $process) {
        Set-Content -LiteralPath $serverPidFile -Value $process.ProcessId
        Set-Content -LiteralPath $serverUrlFile -Value $Url
    }
}

New-Item -ItemType Directory -Force -Path $outputs | Out-Null

if (-not (Test-Path -LiteralPath $cloudflared)) {
    Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $cloudflared -TimeoutSec 120
}

$LocalUrl = Resolve-CrmServerUrl
$serverPort = Get-UrlPort $LocalUrl
$serverOutLog = Join-Path $outputs "crm_web_$serverPort.out.log"
$serverErrLog = Join-Path $outputs "crm_web_$serverPort.err.log"

if (-not (Test-CrmHealth)) {
    Start-CrmWebServer -Url $LocalUrl
    $deadline = (Get-Date).AddSeconds($StartupWaitSeconds)
    while ((Get-Date) -lt $deadline -and -not (Test-CrmHealth)) {
        Start-Sleep -Seconds 1
    }
}

if (-not (Test-CrmHealth)) {
    throw "CRM web server is not reachable at $LocalUrl. Check $serverErrLog"
}
Save-CrmServerProcess -Port $serverPort -Url $LocalUrl

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($oldPid -match '^\d+$') {
        Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
    }
}

Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "cloudflared.exe" -and $_.CommandLine -match "tunnel" -and $_.CommandLine -match "127\.0\.0\.1:(6090|609[2-9]|610[0-9])|localhost:(6090|609[2-9]|610[0-9])" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Remove-Item -LiteralPath $outLog, $errLog, $urlFile, $pidFile -ErrorAction SilentlyContinue

$process = Start-Process `
    -FilePath $cloudflared `
    -ArgumentList @("tunnel", "--url", $LocalUrl, "--no-autoupdate") `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

$deadline = (Get-Date).AddSeconds(45)
$url = $null
while ((Get-Date) -lt $deadline -and -not $url) {
    Start-Sleep -Seconds 1
    $text = ""
    if (Test-Path $errLog) { $text += Get-Content $errLog -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $outLog) { $text += Get-Content $outLog -Raw -ErrorAction SilentlyContinue }
    $match = [regex]::Match($text, "https://[-a-zA-Z0-9]+\.trycloudflare\.com")
    if ($match.Success) {
        $url = $match.Value
    }
}

if (-not $url) {
    throw "Tunnel process started with PID $($process.Id), but no URL appeared. Check $errLog"
}

Set-Content -LiteralPath $urlFile -Value $url
Set-Content -LiteralPath $pidFile -Value $process.Id
Write-Host "CRM tunnel is running."
Write-Host "PID: $($process.Id)"
Write-Host "Local CRM server: $LocalUrl"
Write-Host "URL: $url"
