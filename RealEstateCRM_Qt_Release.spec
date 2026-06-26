# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import PySide6
from PyInstaller.utils.hooks import collect_submodules


pyside_dir = Path(PySide6.__file__).resolve().parent


def qt_plugin_binaries(folder):
    source_dir = pyside_dir / "plugins" / folder
    if not source_dir.exists():
        return []
    return [(str(path), f"PySide6/plugins/{folder}") for path in source_dir.glob("*.dll")]


qt_plugins = []
for plugin_folder in ("platforms", "styles", "imageformats", "iconengines", "printsupport"):
    qt_plugins += qt_plugin_binaries(plugin_folder)


hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    "PIL._tkinter_finder",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "httptools.parser.parser",
    "passlib.handlers.bcrypt",
    "jose.backends.cryptography_backend",
    "qt_crm_premium_style",
]
hiddenimports += collect_submodules("backend")
hiddenimports += collect_submodules("crm_core")


a = Analysis(
    ["qt_crm_app.py"],
    pathex=[],
    binaries=qt_plugins,
    datas=[
        ("company_logo", "company_logo"),
        ("frontend", "frontend"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_qt_runtime_hook.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="RealEstateCRM_Qt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["company_logo\\RealEstateCRM.ico"],
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="RealEstateCRM_Qt",
)
