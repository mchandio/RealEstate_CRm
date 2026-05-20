param(
    [string]$LocalUrl = "http://127.0.0.1:6090"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputsDir = Join-Path $ProjectRoot "outputs"
$CloudflaredPath = Join-Path $ProjectRoot "tools\cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$TunnelLog = Join-Path $OutputsDir "cloudflared_tunnel.log"
$ServerOutLog = Join-Path $OutputsDir "crm_web_6090.out.log"
$ServerErrLog = Join-Path $OutputsDir "crm_web_6090.err.log"

New-Item -ItemType Directory -Force -Path $OutputsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CloudflaredPath) | Out-Null

function Test-CrmHealth {
    try {
        $response = Invoke-WebRequest -Uri "$LocalUrl/api/health" -UseBasicParsing -TimeoutSec 4
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-CrmServer {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python environment not found at $python"
    }

    $command = @"
Set-Location '$ProjectRoot'
`$env:API_HOST='0.0.0.0'
`$env:API_PORT='6090'
`$env:CRM_DB_PATH='$ProjectRoot\real_estate_crm_exp.db'
`$env:DATABASE_URL='sqlite:///$($ProjectRoot.Replace('\','/'))/real_estate_crm_exp.db'
& '$python' -m uvicorn backend.main:app --host 0.0.0.0 --port 6090
"@
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
        -WindowStyle Hidden `
        -RedirectStandardOutput $ServerOutLog `
        -RedirectStandardError $ServerErrLog | Out-Null

    for ($i = 0; $i -lt 12; $i++) {
        Start-Sleep -Seconds 1
        if (Test-CrmHealth) {
            return
        }
    }
    throw "CRM web server did not answer on $LocalUrl. Check $ServerErrLog"
}

Write-Host "Checking CRM web server..."
if (-not (Test-CrmHealth)) {
    Write-Host "CRM is not answering locally. Starting it now..."
    Start-CrmServer
}
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
