# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""只读检查：心率组件是否挂在任务栏上、落在哪个位置。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_hud.win32 import (  # noqa: E402
    child_windows,
    class_name,
    client_rect,
    find_taskbar,
    find_tray_notify,
    sibling_rect,
    window_rect,
)

from hr_hud.taskbar import CLASS_NAME  # noqa: E402


def main() -> int:
    taskbar = find_taskbar()
    if not taskbar:
        print("找不到任务栏（Explorer 没在跑？）")
        return 1
    width, height = client_rect(taskbar)
    print(f"任务栏 hwnd=0x{taskbar:X} 客户区 {width}x{height}  矩形={window_rect(taskbar)}")

    tray = find_tray_notify(taskbar)
    print(f"系统托盘 TrayNotifyWnd = {'0x%X' % tray if tray else '未找到'}")
    if tray:
        print(f"  托盘矩形（屏幕坐标）= {window_rect(tray)}")

    flyout = sibling_rect(taskbar, "FluentFlyout")
    print(f"FluentFlyout 任务栏组件 = {flyout or '未检测到（没在显示）'}")

    ours = [hwnd for hwnd in child_windows(taskbar) if class_name(hwnd) == CLASS_NAME]
    if not ours:
        print("心率组件：没有挂上任务栏 ❌")
        return 2
    for hwnd in ours:
        left, top, right, bottom = window_rect(hwnd)
        print(
            f"心率组件 ✅ hwnd=0x{hwnd:X}  矩形={left, top, right, bottom}  "
            f"大小={right - left}x{bottom - top}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
