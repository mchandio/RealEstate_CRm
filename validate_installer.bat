@echo off
REM ========================================================================
REM Real Estate CRM - Installer Validation & Verification Script
REM ========================================================================
REM
REM This script validates the built installer before distribution.
REM Checks for common issues and verifies the installer is working.
REM
REM Usage: validate_installer.bat
REM ========================================================================

setlocal enabledelayedexpansion

REM Set script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ========================================================================
echo  Real Estate CRM - Installer Validation
echo ========================================================================
echo.

REM Check if installer exists
if not exist "installer_output\*.exe" (
    echo [ERROR] No installer found in installer_output directory
    echo Please run: build_installer.bat all
    pause
    exit /b 1
)

REM Get the latest installer
for /f "delims=" %%A in ('dir /B /O-D "installer_output\*.exe" ^| findstr /V ".log"') do (
    set INSTALLER=%%A
    goto found_installer
)

:found_installer
set INSTALLER_PATH=installer_output\%INSTALLER%

echo [INFO] Found installer: %INSTALLER%
echo [INFO] Location: %INSTALLER_PATH%
echo.

REM Get file size
for %%A in ("%INSTALLER_PATH%") do (
    set INSTALLER_SIZE=%%~zA
    echo [INFO] File size: !INSTALLER_SIZE! bytes
    set SIZE_MB=!INSTALLER_SIZE:~0,-6!
    if "!SIZE_MB!"=="" set SIZE_MB=0
    echo [INFO] Size (approx): !SIZE_MB! MB
)

REM Check if reasonable size (should be 200-500 MB)
if %INSTALLER_SIZE% LSS 52428800 (
    echo [WARNING] Installer is unusually small (less than 50 MB)
    echo           This may indicate a build error
)
if %INSTALLER_SIZE% GTR 1048576000 (
    echo [WARNING] Installer is unusually large (more than 1 GB)
    echo           Consider cleaning and rebuilding
)

echo.
echo ========================================================================
echo  Validation Checks
echo ========================================================================
echo.

REM Check 1: File integrity
echo [1] Checking file integrity...
if exist "%INSTALLER_PATH%" (
    echo [PASS] Installer file exists
) else (
    echo [FAIL] Installer file not found
    goto validation_failed
)

REM Check 2: Executable header
echo [2] Checking if valid executable...
for /f "tokens=*" %%A in ('wmic datafile where name^="%INSTALLER_PATH:\=\\%" get description 2^>nul') do (
    if "%%A" neq "" (
        echo [PASS] Valid Windows executable
    )
)

REM Check 3: Dependencies exist
echo [3] Checking build dependencies...
if exist "installer_staging\dist\RealEstateCRM_Qt" (
    echo [PASS] Qt application found
) else (
    echo [WARNING] Qt application not in staging
)

if exist "installer_staging\dist\RealEstateCRM_LAN_Server.exe" (
    echo [PASS] LAN server executable found
) else (
    echo [WARNING] LAN server not in staging
)

if exist "installer_staging\real_estate_crm.db" (
    echo [PASS] Database file found
) else (
    echo [WARNING] Database file not in staging
)

REM Check 4: Resources
echo [4] Checking resources...
if exist "company_logo\RealEstateCRM.ico" (
    echo [PASS] Icon file found
) else (
    echo [WARNING] Icon file missing
)

REM Check 5: Documentation
echo [5] Checking documentation...
if exist "README.md" (
    echo [PASS] README found
) else (
    echo [WARNING] README missing
)

if exist "LAN_MULTIUSER_SETUP.md" (
    echo [PASS] Setup guide found
) else (
    echo [WARNING] Setup guide missing
)

echo.
echo ========================================================================
echo  Pre-Distribution Checklist
echo ========================================================================
echo.

echo [ ] Installer file size reasonable (200-500 MB)
echo     Current: %SIZE_MB% MB
echo.
echo [ ] Test installer on clean Windows system (recommended)
echo [ ] Verify application launches after installation
echo [ ] Verify LAN server starts correctly
echo [ ] Verify database file created
echo [ ] Verify Start Menu shortcuts appear
echo [ ] Verify desktop shortcuts created (if selected)
echo [ ] Test uninstall (data should be preserved)
echo [ ] Check antivirus doesn't flag installer
echo [ ] Review RELEASE_NOTES_TEMPLATE.md
echo [ ] Document system requirements
echo [ ] Plan distribution method
echo [ ] Create user documentation
echo [ ] Notify support team
echo.

echo ========================================================================
echo  Distribution Ready
echo ========================================================================
echo.

echo Installer location:
echo   %CD%\%INSTALLER_PATH%
echo.
echo Ready to distribute! Next steps:
echo   1. Copy installer to distribution location
echo   2. Create download link (if online)
echo   3. Send to users with RELEASE_NOTES_TEMPLATE.md
echo   4. Update version numbers in build system
echo   5. Archive this build for future reference
echo.
echo Optional:
echo   • Code sign the installer (for production)
echo   • Create checksums (MD5/SHA256)
echo   • Upload to release server
echo   • Announce on social media/email
echo.

echo ========================================================================
echo.

REM Check for build info
if exist "installer_output\build_info.json" (
    echo [INFO] Build info found:
    type "installer_output\build_info.json"
    echo.
)

echo [SUCCESS] Validation complete!
echo [INFO] Installer is ready for distribution
echo.

pause
exit /b 0

:validation_failed
echo.
echo [FAILED] Validation errors found
echo Please review the errors above and rebuild the installer
echo.
pause
exit /b 1
