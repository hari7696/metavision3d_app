# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('C:/Users/ghari/Documents/OPS/UI/metavision3d_app/visionApp/lib', 'lib'), ('C:/Users/ghari/Documents/OPS/UI/metavision3d_app/visionApp/config', 'config'), \
(r'C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\SAMI\MetabAnalystR.R', 'config')]
datas += copy_metadata('anndata')


a = Analysis(
    ['visionApp\\app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['SAMI', 'sami_tk', 'anndata', 'igraph', 'pyarrow', 'leidenalg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    'app_load.jpg',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=False,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='app',
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
    icon=['C:\\Users\\ghari\\Documents\\OPS\\UI\\Isotopes_app\\visionapp.ico'],
)
