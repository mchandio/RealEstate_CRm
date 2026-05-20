# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import PySide6


pyside_dir = Path(PySide6.__file__).resolve().parent


def qt_plugin_binaries(folder):
    source_dir = pyside_dir / 'plugins' / folder
    if not source_dir.exists():
        return []
    return [(str(path), f'PySide6/plugins/{folder}') for path in source_dir.glob('*.dll')]


qt_plugins = []
for plugin_folder in ('platforms', 'styles', 'imageformats', 'iconengines', 'printsupport'):
    qt_plugins += qt_plugin_binaries(plugin_folder)


a = Analysis(
    ['qt_crm_app.py'],
    pathex=[],
    binaries=qt_plugins,
    datas=[
        ('company_logo\\RealEstateCRM.ico', 'company_logo'),
        ('company_logo\\RealEstateCRM_logo.png', 'company_logo'),
        ('frontend\\index.html', 'frontend'),
        ('frontend\\styles.css', 'frontend'),
        ('frontend\\app.js', 'frontend'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtPrintSupport',
        'numpy',
        'pandas',
        'PIL._tkinter_finder',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'fastapi',
        'slowapi',
        'jose',
        'sqlalchemy',
        'backend.main',
        'backend.config',
        'backend.database',
        'backend.models',
        'backend.schemas',
        'backend.auth',
        'backend.routers.auth_router',
        'backend.routers.records_router',
        'backend.routers.reports_router',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyinstaller_qt_runtime_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='RealEstateCRM_Qt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['company_logo\\RealEstateCRM.ico'],
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RealEstateCRM_Qt',
)
