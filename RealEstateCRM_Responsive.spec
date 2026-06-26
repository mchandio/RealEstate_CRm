# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['professional_crm.py'],
    pathex=[],
    binaries=[],
    datas=[('company_logo\\RealEstateCRM.ico', 'company_logo'), ('company_logo\\RealEstateCRM_logo.png', 'company_logo'), ('real_estate_crm.db', '.')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RealEstateCRM_Responsive',
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
)
