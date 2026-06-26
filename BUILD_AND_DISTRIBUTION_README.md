# Real Estate CRM - Build & Distribution Files

This directory contains the complete Windows installer build system for Real Estate CRM.

## 🚀 Quick Start

### For Developers: Build the Installer

**Option 1: Batch File (Windows CMD)**
```cmd
build_installer.bat
```

**Option 2: PowerShell**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
.\build_installer.ps1
```

**Option 3: Python**
```bash
python build_installer.py all
```

The build process will:
1. ✓ Verify all requirements
2. ✓ Build executables with PyInstaller
3. ✓ Stage files for installer
4. ✓ Create Windows Setup.exe using Inno Setup
5. ✓ Output installer to `installer_output/` folder

### For End Users: Install the Application

1. Download: `RealEstateCRM_v2.1.0_Setup.exe`
2. Double-click to run installer
3. Follow the on-screen wizard
4. Done! Launch from Start Menu or desktop shortcut

## 📋 Files in This Directory

### Build Scripts
- **build_installer.py** - Main Python build system
- **build_installer.bat** - Windows CMD batch file wrapper
- **build_installer.ps1** - PowerShell wrapper script

### Installation Scripts  
- **RealEstateCRM_Setup.iss** - Original Inno Setup configuration
- **RealEstateCRM_Setup_Professional.iss** - Enhanced Inno Setup (recommended)

### Documentation
- **INSTALLER_BUILD_GUIDE.md** - Complete build instructions
- **DEPLOYMENT_CHECKLIST.md** - Installation and setup guide
- **This file** - Overview and quick reference

### PyInstaller Specifications
- **RealEstateCRM_Qt.spec** - Desktop app build configuration
- **RealEstateCRM_LAN_Server.spec** - Web server build configuration

## 📁 Directory Structure

After building, you'll have:

```
RealEstate_CRM/
├── build_installer.py              ← Main build script
├── build_installer.bat             ← Batch wrapper
├── build_installer.ps1             ← PowerShell wrapper
├── RealEstateCRM_Qt.spec           ← Desktop app spec
├── RealEstateCRM_LAN_Server.spec   ← Server app spec
├── RealEstateCRM_Setup.iss         ← Installer config
├── RealEstateCRM_Setup_Professional.iss  ← Enhanced config
├── INSTALLER_BUILD_GUIDE.md        ← Build documentation
├── DEPLOYMENT_CHECKLIST.md         ← Deployment guide
│
├── installer_output/               ← Final installer files
│   ├── RealEstateCRM_v2.1.0_Setup.exe   ← Main setup
│   ├── RealEstateCRM_v2.1.0_Setup.exe.log
│   └── build_info.json
│
├── dist/latest/                    ← Built executables
│   ├── RealEstateCRM_Qt/           ← Desktop app
│   │   ├── RealEstateCRM_Qt.exe
│   │   ├── python*.dll
│   │   ├── PySide6/
│   │   └── ...
│   └── RealEstateCRM_LAN_Server.exe
│
└── installer_staging/              ← Staged files
    ├── dist/
    │   ├── RealEstateCRM_Qt/
    │   ├── RealEstateCRM_LAN_Server.exe
    │   └── ...
    └── real_estate_crm.db
```

## 🔧 Prerequisites

### Required Software
1. **Python 3.8+**
   - Download: https://www.python.org/downloads/
   - Must include pip package manager
   - Add to PATH during installation

2. **Inno Setup 6**
   - Download: https://jrsoftware.org/isdl.php
   - Install to: `C:\Program Files (x86)\Inno Setup 6`

3. **Python Packages**
   ```bash
   pip install -r requirements.txt
   ```
   Key packages:
   - PyInstaller (executable builder)
   - PySide6 (Qt framework)
   - FastAPI (web framework)
   - SQLAlchemy (database)

### System Requirements
- Windows 10 or 11 (64-bit)
- 4 GB RAM (for building)
- 2 GB free disk space
- Administrator access

## ⚡ Build Commands Reference

### Full Build (Everything)
```bash
# CMD
build_installer.bat all

# PowerShell
.\build_installer.ps1 -Action all

