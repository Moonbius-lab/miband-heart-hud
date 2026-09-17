# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""诊断脚本：打印本机任务栏的窗口结构，用于确定心率组件该挂在哪里。

只读，不改任何东西。用法：
    python tools/dump_taskbar.py
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_text(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def rect_of(hwnd: int) -> wintypes.RECT:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def walk(hwnd: int, depth: int = 0, max_depth: int = 3) -> None:
    r = rect_of(hwnd)
    print(
        "  " * depth
        + f"[{class_name(hwnd)!r}] ' {window_text(hwnd)}' hwnd=0x{hwnd:X} "
        f"rect=({r.left},{r.top},{r.right},{r.bottom}) size={r.right - r.left}x{r.bottom - r.top}"
    )
    if depth >= max_depth:
        return
    children = []
    cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(child, _):
        children.append(child)
        return True

    user32.EnumChildWindows(hwnd, cb(collect), 0)
    for child in children:
        walk(child, depth + 1, max_depth)


def main() -> None:
    for cls in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        hwnd = user32.FindWindowW(cls, None)
        if not hwnd:
            print(f"{cls}: 未找到")
            continue
        cr = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(cr))
        print(f"=== {cls} hwnd=0x{hwnd:X} client={cr.right - cr.left}x{cr.bottom - cr.top}")
        walk(hwnd, 1, 2)

    tray = user32.FindWindowExW(user32.FindWindowW("Shell_TrayWnd", None), None, "TrayNotifyWnd", None)
    print(f"TrayNotifyWnd: {'0x%X' % tray if tray else '未找到'}")


if __name__ == "__main__":
    main()
