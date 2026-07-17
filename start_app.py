#!/usr/bin/env python3
"""
Real Estate CRM - Cross-Platform Startup Script
================================================
This script:
1. Detects the operating system (Windows, macOS, Linux, Raspberry Pi)
2. Creates a virtual environment if it doesn't exist
3. Installs dependencies from requirements.txt
4. Starts the web server on port 6090

Usage:
    python start_app.py          # Start with default settings
    python start_app.py --port 8080   # Start on custom port
    python start_app.py --dev    # Start with auto-reload for development
"""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────
APP_NAME = "Real Estate CRM"
APP_VERSION = "3.0.0"
DEFAULT_PORT = 6090
VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"


# ── Color Output ──────────────────────────────────────────────────────────────
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


# ── OS Detection ──────────────────────────────────────────────────────────────
def detect_os() -> dict:
    """Detect the operating system and return system information."""
    system = platform.system()
    machine = platform.machine()
    python_version = platform.python_version()
    
    os_info = {
        "system": system,
        "machine": machine,
        "python_version": python_version,
        "is_windows": system == "Windows",
        "is_macos": system == "Darwin",
        "is_linux": system == "Linux",
        "is_raspberry_pi": False,
    }
    
    # Detect Raspberry Pi (ARM Linux)
    if system == "Linux" and machine in ("armv7l", "aarch64", "arm64"):
        # Check for Raspberry Pi specific files
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
                if "Raspberry Pi" in cpuinfo or "BCM2" in cpuinfo:
                    os_info["is_raspberry_pi"] = True
        except FileNotFoundError:
            pass
    
    return os_info


def get_python_executable(venv_path: Path) -> str:
    """Get the Python executable path for the virtual environment."""
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "python.exe")
    else:
        return str(venv_path / "bin" / "python")


def get_pip_executable(venv_path: Path) -> str:
    """Get the pip executable path for the virtual environment."""
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "pip.exe")
    else:
        return str(venv_path / "bin" / "pip")


# ── Virtual Environment Management ────────────────────────────────────────────
def create_venv(project_root: Path) -> Path:
    """Create a virtual environment if it doesn't exist."""
    venv_path = project_root / VENV_DIR
    
    if venv_path.exists():
        print_info(f"Virtual environment already exists at: {venv_path}")
        return venv_path
    
    print_info("Creating virtual environment...")
    python_executable = sys.executable
    
    try:
        subprocess.run(
            [python_executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print_success(f"Virtual environment created at: {venv_path}")
        return venv_path
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        sys.exit(1)


def install_requirements(venv_path: Path, project_root: Path) -> bool:
    """Install requirements from requirements.txt."""
    requirements_file = project_root / REQUIREMENTS_FILE
    
    if not requirements_file.exists():
        print_error(f"Requirements file not found: {requirements_file}")
        return False
    
    pip_executable = get_pip_executable(venv_path)
    
    print_info("Installing dependencies from requirements.txt...")
    
    try:
        # Upgrade pip first
        subprocess.run(
            [pip_executable, "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True,
        )
        
        # Install requirements
        result = subprocess.run(
            [pip_executable, "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True,
        )
        
        print_success("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        if e.stderr:
            print_error(f"Error details: {e.stderr}")
        return False


# ── Server Management ─────────────────────────────────────────────────────────
def start_server(venv_path: Path, port: int, dev_mode: bool = False) -> None:
    """Start the web server."""
    python_executable = get_python_executable(venv_path)
    
    print_info(f"Starting {APP_NAME} v{APP_VERSION}...")
    print_info(f"Server will run on: http://localhost:{port}")
    print_info(f"Python executable: {python_executable}")
    
    if dev_mode:
        print_info("Running in development mode with auto-reload...")
        cmd = [
            python_executable,
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload",
        ]
    else:
        print_info("Running in production mode...")
        cmd = [
            python_executable,
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ]
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}🚀 Starting server...{Colors.END}")
    print(f"{Colors.CYAN}   Open http://localhost:{port} in your browser{Colors.END}")
    print(f"{Colors.YELLOW}   Press Ctrl+C to stop the server{Colors.END}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Server stopped by user.{Colors.END}")
    except subprocess.CalledProcessError as e:
        print_error(f"Server failed to start: {e}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - Cross-Platform Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to run the server on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--dev", "-d",
        action="store_true",
        help="Run in development mode with auto-reload",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation (use if already installed)",
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header(f"{APP_NAME} v{APP_VERSION}")
    
    # Detect OS
    print_info("Detecting operating system...")
    os_info = detect_os()
    
    system_name = os_info["system"]
    if os_info["is_raspberry_pi"]:
        system_name = "Raspberry Pi (ARM Linux)"
    elif os_info["is_macos"]:
        system_name = "macOS"
    elif os_info["is_windows"]:
        system_name = "Windows"
    elif os_info["is_linux"]:
        system_name = "Linux"
    
    print_success(f"OS: {system_name} ({os_info['machine']})")
    print_success(f"Python: {os_info['python_version']}")
    
    # Get project root
    project_root = Path(__file__).parent.absolute()
    print_info(f"Project root: {project_root}")
    
    # Create/use virtual environment
    venv_path = create_venv(project_root)
    
    # Install dependencies
    if not args.skip_install:
        if not install_requirements(venv_path, project_root):
            print_error("Failed to install dependencies. Exiting.")
            sys.exit(1)
    else:
        print_info("Skipping dependency installation (--skip-install)")
    
    # Start server
    start_server(venv_path, args.port, args.dev)


if __name__ == "__main__":
    main()
