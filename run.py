# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""小米手环心率 · 任务栏组件 + 异常提醒。

用法：
    python run.py                 # 正常运行（自动连接上次记住的手环）
    python run.py --scan          # 只扫描附近的 BLE 设备，看看能不能找到手环
    python run.py --demo          # 演示模式：用模拟心率验证组件与提醒
    python run.py --test-alert    # 启动 1.2 秒后发一条测试提醒
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from hr_hud.config import Config
from hr_hud.util import log, setup_console
from hr_hud.win32 import set_dpi_awareness, single_instance


def _scan() -> int:
    from hr_hud.ble import scan

    print("扫描 BLE 设备中（8 秒）…\n")
    devices = asyncio.run(scan(timeout=8.0))
    if not devices:
        print("没有扫到设备。确认电脑蓝牙已打开。")
        return 2
    for device in devices:
        print(f" {'★' if device.has_hrs else ' '} {device.label()}")
    print("\n★ = 广播里带标准心率服务（0x180D）。如果手环没带这个标记也别急，")
    print("   小米手环不一定把服务 UUID 写进广播包，直接 python run.py 让它自己挑就行。")
    return 0


def main(argv: list[str] | None = None) -> int:
    setup_console()
    parser = argparse.ArgumentParser(description="小米手环心率 · Windows 任务栏组件")
    parser.add_argument("--demo", action="store_true", help="用模拟心率运行（不需要手环）")
    parser.add_argument("--test-alert", action="store_true", help="启动后立刻发一条测试提醒")
    parser.add_argument("--scan", action="store_true", help="只扫描设备后退出")
    parser.add_argument("--address", default="", help="指定手环蓝牙地址")
    parser.add_argument("--no-widget", action="store_true", help="不显示任务栏组件")
    parser.add_argument("--diag", action="store_true", help="打包后诊断：逐个加载 Qt 的 DLL 看哪个失败")
    args = parser.parse_args(argv)

    if args.diag:
        return _diagnose_qt()

    set_dpi_awareness()
    if args.scan:
        return _scan()

    if not single_instance():
        print("程序已经在运行了（看系统托盘里的红心图标）。")
        return 1

    config = Config.load()
    if args.address:
        config.device_address = args.address
        config.save()
    if args.no_widget:
        config.widget_enabled = False

    from PySide6.QtWidgets import QApplication

    from hr_hud.app import HeartApp

    qt_app = QApplication([])
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setApplicationName("小米手环心率")

    hub = HeartApp(config, demo=args.demo, test_alert=args.test_alert)
    hub.start()
    log("程序已启动（托盘图标：右键看菜单）")
    code = qt_app.exec()
    hub.teardown()
    log(f"已退出（code={code}）")
    # Qt 与 Win32 子窗口的销毁顺序在解释器关停阶段不可控，直接干净收工，
    # 否则有一定概率在退出瞬间触发访问违例（Windows 的"应用程序错误"弹窗）。
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def _diagnose_qt() -> int:
    """打包后诊断用：在冻结环境里逐个加载 Qt6*.dll，定位加载失败的那一个。"""
    import ctypes
    import os

    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    for root in (os.path.join(base, "_internal"), base):
        pyside = os.path.join(root, "PySide6")
        if not os.path.isdir(pyside):
            continue
        print(f"[diag] 运行环境: {base}")
        print(f"[diag] PySide6 目录: {pyside}")
        if hasattr(os, "add_dll_directory"):
            for extra in (pyside, root, os.path.join(pyside, "plugins", "platforms")):
                if os.path.isdir(extra):
                    try:
                        os.add_dll_directory(extra)
                        print(f"[diag] 已加入 DLL 搜索目录: {extra}")
                    except OSError as exc:
                        print(f"[diag] 加入失败 {extra}: {exc}")
        for name in sorted(os.listdir(pyside)):
            if not (name.startswith("Qt6") and name.endswith(".dll")):
                continue
            try:
                ctypes.WinDLL(os.path.join(pyside, name))
                print(f"[diag] OK   {name}")
            except OSError as exc:
                print(f"[diag] FAIL {name} -> {exc}")
        return 0
    print("[diag] 找不到 PySide6 目录")
    return 1


if __name__ == "__main__":
    sys.exit(main())
