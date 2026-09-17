# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""PyInstaller 配置：单文件版（--onefile）。

产物：packaging/out/onefile/MiBandHeartHUD.exe
用途：试用、随手甩给别人一个文件；正式分发走目录版 / MSIX。
"""

import sys
from pathlib import Path

_spec_dir = Path(SPECPATH).resolve()  # noqa: F821 - PyInstaller 注入
sys.path.insert(0, str(_spec_dir if _spec_dir.is_dir() else _spec_dir.parent))

from spec_common import ASSETS, ENTRY, EXCLUDES, ICON, VERSION  # noqa: E402

a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=[ASSETS],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
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
    name="MiBandHeartHUD",
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
    icon=ICON,
    version=VERSION,
)
