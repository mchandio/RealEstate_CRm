@echo off
REM ========================================================================
REM Real Estate CRM - Professional Windows Installer Build Script
REM ========================================================================
REM
REM This script automates the complete build process for creating a 
REM production-ready Windows installer.
REM
REM Usage: build_installer.bat [check|clean|build|stage|installer|all]
REM
REM Default action (no arguments): Performs full build (all)
REM ========================================================================

setlocal enabledelayedexpansion

REM Set script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Colors for output
set GREEN=[92m
set YELLOW=[93m
set RED=[91m
set RESET=[0m

REM Get action from argument or default to 'all'
if "%1"=="" (
    set ACTION=all
) else (
    set ACTION=%1
)

echo.
echo ========================================================================
echo  Real Estate CRM - Windows Installer Builder
echo ========================================================================
echo.

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your system PATH
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version

REM Check if running from correct directory
if not exist "RealEstateCRM_Qt.spec" (
    echo [ERROR] This script must be run from the project root directory
    echo Expected to find: RealEstateCRM_Qt.spec
    pause
    exit /b 1
)

echo [INFO] Project directory: %CD%
echo.

REM Determine which action to perform
if /i "%ACTION%"=="check" (
    echo [INFO] Checking requirements...
    python build_installer.py check
    goto :end
)

if /i "%ACTION%"=="clean" (
    echo [INFO] Cleaning previous builds...
    python build_installer.py clean
    goto :end
)

if /i "%ACTION%"=="build" (
    echo [INFO] Building executables...
    python build_installer.py build
    goto :end
)

if /i "%ACTION%"=="stage" (
    echo [INFO] Staging files for installer...
    python build_installer.py stage
    goto :end
)

if /i "%ACTION%"=="installer" (
    echo [INFO] Creating Windows installer...
    python build_installer.py installer
    goto :end
)

if /i "%ACTION%"=="all" (
    echo [INFO] Starting complete build process...
    echo.
    python build_installer.py all
    goto :end
)

REM Unknown action
echo [ERROR] Unknown action: %ACTION%
echo.
echo Available actions:
echo   check      - Check all requirements
echo   clean      - Clean previous builds
echo   build      - Build executables only
echo   stage      - Stage files for installer
echo   installer  - Create installer (requires Inno Setup)
echo   all        - Full build process (default)
echo.
pause
exit /b 1

:end
echo.
echo ========================================================================
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Build process completed!
    echo.
    echo Next steps:
    echo 1. Check the 'installer_output' directory for the setup executable
    echo 2. Test the installer on a clean Windows system
    echo 3. Distribute the installer to users
    echo.
) else (
    echo [ERROR] Build process failed with error code: %ERRORLEVEL%
    echo.
    echo Troubleshooting:
    echo - Ensure all Python packages are installed: pip install -r requirements.txt
    echo - For installer creation, install Inno Setup: https://jrsoftware.org/isdl.php
    echo - Check that all required files exist in the project directory
    echo.
)
echo ========================================================================
echo.

REM Keep window open so user can see output
if not "%NOPAUSE%"=="true" (
    pause
)

exit /b %ERRORLEVEL%