# Python
python build_installer.py all
```

### Check Requirements Only
```bash
python build_installer.py check
```

### Clean Old Builds
```bash
python build_installer.py clean
```

### Build Executables Only
```bash
python build_installer.py build
```
Duration: 8-20 minutes (first build slower)

### Stage Files for Installer
```bash
python build_installer.py stage
```

### Create Installer Only
```bash
python build_installer.py installer
```
Requires: Inno Setup installed

## 🎯 What Gets Built

### Desktop Application (RealEstateCRM_Qt.exe)
- Pure Python desktop app using PySide6
- Standalone executable with all dependencies
- Database: SQLite (included)
- Size: ~150-200 MB
- Launch: Single click, no additional setup

### LAN Web Server (RealEstateCRM_LAN_Server.exe)
- FastAPI web application
- Multi-user support over local network
- Web interface: Port 6090
- Size: ~100-150 MB
- Launch: Runs in console window

### Windows Installer (.exe)
- Bundles both applications
- Silent installation support
- Auto-update capability
- Uninstall support
- Size: ~200-400 MB (compressed)

## 📊 Build Performance

| Step | Time | Size |
|------|------|------|
| Check Requirements | 5 sec | N/A |
| Clean | 2 sec | N/A |
| Build Desktop App | 10-15 min | 150-200 MB |
| Build LAN Server | 5-8 min | 100-150 MB |
| Stage Files | 1 min | ~300 MB |
| Create Installer | 2-3 min | 200-400 MB |
| **Total** | **20-35 min** | **~400 MB** |

First build takes longer. Subsequent builds reuse cache and are faster.

## 🐛 Troubleshooting

### Python Not Found
```
[ERROR] Python is not installed or not in PATH
```
**Solution**: Install Python from python.org and add to PATH

### Inno Setup Not Found
```
[WARNING] Inno Setup not found
```
**Solution**: Download and install from https://jrsoftware.org/isdl.php

### Module Not Found
```
ModuleNotFoundError: No module named 'PySide6'
```
**Solution**:
```bash
pip install -r requirements.txt
```

### Spec File Not Found
```
FileNotFoundError: RealEstateCRM_Qt.spec
```
**Solution**: Run script from project root directory

### Permission Denied
```
Permission denied: 'build_installer.bat'
```
**Solution**: 
- PowerShell: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser`
- Or: Right-click Python file → Properties → Run as administrator

## 📝 Customization

### Change App Version
Edit `build_installer.py`:
```python
class Config:
    VERSION = "2.2.0"  # Change this
```

### Change Installer Output
Edit `RealEstateCRM_Setup_Professional.iss`:
```ini
OutputDir=my_installers
OutputBaseFilename=MyApp_Setup_v{#MyAppVersion}
```

### Add Files to Installer
Edit `[Files]` section in .iss file:
```ini
[Files]
Source: "path\to\file"; DestDir: "{app}\subfolder"; Flags: ignoreversion
```

### Modify Start Menu Shortcuts
Edit `[Icons]` section in .iss file:
```ini
[Icons]
Name: "{group}\My Shortcut"; Filename: "{app}\app.exe"
```

## 🚢 Distribution

### For Single User
1. Build installer: `python build_installer.py all`
2. Find: `installer_output/RealEstateCRM_v2.1.0_Setup.exe`
3. Share with user or copy to USB

### For Multiple Users
Use silent installation:
```batch
RealEstateCRM_v2.1.0_Setup.exe /SILENT /SP- /NORESTART
```

### For Corporate Deployment
1. Host installer on network share
2. Use Group Policy or deployment tool
3. Command for automated install:
   ```batch
   \\server\share\RealEstateCRM_v2.1.0_Setup.exe /SILENT /SP- /NORESTART /D=C:\Program Files\RealEstateCRM
   ```

## ✅ Verification Checklist

After building:
- [ ] Installer file created (installer_output/*.exe)
- [ ] Installer size is reasonable (200-400 MB)
- [ ] Can run installer without errors
- [ ] Application launches after installation
- [ ] LAN server starts correctly
- [ ] Database file exists
- [ ] Start Menu shortcuts appear
- [ ] Desktop shortcuts created (if selected)
- [ ] Uninstall works cleanly

## 🔐 Security Notes

- Executables include all Python/Qt libraries
- No separate runtime installation required
- Database encrypted at rest (if configured)
- Firewall port 6090 for LAN only (by default)
- Code signing recommended for production

## 📞 Support

### Common Issues
See **DEPLOYMENT_CHECKLIST.md** for troubleshooting

### Build Issues
1. Check all prerequisites installed
2. Run: `python build_installer.py check`
3. Review build logs
4. Check error messages carefully

### Runtime Issues
1. Check: `Windows Event Viewer`
2. Check: Application logs in installation folder
3. Verify: Database file exists and accessible
4. Try: Reinstall application

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **INSTALLER_BUILD_GUIDE.md** | Complete build instructions |
| **DEPLOYMENT_CHECKLIST.md** | Installation and setup guide |
| **README.md** | Project overview |
| **QUICKSTART.md** | Quick start guide |
| **LAN_MULTIUSER_SETUP.md** | Network setup guide |

## 🎓 Learn More

- **PyInstaller**: https://pyinstaller.readthedocs.io/
- **Inno Setup**: https://jrsoftware.org/isinfo.php  
- **PySide6**: https://doc.qt.io/qtforpython/
- **FastAPI**: https://fastapi.tiangolo.com/

## 📜 Version History

| Version | Date | Notes |
|---------|------|-------|
| 2.1.0 | 2026-06-05 | Professional installer build system |
| 2.0.0 | 2026-05-24 | Multi-user LAN support |
| 1.0.0 | 2026-01-01 | Initial release |

---

**Last Updated**: 2026-06-05  
**Creator**: Muhammad Siddique  
**Email**: info@msxhan.online  
**License**: [Your License Here]
