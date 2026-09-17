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
from hr_hud.util import log
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
    parser = argparse.ArgumentParser(description="小米手环心率 · Windows 任务栏组件")
    parser.add_argument("--demo", action="store_true", help="用模拟心率运行（不需要手环）")
    parser.add_argument("--test-alert", action="store_true", help="启动后立刻发一条测试提醒")
    parser.add_argument("--scan", action="store_true", help="只扫描设备后退出")
    parser.add_argument("--address", default="", help="指定手环蓝牙地址")
    parser.add_argument("--no-widget", action="store_true", help="不显示任务栏组件")
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
