# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""三个 .spec 共用的路径与裁剪清单。

为什么单独放一个文件：.spec 是被 PyInstaller exec 执行的脚本，里面的相对路径
会跟着"用户在哪个目录敲命令"漂移。这里统一用 __file__ 算出仓库根，spec 里
`sys.path.insert(0, SPECPATH)` 后 `import spec_common` 拿到的就是绝对路径。
"""

from __future__ import annotations

from pathlib import Path

# packaging/pyinstaller/spec_common.py -> 仓库根
ROOT = Path(__file__).resolve().parents[2]

ENTRY = str(ROOT / "run.py")
ASSETS = (str(ROOT / "assets"), "assets")
ICON = str(ROOT / "assets" / "app.ico")

# 版本号只有一个来源：hr_hud/__init__.py 的 __version__。
# build.ps1 会先跑 make_version_info.py，把它写成 PyInstaller 认的版本资源文件。
VERSION_FILE = ROOT / "packaging" / "out" / "version_info.txt"
VERSION = str(VERSION_FILE) if VERSION_FILE.exists() else None

# 本程序只用到 QtCore / QtGui / QtWidgets / QtSvg，但 PySide6 全量装下来 300MB+。
# 靠 excludes 把用不到的模块剔掉，产物从 ~300MB 降到 ~60MB。
QT_KEEP = ("QtCore", "QtGui", "QtWidgets", "QtSvg")

EXCLUDES = [
    # 标准库里用不到的大件
    "tkinter",
    "unittest",
    "pydoc",
    "pydoc_data",
    # PySide6 的其余模块
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtDesigner",
    "PySide6.QtTest",
    "PySide6.QtSql",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSerialPort",
    "PySide6.QtWebSockets",
    "PySide6.QtWebChannel",
    "PySide6.QtHelp",
    "PySide6.QtOpenGL",
]
