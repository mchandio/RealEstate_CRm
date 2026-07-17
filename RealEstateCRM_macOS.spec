# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Real Estate CRM - macOS Build
===================================================
Builds a macOS .app bundle for the Qt desktop application.

Usage:
    pyinstaller RealEstateCRM_macOS.spec

Output: dist/RealEstateCRM.app
"""

from pathlib import Path

# ── Detect PySide6 plugin directory ──────────────────────────────────────────
try:
    import PySide6
    pyside_dir = Path(PySide6.__file__).resolve().parent
except ImportError:
    pyside_dir = None

def qt_plugin_binaries(folder):
    """Collect Qt platform plugins."""
    if pyside_dir is None:
        return []
    source_dir = pyside_dir / 'plugins' / folder
    if not source_dir.exists():
        return []
    return [(str(path), f'PySide6/plugins/{folder}') for path in source_dir.glob('*') if path.is_file()]

# ── Qt plugins to bundle ─────────────────────────────────────────────────────
qt_plugins = []
for plugin_folder in ('platforms', 'styles', 'imageformats', 'iconengines', 'printsupport', 'tls'):
    qt_plugins += qt_plugin_binaries(plugin_folder)

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # PySide6 modules
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtPrintSupport',
    # Backend modules
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    'fastapi',
    'slowapi',
    'jose.backends.cryptography_backend',
    'passlib.handlers.bcrypt',
    'sqlalchemy.dialects.sqlite',
    # Utility modules
    'PIL._tkinter_finder',
    'numpy',
    'pandas',
    # CRM modules
    'qt_crm_premium_style',
]

# Dynamically collect backend and crm_core submodules
try:
    from PyInstaller.utils.hooks import collect_submodules
    hiddenimports += collect_submodules('backend')
    hiddenimports += collect_submodules('crm_core')
except ImportError:
    pass

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ['CRM/main.py'],
    pathex=[],
    binaries=qt_plugins,
    datas=[
        ('company_logo', 'company_logo'),
        ('frontend', 'frontend'),
        ('migrations', 'migrations'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyinstaller_qt_runtime_hook.py'],
    excludes=[
        'tkinter',
        'test',
        'unittest',
        'pytest',
        'numpy.random._examples',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ── BUNDLE (macOS .app) ──────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RealEstateCRM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='RealEstateCRM',
)

app = BUNDLE(
    coll,
    name='RealEstateCRM.app',
    icon='company_logo/RealEstateCRM.icns',
    bundle_identifier='com.realestate.crm',
    info_plist={
        'CFBundleDisplayName': 'Real Estate CRM',
        'CFBundleShortVersionString': '3.0.0',
        'CFBundleVersion': '3.0.0',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSApplicationCategoryType': 'public.app-category.business',
        'NSHumanReadableCopyright': 'Copyright © 2026 Real Estate CRM. All rights reserved.',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'SQLite Database',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
                'LSItemContentTypes': ['public.database']
            }
        ],
        'NSSupportsAutomaticGraphicsSwitching': True,
        'LSUIElement': False,
    },
)
