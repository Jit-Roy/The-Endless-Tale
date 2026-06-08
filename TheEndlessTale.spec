# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[('ui/icons', 'ui/icons'), ('.env', '.')],
    hiddenimports=['ui', 'ui.main_window', 'managers', 'loaders', 'helpers', 'roleplay_system', 'data_models', 'gemini_client', 'PyQt5'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PySide2', 'PyQt6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TheEndlessTale',
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
    upx_exclude=[],
    name='TheEndlessTale',
)
