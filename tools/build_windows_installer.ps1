param(
    [string]$Version = "2.1.0",
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root ".venv\Scripts\python.exe"
$staging = Join-Path $root "installer_staging"
$buildQt = Join-Path $staging "build_qt_release"
$buildLan = Join-Path $staging "build_lan_release"
$dist = Join-Path $staging "dist"
$dbSnapshot = Join-Path $staging "real_estate_crm.db"
$installerOut = Join-Path $root "installer_output"
$iss = Join-Path $root "RealEstateCRM_Setup.iss"

function Assert-InWorkspace {
    param([string]$Path)
    $resolvedRoot = [System.IO.Path]::GetFullPath($root)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside workspace: $resolvedPath"
    }
}

function Remove-WorkspaceItem {
    param([string]$Path)
    Assert-InWorkspace $Path
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment was not found at $python"
}

$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $isccCommand) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path -LiteralPath $candidate) {
        $iscc = $candidate
    } else {
        throw "Inno Setup compiler ISCC.exe was not found."
    }
} else {
    $iscc = $isccCommand.Source
}

New-Item -ItemType Directory -Force -Path $staging, $installerOut | Out-Null
Remove-WorkspaceItem $buildQt
Remove-WorkspaceItem $buildLan
Remove-WorkspaceItem $dist
New-Item -ItemType Directory -Force -Path $dist | Out-Null

Push-Location $root
try {
    Write-Host "Checking Python syntax..."
    & $python -m compileall qt_crm_app.py qt_crm_premium_style.py backend crm_core tools
    if ($LASTEXITCODE -ne 0) { throw "Python compile check failed." }

    Write-Host "Creating SQLite release snapshot..."
    & $python -c "import sqlite3, pathlib, sys; src=pathlib.Path(sys.argv[1]); dst=pathlib.Path(sys.argv[2]); dst.unlink(missing_ok=True); con=sqlite3.connect(src); out=sqlite3.connect(dst); con.backup(out); out.close(); con.close()" "real_estate_crm.db" $dbSnapshot
    if ($LASTEXITCODE -ne 0) { throw "SQLite snapshot failed." }

    Write-Host "Building desktop executable..."
    & $python -m PyInstaller --noconfirm --clean --distpath $dist --workpath $buildQt RealEstateCRM_Qt_Release.spec
    if ($LASTEXITCODE -ne 0) { throw "Desktop PyInstaller build failed." }

    Write-Host "Building LAN server executable..."
    & $python -m PyInstaller --noconfirm --clean --distpath $dist --workpath $buildLan RealEstateCRM_LAN_Server.spec
    if ($LASTEXITCODE -ne 0) { throw "LAN server PyInstaller build failed." }

    Write-Host "Compiling Windows installer..."
    & $iscc "/DMyAppVersion=$Version" $iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }

    $installer = Join-Path $installerOut "RealEstateCRM_Setup_v$Version.exe"
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Installer was not created at $installer"
    }

    Write-Host "Installer ready: $installer"

    if ($Install) {
        Write-Host "Installing current build..."
        $process = Start-Process -FilePath $installer -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS") -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Installer exited with code $($process.ExitCode)"
        }
        Write-Host "Install complete."
    }
} finally {
    Pop-Location
}
