# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all PIL/Pillow components
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')

block_cipher = None

a = Analysis(
    ['pipboard.py'],
    pathex=[],
    binaries=pil_binaries,  # Add PIL binaries
    datas=pil_datas,  # Add PIL data files
    hiddenimports=[
        # Psutil
        'psutil',
        'psutil._psutil_windows',
        
        # Win32 modules
        'win32gui',
        'win32con',
        'win32ui',
        'win32process',
        'win32api',
        'win32com',
        'pywintypes',
        'pythoncom',
        
        # PIL/Pillow - expanded list
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL._imaging',
        'PIL._tkinter_finder',
        
        # Other dependencies
        'requests',
        'queue',
        'threading',
        'logging',
        'logging.handlers',
        'webbrowser',
        'io',
        'json',
        'ctypes',
        're',
        'tempfile',
        'subprocess',
        'os',
        'sys',
        'time',
    ] + pil_hiddenimports,  # Add all discovered PIL hidden imports
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MultiClientViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True temporarily if you need to see error messages
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Optional - remove this line if you don't have an icon
)
