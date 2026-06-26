# Windows Installer Setup Guide - Real Estate CRM

## Quick Start

### Prerequisites
Before building the installer, ensure you have:

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
   - Add Python to PATH during installation
   
2. **All Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Inno Setup 6** - [Download](https://jrsoftware.org/isdl.php)
   - Required for creating the Windows installer (.exe)
   - Install to default location (C:\Program Files (x86)\Inno Setup 6)

4. **PyInstaller** - Included in requirements.txt
   ```bash
   pip install pyinstaller
   ```

## Building the Installer

### Option 1: Using Batch File (Windows CMD)

```bash
# Open Command Prompt and run:
cd C:\path\to\RealEstate_CRM
build_installer.bat

# Or with specific action:
build_installer.bat all         # Full build (default)
build_installer.bat check       # Check requirements only
build_installer.bat clean       # Clean previous builds
build_installer.bat build       # Build executables only
build_installer.bat stage       # Stage files for installer
build_installer.bat installer   # Create installer only
```

### Option 2: Using PowerShell

```powershell
# Open PowerShell and run:
cd C:\path\to\RealEstate_CRM
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
.\build_installer.ps1

# Or with specific action:
.\build_installer.ps1 -Action all
.\build_installer.ps1 -Action check
.\build_installer.ps1 -Action build
```

### Option 3: Using Python Directly

```bash
# Full build
python build_installer.py all

# Specific steps
python build_installer.py check       # Verify requirements
python build_installer.py clean       # Clean old builds
python build_installer.py build       # Build executables
python build_installer.py stage       # Stage files
python build_installer.py installer   # Create installer
```

## Build Process Steps

The complete build performs these steps:

### 1. **Check Requirements** (`check`)
   - Verifies Python packages (PyInstaller, PySide6)
   - Checks for PyInstaller spec files
   - Locates Inno Setup compiler
   - **Output**: Console report of what's missing

### 2. **Clean Previous Builds** (`clean`)
   - Removes old build artifacts
   - Clears dist/ and build/ directories
   - **Time**: ~2 seconds
   - **Output**: Cleaned directories listed

### 3. **Build Executables** (`build`)
   - **Desktop App**: Creates RealEstateCRM_Qt.exe
     - Bundles Qt framework and all dependencies
     - Single-file or folder deployment
     - **Time**: 5-15 minutes
   
   - **LAN Server**: Creates RealEstateCRM_LAN_Server.exe
     - Bundles FastAPI backend
     - Database and frontend files
     - **Time**: 3-8 minutes
   
   - **Output**: Executables in `dist/latest/`

### 4. **Stage Files** (`stage`)
   - Copies executables to installer staging area
   - Includes database, icons, and tools
   - Prepares everything for Inno Setup
   - **Output**: `installer_staging/dist/`

### 5. **Create Installer** (`installer`)
   - Runs Inno Setup compiler
   - Creates RealEstateCRM_v2.1.0_Setup.exe
   - **Output**: `installer_output/` directory
   - **Size**: ~200-400 MB (depends on dependencies)

### 6. **Build Info** 
   - Creates build_info.json with version and build metadata
   - Useful for deployment tracking

## Output Files

After a successful build, you'll have:

```
installer_output/
├── RealEstateCRM_v2.1.0_Setup.exe    (Main installer - ~300 MB)
├── build_info.json                    (Build metadata)
└── RealEstateCRM_v2.1.0_Setup.exe.log (Build log)

dist/latest/
├── RealEstateCRM_Qt/                  (Desktop app folder)
│   ├── RealEstateCRM_Qt.exe          (Main executable)
│   ├── python*.dll
│   ├── PySide6/
│   └── ...
└── RealEstateCRM_LAN_Server.exe       (LAN server executable)

installer_staging/
└── dist/
    ├── RealEstateCRM_Qt/
    ├── RealEstateCRM_LAN_Server.exe
    └── real_estate_crm.db
```

## Installer Features

The generated Windows installer includes:

### Desktop Shortcuts
- ✓ Real Estate CRM (main application)
- ✓ CRM LAN Web Server
- ✓ Open CRM Web (local access)
- ✓ Firewall Configuration

### Installation Options
- **Install Location**: `C:\Users\[User]\AppData\Local\Programs\Real Estate CRM`
- **Desktop Icon**: Optional (checkbox)
- **Quick Launch Icon**: Optional (Windows 7/8)
- **Auto-start LAN Server**: Optional (checkbox)
- **Remote Tunnel**: Optional setup

### Post-Installation
- Database is automatically copied (if not already present)
- User data preserved on upgrades
- Launch options available after installation
- Documentation accessible from Start Menu

### Features
- LZMA2 Ultra compression (smaller file size)
- Modern wizard interface
- Automatic cleanup of old versions
- Registry entries for system integration
- Uninstall support with data preservation options

## Customization

### Change Version Number

Edit `build_installer.py`:
```python
class Config:
    VERSION = "2.2.0"  # Change this
```

### Change Installation Directory

Edit `RealEstateCRM_Setup_Professional.iss`:
```ini
DefaultDirName={localappdata}\Programs\Your App Name
```

### Add Additional Files

1. Place files in your project
2. Add to `RealEstateCRM_Setup_Professional.iss`:
```ini
[Files]
Source: "path\to\your\file"; DestDir: "{app}\subfolder"; Flags: ignoreversion
```

### Customize Shortcuts

Edit `[Icons]` section in the .iss file:
```ini
[Icons]
Name: "{group}\Your App"; Filename: "{app}\app.exe"; WorkingDir: "{app}"
```

## Troubleshooting

### Error: "Python not found"
**Solution**:
1. Install Python from python.org
2. During installation, check "Add Python to PATH"
3. Restart Command Prompt/PowerShell

### Error: "PyInstaller not found"
**Solution**:
```bash
pip install pyinstaller
pip install -r requirements.txt
```

### Error: "Inno Setup compiler not found"
**Solution**:
1. Download from https://jrsoftware.org/isdl.php
2. Install to default location: `C:\Program Files (x86)\Inno Setup 6`
3. Or modify `Config.inno_compiler` path in `build_installer.py`

### Error: "PyInstaller spec file not found"
**Solution**:
- Ensure you're running from the project root directory
- Files should be: `RealEstateCRM_Qt.spec` and `RealEstateCRM_LAN_Server.spec`

### Error: "Module not found during build"
**Solution**:
1. Verify all modules are installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Add missing modules to hiddenimports in the .spec file:
   ```python
   hiddenimports=[
       'module_name',
       'another_module'
   ]
   ```
3. Rebuild

### Build takes too long
**Tips**:
- First build is slower (downloads all dependencies)
- Subsequent builds are faster due to caching
- Consider running on an SSD for faster builds
- You can skip the clean step: `python build_installer.py build`

### Installer is too large
**Tips**:
- The executable includes all Python and Qt libraries (~200-300 MB)
- Use the LZMA2 compression in Inno Setup (already enabled)
- Consider using the standalone folder distribution instead

## Distribution

### For End Users

Share the installer executable:
```
RealEstateCRM_v2.1.0_Setup.exe
```

**Installation Instructions for Users**:
1. Download the installer
2. Double-click to run
3. Follow the on-screen wizard
4. Choose installation location
5. Select additional options (desktop shortcuts, auto-start, etc.)
6. Click Install
7. Application shortcuts appear in Start Menu

### For IT Departments (Silent Installation)

**Silent installation (no user interaction)**:
```bash
RealEstateCRM_v2.1.0_Setup.exe /SILENT /SP- /NORESTART
```

**Options**:
- `/SILENT` - Silent mode
- `/VERYSILENT` - Very silent mode
- `/SP-` - Don't show "Setup Complete" page
- `/NORESTART` - Don't restart after installation
- `/D=C:\InstallPath` - Custom installation directory

**Example**:
```batch
@echo off
REM Enterprise deployment script
REM Install for all users (requires admin)

cd C:\SoftwareShare
RealEstateCRM_v2.1.0_Setup.exe /SILENT /SP- /NORESTART /D=C:\Program Files\RealEstateCRM

if %errorlevel% equ 0 (
    echo Installation successful
) else (
    echo Installation failed with code %errorlevel%
)
```

## Post-Installation Verification

After installation, verify:

1. **Desktop Shortcut Works**
   - Click "Real Estate CRM" on desktop
   - Application should launch

2. **LAN Server Works**
   - Click "CRM LAN Web Server" shortcut
   - Console window should open
   - Navigate to http://127.0.0.1:6090
   - Web interface should load

3. **Database Exists**
   - Check: `C:\Users\[User]\AppData\Local\Programs\Real Estate CRM\real_estate_crm.db`

4. **Uninstall Works**
   - Control Panel → Programs → Real Estate CRM
   - Click Uninstall
   - Should complete successfully
   - User data preserved in outputs folder

## Advanced: Code Signing

For production releases, consider code signing to avoid Windows SmartScreen warnings:

1. Obtain a code signing certificate
2. Install certificate on your build machine
3. Modify `build_installer.py` to sign the exe:
```python
subprocess.call([
    'signtool', 'sign', 
    '/f', 'certificate.pfx',
    '/p', 'password',
    str(exe_path)
])
```

## Support & Resources

- **PyInstaller**: https://pyinstaller.readthedocs.io/
- **Inno Setup**: https://jrsoftware.org/isinfo.php
- **PySide6**: https://doc.qt.io/qtforpython/
- **Python**: https://docs.python.org/

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-06-05 | Professional installer build system |
| 2.0.0 | 2026-05-24 | LAN server support |
| 1.0.0 | 2026-01-01 | Initial release |

---

**Last Updated**: 2026-06-05  
**Created by**: Muhammad Siddique  
**Support**: info@msxhan.online
