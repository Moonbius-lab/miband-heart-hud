# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""PyInstaller 配置：带控制台的排障版。

产物：packaging/out/debug/MiBandHeartHUD_dbg.exe
装了没反应、闪退时用它跑，日志和异常会直接打在控制台里；
再加 --diag（run.py 里的 Qt DLL 逐个加载诊断）定位是不是缺 DLL。
"""

import sys
from pathlib import Path

_spec_dir = Path(SPECPATH).resolve()  # noqa: F821 - PyInstaller 注入
sys.path.insert(0, str(_spec_dir if _spec_dir.is_dir() else _spec_dir.parent))

from spec_common import ASSETS, ENTRY, EXCLUDES  # noqa: E402

a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=[ASSETS],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[e for e in EXCLUDES if e not in ("unittest",)],
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
    name="MiBandHeartHUD_dbg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
