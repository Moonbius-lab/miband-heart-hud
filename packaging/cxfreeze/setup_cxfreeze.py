"""cx_Freeze 打包配置（备用方案）。

用法：python packaging/cxfreeze/setup_cxfreeze.py build_exe
产物：packaging/out/cxfreeze/MiBandHeartHUD.exe（免安装绿色目录）

主力打包工具是 PyInstaller（见 packaging/pyinstaller/），这里保留一份 cx_Freeze
配置，用于 PyInstaller 出问题时交叉验证"到底是我们的代码还是打包器的问题"。
"""

from __future__ import annotations

import sys
from pathlib import Path

from cx_Freeze import Executable, setup

ROOT = Path(__file__).resolve().parents[2]   # packaging/cxfreeze/xxx.py -> 仓库根
sys.path.insert(0, str(ROOT))

build_options = {
    "packages": ["hr_hud"],
    "include_files": [(str(ROOT / "assets"), "assets")],
    "build_exe": str(ROOT / "packaging" / "out" / "cxfreeze"),
    "excludes": [
        "tkinter",
        "unittest",
        "pydoc_data",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtCharts",
        "PySide6.QtPdf",
        "PySide6.QtDesigner",
        "PySide6.QtTest",
        "PySide6.QtSql",
        "PySide6.QtBluetooth",
        "PySide6.Qt3DCore",
        "PySide6.QtOpenGL",
    ],
    "include_msvcr": True,
    "optimize": 1,
}

setup(
    name="MiBandHeartHUD",
    version="1.0.0",
    description="小米手环心率 · Windows 任务栏组件",
    options={"build_exe": build_options},
    executables=[
        Executable(
            script=str(ROOT / "run.py"),
            base="gui",  # 不弹控制台窗口
            target_name="MiBandHeartHUD.exe",
            icon=str(ROOT / "assets" / "app.ico"),
            shortcut_name="小米手环心率",
        )
    ],
)
