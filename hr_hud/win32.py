# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""Win32 底层封装：DPI 感知、任务栏查找、窗口样式、主题判断。

任务栏组件的做法和 FluentFlyout 一致：把自己的窗口变成任务栏（Shell_TrayWnd）
的子窗口，于是它会跟着任务栏一起显示/隐藏/缩放。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
msimg32 = ctypes.WinDLL("msimg32", use_last_error=True)

# ---- 窗口样式 ----
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

GWL_STYLE = -16
GWL_EXSTYLE = -20

SWP_NOACTIVATE = 0x0010
SWP_NOZORDER = 0x0004
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_FRAMECHANGED = 0x0020

# ---- 消息 ----
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_MOUSEACTIVATE = 0x0021
WM_DPICHANGED = 0x02E0
WM_TIMER = 0x0113
MA_NOACTIVATE = 3

# ---- GDI ----
PS_SOLID = 0
TRANSPARENT = 1
SRCCOPY = 0x00CC0020
ANTIALIASED_QUALITY = 4
CLEARTYPE_QUALITY = 5

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class BLENDFUNCTION(ctypes.Structure):
    """AlphaBlend 的混合参数。"""

    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
BI_RGB = 0
DIB_RGB_COLORS = 0

# 句柄在 64 位下是 8 字节。不声明参数类型的话，ctypes 会按 32 位 int 传，
# 于是 GetModuleHandleW 之类返回的大句柄会直接抛 OverflowError。
_H = ctypes.c_void_p
_I = ctypes.c_int
_U = wintypes.UINT

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = _H
user32.FindWindowExW.argtypes = [_H, _H, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = _H
user32.GetParent.argtypes = [_H]
user32.GetParent.restype = _H
user32.SetParent.argtypes = [_H, _H]
user32.SetParent.restype = _H
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    _I, _I, _I, _I, _H, _H, _H, _H,
]
user32.CreateWindowExW.restype = _H
user32.RegisterClassW.argtypes = [_H]
user32.RegisterClassW.restype = wintypes.ATOM
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, _H]
user32.DefWindowProcW.argtypes = [_H, _U, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.SetWindowPos.argtypes = [_H, _H, _I, _I, _I, _I, _U]
user32.ShowWindow.argtypes = [_H, _I]
user32.InvalidateRect.argtypes = [_H, _H, wintypes.BOOL]
user32.GetClientRect.argtypes = [_H, _H]
user32.GetWindowRect.argtypes = [_H, _H]
user32.ClientToScreen.argtypes = [_H, _H]
user32.ScreenToClient.argtypes = [_H, _H]
user32.GetClassNameW.argtypes = [_H, wintypes.LPWSTR, _I]
user32.GetWindowRgn.argtypes = [_H, _H]
user32.EnumChildWindows.argtypes = [_H, _H, wintypes.LPARAM]
user32.IsWindow.argtypes = [_H]
user32.DestroyWindow.argtypes = [_H]
user32.PostMessageW.argtypes = [_H, _U, wintypes.WPARAM, wintypes.LPARAM]
user32.PeekMessageW.argtypes = [_H, _H, _U, _U, _U]
user32.TranslateMessage.argtypes = [_H]
user32.DispatchMessageW.argtypes = [_H]
user32.DispatchMessageW.restype = LRESULT
user32.MsgWaitForMultipleObjects.argtypes = [wintypes.DWORD, _H, wintypes.BOOL, wintypes.DWORD, wintypes.DWORD]
user32.MsgWaitForMultipleObjects.restype = wintypes.DWORD
user32.SetLayeredWindowAttributes.argtypes = [_H, wintypes.DWORD, ctypes.c_ubyte, wintypes.DWORD]
user32.FillRect.argtypes = [_H, _H, _H]
user32.GetDC.argtypes = [_H]
user32.GetDC.restype = _H
user32.ReleaseDC.argtypes = [_H, _H]
user32.BeginPaint.argtypes = [_H, _H]
user32.BeginPaint.restype = _H
user32.EndPaint.argtypes = [_H, _H]
user32.GetWindowLongPtrW.argtypes = [_H, _I]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [_H, _I, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongW.argtypes = [_H, _I]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [_H, _I, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long

gdi32.CreateCompatibleDC.argtypes = [_H]
gdi32.CreateCompatibleDC.restype = _H
gdi32.CreateCompatibleBitmap.argtypes = [_H, _I, _I]
gdi32.CreateCompatibleBitmap.restype = _H
gdi32.DeleteDC.argtypes = [_H]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.CreateSolidBrush.argtypes = [wintypes.DWORD]
gdi32.CreateSolidBrush.restype = _H
gdi32.CreatePen.argtypes = [_I, _I, wintypes.DWORD]
gdi32.CreatePen.restype = _H
gdi32.CreateFontW.argtypes = [
    _I, _I, _I, _I, _I, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.LPCWSTR,
]
gdi32.CreateFontW.restype = _H
gdi32.CreateRectRgn.argtypes = [_I, _I, _I, _I]
gdi32.CreateRectRgn.restype = _H
gdi32.SelectObject.argtypes = [_H, _H]
gdi32.SelectObject.restype = _H
gdi32.DeleteObject.argtypes = [_H]
gdi32.GetStockObject.argtypes = [_I]
gdi32.GetStockObject.restype = _H
gdi32.RoundRect.argtypes = [_H, _I, _I, _I, _I, _I, _I]
gdi32.Ellipse.argtypes = [_H, _I, _I, _I, _I]
gdi32.Polygon.argtypes = [_H, _H, _I]
gdi32.TextOutW.argtypes = [_H, _I, _I, wintypes.LPCWSTR, _I]
gdi32.GetTextExtentPoint32W.argtypes = [_H, wintypes.LPCWSTR, _I, _H]
gdi32.SetTextColor.argtypes = [_H, wintypes.DWORD]
gdi32.SetBkMode.argtypes = [_H, _I]
gdi32.BitBlt.argtypes = [_H, _I, _I, _I, _I, _H, _I, _I, wintypes.DWORD]
gdi32.GetPixel.argtypes = [_H, _I, _I]
gdi32.GetPixel.restype = wintypes.DWORD
gdi32.GetRgnBox.argtypes = [_H, _H]
gdi32.GetDIBits.argtypes = [_H, _H, wintypes.UINT, wintypes.UINT, _H, _H, wintypes.UINT]
gdi32.GetDIBits.restype = _I
gdi32.CreateDIBSection.argtypes = [_H, _H, wintypes.UINT, ctypes.POINTER(_H), _H, wintypes.DWORD]
gdi32.CreateDIBSection.restype = _H

msimg32.AlphaBlend.argtypes = [_H, _I, _I, _I, _I, _H, _I, _I, _I, _I, BLENDFUNCTION]
msimg32.AlphaBlend.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = _H
kernel32.CreateMutexW.argtypes = [_H, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = _H


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


# ---------------------------------------------------------------- DPI / 进程
def set_dpi_awareness() -> None:
    """必须在创建任何窗口之前调用。"""
    try:  # Windows 10 1703+：Per-Monitor V2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except OSError:
            pass


def single_instance(name: str = "MiBandHeartHUD.SingleInstance") -> bool:
    """返回 True 表示这是第一个实例。"""
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return True
    return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


# ------------------------------------------------------------------- 任务栏
def find_taskbar() -> int:
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    return int(hwnd or 0)


def find_tray_notify(taskbar: int) -> int:
    hwnd = user32.FindWindowExW(wintypes.HWND(taskbar), None, "TrayNotifyWnd", None)
    return int(hwnd or 0)


def child_windows(parent: int) -> list[int]:
    result: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(child, _param):
        result.append(int(child))
        return True

    user32.EnumChildWindows(wintypes.HWND(parent), callback_type(collect), 0)
    return result


def class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(wintypes.HWND(hwnd), buf, 256)
    return buf.value


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def client_rect(hwnd: int) -> tuple[int, int]:
    rect = wintypes.RECT()
    user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return rect.right - rect.left, rect.bottom - rect.top


def window_region_box(hwnd: int) -> Optional[tuple[int, int, int, int]]:
    """取窗口被裁剪后实际可见的区域（相对窗口），FluentFlyout 的组件靠这个定位。"""
    rgn = gdi32.CreateRectRgn(0, 0, 0, 0)
    if not rgn:
        return None
    try:
        kind = user32.GetWindowRgn(wintypes.HWND(hwnd), rgn)
        if kind <= 1:  # ERROR / NULLREGION
            return None
        box = wintypes.RECT()
        gdi32.GetRgnBox(rgn, ctypes.byref(box))
        if box.right <= box.left or box.bottom <= box.top:
            return None
        return box.left, box.top, box.right, box.bottom
    finally:
        gdi32.DeleteObject(rgn)


def sibling_rect(parent: int, class_substring: str) -> Optional[tuple[int, int, int, int]]:
    """在任务栏里找某个同族组件（比如 FluentFlyout 的任务栏组件）实际占用的屏幕矩形。"""
    for child in child_windows(parent):
        if class_substring.lower() not in class_name(child).lower():
            continue
        box = window_region_box(child)
        if box is None:
            continue
        left, top, _right, _bottom = window_rect(child)
        return left + box[0], top + box[1], left + box[2], top + box[3]
    return None


def client_to_screen(hwnd: int, x: int, y: int) -> tuple[int, int]:
    point = wintypes.POINT(x, y)
    user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(point))
    return point.x, point.y


def screen_to_client(hwnd: int, x: int, y: int) -> tuple[int, int]:
    point = wintypes.POINT(x, y)
    user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(point))
    return point.x, point.y


def screen_pixel(x: int, y: int) -> Optional[tuple[int, int, int]]:
    hdc = user32.GetDC(None)
    if not hdc:
        return None
    try:
        value = gdi32.GetPixel(hdc, x, y)
        if value == 0xFFFFFFFF:  # CLR_INVALID
            return None
        return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
    finally:
        user32.ReleaseDC(None, hdc)


def set_position(hwnd: int, x: int, y: int, width: int, height: int) -> None:
    user32.SetWindowPos(
        wintypes.HWND(hwnd), None, x, y, width, height,
        SWP_NOACTIVATE | SWP_NOZORDER,
    )


HWND_TOP = 0


def raise_child(hwnd: int) -> None:
    """在同级子窗口里置顶（不改变全局置顶属性，也不激活）。"""
    user32.SetWindowPos(wintypes.HWND(hwnd), wintypes.HWND(HWND_TOP), 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def invalidate(hwnd: int) -> None:
    user32.InvalidateRect(wintypes.HWND(hwnd), None, False)


def is_window(hwnd: int) -> bool:
    return bool(user32.IsWindow(wintypes.HWND(hwnd)))


def parent_of(hwnd: int) -> int:
    return int(user32.GetParent(wintypes.HWND(hwnd)) or 0)


def screen_bounds() -> tuple[int, int]:
    """主屏分辨率。"""
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def is_taskbar_visible() -> bool:
    """任务栏此刻能不能被看见。

    判据：任务栏是否可见、是否还在屏幕内，以及**任务栏上那一点的最上层窗口
    是不是它自己**（被全屏游戏盖住时，那个点返回的是游戏窗口）。
    比"前台窗口是否满屏"可靠——最大化的普通窗口 GetWindowRect 同样满屏，
    但它并不会盖住任务栏。
    """
    taskbar = find_taskbar()
    if not taskbar or not user32.IsWindowVisible(wintypes.HWND(taskbar)):
        return False

    screen_width, screen_height = screen_bounds()
    left, top, right, bottom = window_rect(taskbar)
    if bottom <= 0 or top >= screen_height or right <= 0 or left >= screen_width:
        return False
    if bottom - top <= 0 or right - left <= 0:
        return False

    # 取任务栏托盘区附近的一个点，看压在那里的最上层窗口是不是任务栏的后代
    probe_x = min(right - 40, screen_width - 1)
    probe_y = min(max((top + bottom) // 2, 0), screen_height - 1)
    hit = int(user32.WindowFromPoint(wintypes.POINT(probe_x, probe_y)) or 0)
    if not hit:
        return False
    for _ in range(8):  # 沿父链往上找，看能不能找到任务栏
        if hit == taskbar:
            return True
        parent = parent_of(hit)
        if not parent or parent == hit:
            return False
        hit = parent
    return False


def get_style(hwnd: int, index: int) -> int:
    getter = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
    return int(getter(wintypes.HWND(hwnd), index))


def set_style(hwnd: int, index: int, value: int) -> None:
    setter = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
    setter(wintypes.HWND(hwnd), index, value)


def make_no_activate(hwnd: int) -> None:
    """给 Qt 的弹窗加上"不抢焦点、不进 Alt+Tab"。"""
    style = get_style(hwnd, GWL_EXSTYLE)
    set_style(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    user32.SetWindowPos(
        wintypes.HWND(hwnd), None, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
    )


# --------------------------------------------------------------------- 主题
def system_uses_light_theme() -> bool:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return bool(value)
    except OSError:
        return False


DEFAULT_ACCENT = (0x00, 0x78, 0xD4)  # Windows 默认蓝


def system_accent_color() -> tuple[int, int, int]:
    """系统的强调色（RGB）。

    首选资源管理器调色板里的 Accent 项（就是"设置 → 个性化 → 颜色"里选的那个颜色），
    它是一段 REG_BINARY，每组 4 字节按 B,G,R,A 排列。
    取不到时退回 DWM 的 ColorizationColor（0xAABBGGRR）。
    """
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent",
        ) as key:
            palette, _ = winreg.QueryValueEx(key, "AccentPalette")
        offset = 3 * 4  # Light3, Light2, Light1, Accent
        blue, green, red = palette[offset], palette[offset + 1], palette[offset + 2]
        if red or green or blue:
            return red, green, blue
    except (OSError, IndexError, TypeError):
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
            value, _ = winreg.QueryValueEx(key, "ColorizationColor")
        red = value & 0xFF
        green = (value >> 8) & 0xFF
        blue = (value >> 16) & 0xFF
        if red or green or blue:
            return red, green, blue
    except OSError:
        pass
    return DEFAULT_ACCENT


def readable_accent(rgb: tuple[int, int, int], light_theme: bool) -> tuple[int, int, int]:
    """让强调色在当前底色上看得清：浅色主题压暗，深色主题提亮。"""
    red, green, blue = rgb
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    if light_theme and luminance > 0.62:
        scale = 0.62 / luminance
        return tuple(max(0, min(255, int(channel * scale))) for channel in rgb)
    if not light_theme and luminance < 0.5:
        blend = min(1.0, (0.5 - luminance) / 0.5) * 0.55
        return tuple(int(channel + (255 - channel) * blend) for channel in rgb)
    return rgb
