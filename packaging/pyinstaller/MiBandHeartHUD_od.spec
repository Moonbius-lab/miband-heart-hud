# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""PyInstaller 配置：目录版（--onedir）—— 免安装绿色版，推荐的分发形态。

产物：packaging/out/onedir/MiBandHeartHUD/（整个目录一起拷走就能跑）

为什么不默认用单文件版：--onefile 每次启动都要把自己解压到 %TEMP%，
启动慢、杀软更爱盯。目录版是解压好的，直接加载。
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
    [],
    exclude_binaries=True,
    name="MiBandHeartHUD",
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
    icon=ICON,
    version=VERSION,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MiBandHeartHUD",
)
