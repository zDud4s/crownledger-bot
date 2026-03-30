# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path.cwd()
entrypoint = project_root / "desktop" / "updater.py"


block_cipher = None

analysis = Analysis(
    [str(entrypoint)],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

# Onefile mode: binaries/datas embedded directly in the exe, no COLLECT needed.
# This allows the updater to be copied to any location without needing _internal/.
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name="CrownLedgerUpdater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
)
