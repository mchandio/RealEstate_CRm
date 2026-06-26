#!/usr/bin/env python3
"""
Complete Windows Installer Build System for Real Estate CRM
=========================================================

This script handles:
1. Building executables with PyInstaller
2. Staging files for the installer
3. Creating the Windows MSI/EXE installer
4. Cleanup and validation

Run: python build_installer.py [build|stage|installer|all|clean]
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Configuration
class Config:
    PROJECT_ROOT = Path(__file__).parent
    VERSION = "2.1.0"
    APP_NAME = "Real Estate CRM"
    PUBLISHER = "Muhammad Siddique"
    
    # Build directories
    BUILD_DIR = PROJECT_ROOT / "build"
    DIST_DIR = PROJECT_ROOT / "dist"
    INSTALLER_STAGING = PROJECT_ROOT / "installer_staging"
    INSTALLER_OUTPUT = PROJECT_ROOT / "installer_output"
    
    # PyInstaller specs
    QT_SPEC = PROJECT_ROOT / "RealEstateCRM_Qt.spec"
    LAN_SPEC = PROJECT_ROOT / "RealEstateCRM_LAN_Server.spec"
    
    # Source files
    DATABASE_FILE = PROJECT_ROOT / "real_estate_crm.db"
    ICON_DIR = PROJECT_ROOT / "company_logo"
    TOOLS_DIR = PROJECT_ROOT / "tools"
    FRONTEND_DIR = PROJECT_ROOT / "frontend"
    
    # Output files
    SETUP_ISS = PROJECT_ROOT / "RealEstateCRM_Setup_Professional.iss"


class Logger:
    """Simple logging utility"""
    @staticmethod
    def info(msg: str):
        print(f"[INFO] {msg}")
    
    @staticmethod
    def success(msg: str):
        print(f"[OK] {msg}")
    
    @staticmethod
    def error(msg: str):
        print(f"[ERROR] {msg}")
        sys.exit(1)
    
    @staticmethod
    def warning(msg: str):
        print(f"[WARN] {msg}")


class BuildSystem:
    """Manages the complete build process"""
    
    def __init__(self):
        self.config = Config
        self.logger = Logger
    
    def check_requirements(self) -> bool:
        """Verify all required tools and files exist"""
        self.logger.info("Checking requirements...")
        
        # Check Python packages (more lenient check)
        required_packages = ['PyInstaller', 'PySide6']
        missing_packages = []
        
        for package in required_packages:
            try:
                # Try both package name and import name
                try:
                    __import__(package.lower())
                except ImportError:
                    __import__(package)
            except ImportError:
                # Just warn but don't fail - packages might be installed
                self.logger.warning(f"Could not verify {package} - proceeding anyway")
        
        if missing_packages and len(missing_packages) > 2:
            self.logger.error(
                f"Missing packages: {', '.join(missing_packages)}\n"
                f"Run: pip install -r requirements.txt"
            )
            return False
        
        # Check PyInstaller specs
        if not self.config.QT_SPEC.exists():
            self.logger.error(f"PyInstaller spec not found: {self.config.QT_SPEC}")
            return False
        
        if not self.config.LAN_SPEC.exists():
            self.logger.error(f"PyInstaller spec not found: {self.config.LAN_SPEC}")
            return False
        
        # Check Inno Setup compiler
        inno_paths = [
            Path("C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"),
            Path("C:\\Program Files\\Inno Setup 6\\ISCC.exe"),
            Path("C:\\Program Files (x86)\\Inno Setup 5\\ISCC.exe"),
            Path(str(Path.home()) + "\\AppData\\Local\\Programs\\Inno Setup 6\\ISCC.exe"),
        ]
        
        self.inno_compiler = None
        for path in inno_paths:
            if path.exists():
                self.inno_compiler = path
                self.logger.success(f"Found Inno Setup: {path}")
                break
        
        if not self.inno_compiler:
            self.logger.warning(
                "Inno Setup not found. Installer creation will fail.\n"
                "Download from: https://jrsoftware.org/isdl.php"
            )
        
        self.logger.success("All requirements met!")
        return True
    
    def clean_builds(self):
        """Clean previous build artifacts"""
        self.logger.info("Cleaning previous builds...")
        
        dirs_to_clean = [
            self.config.BUILD_DIR,
            self.config.DIST_DIR,
            self.config.INSTALLER_STAGING / "dist"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.logger.success(f"Cleaned: {dir_path}")
        
        self.logger.success("Build cleanup complete!")
    
    def build_executables(self):
        """Build both desktop and LAN server executables"""
        self.logger.info("Building executables...")
        
        # Build Qt Desktop App
        self.logger.info("Building Qt Desktop App...")
        result = self._run_pyinstaller(self.config.QT_SPEC)
        if result != 0:
            self.logger.error("Failed to build Qt application")
        self.logger.success("Qt Desktop App built!")
        
        # Build LAN Server
        self.logger.info("Building LAN Server...")
        result = self._run_pyinstaller(self.config.LAN_SPEC)
        if result != 0:
            self.logger.error("Failed to build LAN Server")
        self.logger.success("LAN Server built!")
    
    def _run_pyinstaller(self, spec_file: Path) -> int:
        """Run PyInstaller with the given spec file"""
        cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--distpath", str(self.config.DIST_DIR),
            "--buildpath", str(self.config.BUILD_DIR),
            str(spec_file)
        ]
        
        return subprocess.call(cmd)
    
    def stage_for_installer(self):
        """Stage all files needed for the installer"""
        self.logger.info("Staging files for installer...")
        
        # Create staging directories
        staging_dist = self.config.INSTALLER_STAGING / "dist"
        staging_dist.mkdir(parents=True, exist_ok=True)
        
        # Copy Qt application
        qt_src = self.config.DIST_DIR / "RealEstateCRM_Qt"
        qt_dst = staging_dist / "RealEstateCRM_Qt"
        
        if qt_src.exists():
            if qt_dst.exists():
                shutil.rmtree(qt_dst)
            shutil.copytree(qt_src, qt_dst)
            self.logger.success(f"Staged Qt app: {qt_dst}")
        else:
            self.logger.error(f"Qt app not found: {qt_src}")
        
        # Copy LAN Server executable
        lan_exe_src = self.config.DIST_DIR / "RealEstateCRM_LAN_Server.exe"
        if lan_exe_src.exists():
            shutil.copy(lan_exe_src, staging_dist / "RealEstateCRM_LAN_Server.exe")
            self.logger.success("Staged LAN Server executable")
        else:
            self.logger.error(f"LAN Server executable not found: {lan_exe_src}")
        
        # Copy database
        if self.config.DATABASE_FILE.exists():
            shutil.copy(
                self.config.DATABASE_FILE,
                self.config.INSTALLER_STAGING / "real_estate_crm.db"
            )
            self.logger.success("Staged database")
        
        self.logger.success("Staging complete!")
    
    def create_installer(self):
        """Create the Windows installer using Inno Setup"""
        if not self.inno_compiler:
            self.logger.error(
                "Inno Setup compiler not found.\n"
                "Download from: https://jrsoftware.org/isdl.php"
            )
        
        self.logger.info("Creating Windows installer...")
        
        # Prepare Inno Setup command
        cmd = [
            str(self.inno_compiler),
            str(self.config.SETUP_ISS),
            f"/DMyAppVersion={self.config.VERSION}"
        ]
        
        result = subprocess.call(cmd)
        
        if result == 0:
            self.logger.success("Installer created successfully!")
            
            # Find and report installer location
            installer_files = list(self.config.INSTALLER_OUTPUT.glob("*.exe"))
            if installer_files:
                latest = max(installer_files, key=lambda p: p.stat().st_mtime)
                self.logger.success(f"Installer location: {latest}")
                self.logger.success(f"Installer size: {latest.stat().st_size / (1024*1024):.2f} MB")
        else:
            self.logger.error("Failed to create installer")
    
    def create_build_info(self):
        """Create a build information file"""
        info = {
            "version": self.config.VERSION,
            "app_name": self.config.APP_NAME,
            "build_date": datetime.now().isoformat(),
            "python_version": sys.version,
            "build_path": str(self.config.INSTALLER_OUTPUT),
            "executables": {
                "desktop": "RealEstateCRM_Qt.exe",
                "lan_server": "RealEstateCRM_LAN_Server.exe"
            }
        }
        
        info_file = self.config.INSTALLER_OUTPUT / "build_info.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        self.logger.success(f"Build info saved: {info_file}")
    
    def run_full_build(self):
        """Execute the complete build process"""
        self.logger.info("Starting complete build process...")
        self.logger.info("=" * 60)
        
        try:
            if not self.check_requirements():
                return False
            
            self.clean_builds()
            self.build_executables()
            self.stage_for_installer()
            self.create_installer()
            self.create_build_info()
            
            self.logger.info("=" * 60)
            self.logger.success("BUILD COMPLETE! ✓")
            self.logger.info(f"Setup executable: {self.config.INSTALLER_OUTPUT}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Build failed: {e}")
            return False


def main():
    """Main entry point"""
    builder = BuildSystem()
    
    if len(sys.argv) < 2:
        action = "all"
    else:
        action = sys.argv[1].lower()
    
    if action == "check":
        builder.check_requirements()
    elif action == "clean":
        builder.clean_builds()
    elif action == "build":
        if builder.check_requirements():
            builder.clean_builds()
            builder.build_executables()
    elif action == "stage":
        builder.stage_for_installer()
    elif action == "installer":
        builder.check_requirements()
        builder.create_installer()
    elif action == "all":
        builder.run_full_build()
    else:
        print(f"Unknown action: {action}")
        print("Available actions: check, clean, build, stage, installer, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
