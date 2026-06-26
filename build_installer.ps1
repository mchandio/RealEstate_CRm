# Real Estate CRM - Professional Windows Installer Build Script (PowerShell)
# ============================================================================
#
# This script automates the complete build process for creating a 
# production-ready Windows installer.
#
# Usage: 
#   .\build_installer.ps1              (Runs full build)
#   .\build_installer.ps1 -Action check (Runs specific action)
#
# Actions: check, clean, build, stage, installer, all
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('check', 'clean', 'build', 'stage', 'installer', 'all')]
    [string]$Action = 'all',
    
    [Parameter(Mandatory=$false)]
    [switch]$NoWait
)

# Set error handling
$ErrorActionPreference = 'Stop'

# Script configuration
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = (Get-Command python).Source
$projectRoot = Get-Item $scriptDir

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Real Estate CRM - Windows Installer Builder (PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Validate Python installation
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "[✓] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "    Please install Python 3.8+ and add it to your system PATH" -ForegroundColor Yellow
    exit 1
}

# Validate project directory
if (-not (Test-Path "$scriptDir\RealEstateCRM_Qt.spec")) {
    Write-Host "[✗] This script must be run from the project root directory" -ForegroundColor Red
    Write-Host "    Expected to find: RealEstateCRM_Qt.spec" -ForegroundColor Yellow
    exit 1
}

Write-Host "[✓] Project directory: $scriptDir" -ForegroundColor Green
Write-Host "[→] Action: $Action" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Push-Location $scriptDir

try {
    # Execute the Python build script with the specified action
    Write-Host "Executing build process..." -ForegroundColor Cyan
    & python build_installer.py $Action
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Cyan
    
    if ($exitCode -eq 0) {
        Write-Host "[✓] Build process completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Check the 'installer_output' directory for the setup executable" -ForegroundColor White
        Write-Host "  2. Test the installer on a clean Windows system" -ForegroundColor White
        Write-Host "  3. Distribute the installer to users" -ForegroundColor White
        Write-Host ""
        Write-Host "Installer location:" -ForegroundColor Yellow
        Get-ChildItem "$scriptDir\installer_output\*.exe" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  → $($_.FullName)" -ForegroundColor Green
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            Write-Host "    Size: $sizeMB MB" -ForegroundColor Gray
        }
    } else {
        Write-Host "[✗] Build process failed with error code: $exitCode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "  • Ensure all Python packages are installed:" -ForegroundColor White
        Write-Host "    pip install -r requirements.txt" -ForegroundColor Cyan
        Write-Host "  • For installer creation, install Inno Setup:" -ForegroundColor White
        Write-Host "    https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
        Write-Host "  • Check that all required files exist" -ForegroundColor White
    }
    
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    exit $exitCode
}
catch {
    Write-Host "[✗] Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
    
    if (-not $NoWait) {
        Read-Host "Press Enter to exit"
    }
}
