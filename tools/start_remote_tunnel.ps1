param(
    [string]$LocalUrl = "http://127.0.0.1:6090"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputsDir = Join-Path $ProjectRoot "outputs"
$CloudflaredPath = Join-Path $ProjectRoot "tools\cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$TunnelLog = Join-Path $OutputsDir "cloudflared_tunnel.log"
$ServerPidFile = Join-Path $OutputsDir "crm_web.pid.txt"
$ServerUrlFile = Join-Path $OutputsDir "crm_web.url.txt"
$ServerOutLog = $null
$ServerErrLog = $null

New-Item -ItemType Directory -Force -Path $OutputsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CloudflaredPath) | Out-Null

function Test-CrmHealth {
    param([string]$Url = $LocalUrl)
    try {
        $response = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 4
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
    if (Test-CrmHealth -Url $LocalUrl) {
        return $LocalUrl
    }

    $listener = Get-ListenerProcess -Port $requestedPort
    if (-not $listener) {
        return $LocalUrl
    }

    if (Test-ProjectUvicornProcess $listener) {
        Write-Host "CRM project server on port $requestedPort is not healthy. Restarting it."
        Stop-ProjectWebServerOnPort -Port $requestedPort | Out-Null
        return (New-CrmLocalUrl -Port $requestedPort)
    }

    $fallbackPort = Find-FreeCrmPort -PreferredPort 6092
    Write-Host "Port $requestedPort is already used by $($listener.Name) PID $($listener.ProcessId)."
    Write-Host "Starting a dedicated remote CRM web server on port $fallbackPort."
    return (New-CrmLocalUrl -Port $fallbackPort)
}

function Start-CrmServer {
    param([string]$Url = $LocalUrl)

    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
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
        $env:CRM_DB_PATH = Join-Path $ProjectRoot "real_estate_crm.db"
        $env:DATABASE_URL = "sqlite:///$($ProjectRoot.Replace('\','/'))/real_estate_crm.db"
        $process = Start-Process -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", [string]$port) `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $ServerOutLog `
            -RedirectStandardError $ServerErrLog `
            -PassThru
        Set-Content -LiteralPath $ServerPidFile -Value $process.Id
        Set-Content -LiteralPath $ServerUrlFile -Value $Url
    } finally {
        foreach ($name in $oldEnv.Keys) {
            if ($null -eq $oldEnv[$name]) {
                Remove-Item -LiteralPath "Env:\$name" -ErrorAction SilentlyContinue
            } else {
                Set-Item -LiteralPath "Env:\$name" -Value $oldEnv[$name]
            }
        }
    }

    for ($i = 0; $i -lt 12; $i++) {
        Start-Sleep -Seconds 1
        if (Test-CrmHealth -Url $Url) {
            return
        }
    }
    throw "CRM web server did not answer on $Url. Check $ServerErrLog"
}

function Save-CrmServerProcess {
    param([int]$Port, [string]$Url)
    $process = Get-ListenerProcess -Port $Port
    if (Test-ProjectUvicornProcess $process) {
        Set-Content -LiteralPath $ServerPidFile -Value $process.ProcessId
        Set-Content -LiteralPath $ServerUrlFile -Value $Url
    }
}

Write-Host "Checking CRM web server..."
$LocalUrl = Resolve-CrmServerUrl
$ServerPort = Get-UrlPort $LocalUrl
$ServerOutLog = Join-Path $OutputsDir "crm_web_$ServerPort.out.log"
$ServerErrLog = Join-Path $OutputsDir "crm_web_$ServerPort.err.log"
if (-not (Test-CrmHealth)) {
    Write-Host "CRM is not answering locally. Starting it now..."
    Start-CrmServer -Url $LocalUrl
}
Save-CrmServerProcess -Port $ServerPort -Url $LocalUrl
Write-Host "CRM is healthy at $LocalUrl"
Write-Host

if (-not (Test-Path -LiteralPath $CloudflaredPath)) {
    Write-Host "Downloading Cloudflare tunnel helper..."
    Write-Host $DownloadUrl
    & curl.exe -L --fail --output $CloudflaredPath $DownloadUrl
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $CloudflaredPath)) {
        throw "Could not download cloudflared.exe"
    }
}

"" | Set-Content -LiteralPath $TunnelLog -Encoding UTF8
Write-Host "============================================================"
Write-Host "Real Estate CRM Remote Access"
Write-Host "============================================================"
Write-Host "Keep this window open."
Write-Host "Copy the https://...trycloudflare.com URL shown below and send it to users."
Write-Host "Users will still need their CRM username and password."
Write-Host "Press Ctrl+C in this window to stop remote access."
Write-Host "============================================================"
Write-Host

& $CloudflaredPath tunnel --url $LocalUrl --no-autoupdate --logfile $TunnelLog --loglevel info
