# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""任务栏心率组件：一个挂在 Shell_TrayWnd 里的原生 Win32 子窗口。

为什么不用 Qt 画这个窗口：Qt 的窗口被 SetParent 到别的进程窗口下容易出各种怪问题，
而这块只要"画几个像素 + 定时自愈"，用 GDI 手写反而更稳、更省。

位置逻辑（与 FluentFlyout 的任务栏组件并排）：
    系统托盘左边缘  ←  [心率组件]  ←  [FluentFlyout 组件]
"""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Optional

from . import widget_render
from .util import log
from .widget_render import pick_family, reading_width
from .win32 import (
    AC_SRC_ALPHA,
    AC_SRC_OVER,
    ANTIALIASED_QUALITY,
    BI_RGB,
    BITMAPINFO,
    BLENDFUNCTION,
    CLEARTYPE_QUALITY,
    DIB_RGB_COLORS,
    GWL_EXSTYLE,
    GWL_STYLE,
    MA_NOACTIVATE,
    PS_SOLID,
    TRANSPARENT,
    WM_DESTROY,
    WM_DPICHANGED,
    WM_ERASEBKGND,
    WM_MOUSEACTIVATE,
    WM_PAINT,
    WS_CHILD,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
    WS_VISIBLE,
    WNDCLASSW,
    WNDPROC,
    PAINTSTRUCT,
    client_rect,
    class_name,
    client_to_screen,
    find_taskbar,
    find_tray_notify,
    gdi32,
    get_style,
    is_window,
    kernel32,
    msimg32,
    parent_of,
    raise_child,
    screen_pixel,
    screen_to_client,
    set_position,
    set_style,
    sibling_rect,
    system_uses_light_theme,
    user32,
    window_rect,
)
from .zones import HEART_COLOR

CLASS_NAME = "MiBandHeartHUDTaskbarWidget"
KEY_COLOR = 0x00FF00FF  # 透明色键（品红），只在 clear 模式下用

QS_ALLINPUT = 0x04FF
WS_POPUP = 0x80000000

# 这几个消息必须立刻吞掉并返回，否则任务栏会被拖死：
# 辅助功能/界面增强工具（UI Automation、Nilesoft Shell、Windhawk 之类）会挨个
# 询问任务栏的每个子窗口，只要有一个不回话，整个任务栏就卡住。
# FluentFlyout 的 TaskbarWindow 也是这么处理的。
WM_GETOBJECT = 0x003D
WM_SHOWWINDOW = 0x0018
WM_WINDOWPOSCHANGING = 0x0046
WM_NCCALCSIZE = 0x0083
WM_IME_SETCONTEXT = 0x0281
WM_IME_NOTIFY = 0x0282

SWALLOWED_MESSAGES = frozenset(
    {
        WM_GETOBJECT,
        WM_SHOWWINDOW,
        WM_WINDOWPOSCHANGING,
        WM_NCCALCSIZE,
        WM_IME_SETCONTEXT,
        WM_IME_NOTIFY,
    }
)
LWA_COLORKEY = 0x1

HEART = 13

# 没检测到 FluentFlyout 组件时的左侧默认槽位（它在任务栏左端，约到 410 结束）
DEFAULT_LEFT_ANCHOR = 410
CARD_LIGHT_BG = "#F0F0F0"
CARD_DARK_BG = "#232323"


def _rgb(r: int, g: int, b: int) -> int:
    return r | (g << 8) | (b << 16)


def tray_reserve(taskbar: int) -> int:
    """右侧系统托盘区占多宽，用来判断左边还放不放得下。"""
    tray = find_tray_notify(taskbar)
    if tray:
        left, _top, right, _bottom = window_rect(tray)
        if right > left:
            return right - left + 16
    return 240


class ArgbBlitter:
    """把一张 32 位预乘 ARGB 位图用 AlphaBlend 贴到目标 DC 上（按尺寸缓存）。"""

    def __init__(self) -> None:
        self._size: Optional[tuple[int, int]] = None
        self._hdc = 0
        self._bitmap = 0
        self._bits = ctypes.c_void_p()

    def blit(self, target_dc, pixels: bytes, width: int, height: int, x: int = 0, y: int = 0) -> None:
        if self._size != (width, height):
            self._release()
            self._prepare(width, height)
        if not self._hdc:
            return
        ctypes.memmove(self._bits, pixels, min(len(pixels), width * height * 4))
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        msimg32.AlphaBlend(target_dc, x, y, width, height, self._hdc, 0, 0, width, height, blend)

    def _prepare(self, width: int, height: int) -> None:
        screen_dc = user32.GetDC(None)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(type(info.bmiHeader))
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        bits = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(
            screen_dc, ctypes.byref(info), DIB_RGB_COLORS, ctypes.byref(bits), None, 0
        )
        user32.ReleaseDC(None, screen_dc)
        if not bitmap or not memory_dc:
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            return
        gdi32.SelectObject(memory_dc, bitmap)
        self._hdc, self._bitmap, self._bits = memory_dc, bitmap, bits
        self._size = (width, height)

    def _release(self) -> None:
        if self._bitmap:
            gdi32.DeleteObject(self._bitmap)
        if self._hdc:
            gdi32.DeleteDC(self._hdc)
        self._hdc = 0
        self._bitmap = 0
        self._bits = ctypes.c_void_p()
        self._size = None


_image_blitter = ArgbBlitter()


def draw_reading(
    hdc,
    width: int,
    height: int,
    bpm: Optional[int],
    zone: str,
    light_theme: bool = False,
    mode: str = "card",
    background: str = "",
    heart_color: str = HEART_COLOR,
    font_face: str = "Segoe UI",
    key_color: int = KEY_COLOR,
) -> None:
    """把组件画面画到任意 DC 上——线上窗口和预览脚本共用同一段绘制代码。

    整张卡片（圆角底 + 爱心 + 数字）都由 widget_render 用 Qt 渲染成一张位图，
    再一次性 AlphaBlend 上去；GDI 只负责"贴图"，不碰字体。
    """
    if mode == "clear":  # 透明模式：先把底色涂成色键，再贴带透明通道的内容
        brush = gdi32.CreateSolidBrush(key_color)
        rect = wintypes.RECT(0, 0, width, height)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)

    image = widget_render.render_card(
        width, height, bpm, zone, light_theme, heart_color, font_face, mode, background or ""
    )
    _image_blitter.blit(hdc, bytes(image.constBits()), width, height)


class TaskbarWidget:
    """线程安全的任务栏组件。主线程只管塞数值，绘制在组件自己的线程里。"""

    def __init__(self, config) -> None:
        self.cfg = config
        self.light_theme = False
        self.font_face = pick_family(getattr(config, "font_family", ""))
        self.hwnd = 0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._bpm: Optional[int] = None
        self._zone = "normal"
        self._font = 0
        self._font_px = 0
        self._wndproc = None
        self._size = (78, 34)
        self._bg_cache: Optional[int] = None
        self._key_color: Optional[int] = None
        self._bg_sampled_at = 0.0
        self._theme_checked_at = 0.0
        self._visible = True
        self._screen_rect: Optional[tuple[int, int, int, int]] = None
        self._flyout_left: Optional[int] = None
        self._flyout_right: Optional[int] = None
        # 点击组件时的回调（由 app 设置为弹出设置菜单）

    # ------------------------------------------------------------ 对外接口
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="taskbar-widget", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.5) -> None:
        self._stop.set()
        if self.hwnd:
            user32.PostMessageW(wintypes.HWND(self.hwnd), 0x0010, 0, 0)  # WM_CLOSE
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout)  # 等消息循环退出，避免进程关停时崩在 Win32 调用里

    def set_values(self, bpm: Optional[int], zone: str) -> None:
        with self._lock:
            changed = (bpm != self._bpm) or (zone != self._zone)
            self._bpm, self._zone = bpm, zone
        if changed and self.hwnd:
            user32.InvalidateRect(wintypes.HWND(self.hwnd), None, False)

    def set_visible(self, visible: bool) -> None:
        with self._lock:
            self._visible = visible
        if self.hwnd:
            user32.ShowWindow(wintypes.HWND(self.hwnd), 5 if visible else 0)
            if visible:
                raise_child(self.hwnd)

    def _snapshot(self) -> tuple[Optional[int], str]:
        with self._lock:
            return self._bpm, self._zone

    # -------------------------------------------------------------- 线程主体
    def _thread_main(self) -> None:
        if not self._register_class():
            return
        while not self._stop.is_set():
            try:
                self._ensure_window()
            except Exception as exc:  # noqa: BLE001
                log(f"任务栏组件异常：{exc!r}")
            self._pump_messages()
            user32.MsgWaitForMultipleObjects(0, None, False, 700, QS_ALLINPUT)
        if self.hwnd and is_window(self.hwnd):
            user32.DestroyWindow(wintypes.HWND(self.hwnd))

    def _register_class(self) -> bool:
        self._wndproc = WNDPROC(self._window_proc)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = CLASS_NAME
        if not user32.RegisterClassW(ctypes.byref(wc)):
            error = ctypes.get_last_error()
            if error != 1410:  # ERROR_CLASS_ALREADY_EXISTS
                log(f"注册窗口类失败：{error}")
                return False
        return True

    def _pump_messages(self) -> None:
        msg = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _ensure_window(self) -> None:
        self._refresh_theme()
        taskbar = find_taskbar()
        if not taskbar:
            return
        if self.hwnd and (not is_window(self.hwnd) or parent_of(self.hwnd) != taskbar):
            # Explorer 重启过，父窗口没了，得重建
            self.hwnd = 0
        if not self.hwnd:
            self._create_window(taskbar)
            return
        self._reposition(taskbar)

    def _refresh_theme(self) -> None:
        """主题可能在运行中被切换，每 10 秒跟一次，别到重启才换色。"""
        now = time.monotonic()
        if now - self._theme_checked_at < 10.0:
            return
        self._theme_checked_at = now
        light = system_uses_light_theme()
        if light != self.light_theme:
            self.light_theme = light
            self._bg_cache = None
            if self.hwnd:
                user32.InvalidateRect(wintypes.HWND(self.hwnd), None, True)

    def _create_window(self, taskbar: int) -> None:
        width, height = self._geometry(taskbar)[2:]
        # 纯展示：鼠标穿透，点它等于点任务栏，不抢任何输入
        ex_style = WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT
        if self.cfg.widget_background == "clear":
            ex_style |= WS_EX_LAYERED
        # 跨进程做子窗口必须"先按顶层窗口创建，再 SetParent 变成子窗口"。
        # 直接以 WS_CHILD + 外部父窗口创建的话，窗口能画出来，但鼠标输入不会
        # 投递到这个窗口（实测点击被任务栏截走）。FluentFlyout 也是这么做的。
        hwnd = user32.CreateWindowExW(
            ex_style, CLASS_NAME, "MiBandHeart", WS_POPUP,
            0, 0, width, height, None, None,
            kernel32.GetModuleHandleW(None), None,
        )
        if not hwnd:
            log(f"创建任务栏组件失败：{ctypes.get_last_error()}")
            return
        self.hwnd = int(hwnd)
        style = get_style(self.hwnd, GWL_STYLE)
        set_style(self.hwnd, GWL_STYLE, (style & ~WS_POPUP) | WS_CHILD)
        user32.SetParent(wintypes.HWND(self.hwnd), wintypes.HWND(taskbar))
        user32.ShowWindow(wintypes.HWND(self.hwnd), 5)
        if ex_style & WS_EX_LAYERED:
            user32.SetLayeredWindowAttributes(wintypes.HWND(self.hwnd), KEY_COLOR, 0, LWA_COLORKEY)
        self._reposition(taskbar)
        raise_child(self.hwnd)
        self.set_visible(self._visible)
        log(f"任务栏组件已挂载（hwnd=0x{self.hwnd:X}）")

    # ---------------------------------------------------------------- 几何
    def _geometry(self, taskbar: int) -> tuple[int, int, int, int]:
        taskbar_width, taskbar_height = client_rect(taskbar)
        height = max(24, min(40, taskbar_height - 8))
        y = max(0, (taskbar_height - height) // 2)
        gap = int(self.cfg.widget_gap + self.cfg.widget_extra_gap)
        width = self._measure_width(taskbar, height)

        if getattr(self.cfg, "widget_side", "left") == "right":
            x = max(4, min(self._tray_left(taskbar) - gap - width, taskbar_width - width - 4))
            return x, y, width, height

        # 左侧：和 FluentFlyout 的任务栏组件并排，谁都不盖谁
        flyout = sibling_rect(taskbar, "FluentFlyout")
        if flyout:
            flyout_left, _ = screen_to_client(taskbar, flyout[0], flyout[1])
            flyout_width = flyout[2] - flyout[0]
            if 0 <= flyout_left < taskbar_width and flyout_width < 700:
                self._flyout_left = flyout_left
                self._flyout_right = flyout_left + flyout_width

        anchor = self._flyout_right if self._flyout_right is not None else DEFAULT_LEFT_ANCHOR
        x = anchor + gap
        if x + width > taskbar_width - tray_reserve(taskbar):
            anchor_left = self._flyout_left if self._flyout_left is not None else DEFAULT_LEFT_ANCHOR
            x = max(4, anchor_left - gap - width)
        return x, y, width, height

    def _measure_width(self, taskbar: int, height: int) -> int:
        """和弹窗读数卡片同宽，这样弹窗能正好居中在组件正上方。"""
        return reading_width(self.font_face)

    def current_rect(self) -> Optional[tuple[int, int, int, int]]:
        """组件当前的屏幕矩形（左, 上, 右, 下）；没挂上任务栏时返回 None。"""
        return self._screen_rect

    @staticmethod
    def _tray_left(taskbar: int) -> int:
        tray = find_tray_notify(taskbar)
        if tray:
            left, top, _right, _bottom = window_rect(tray)
            return screen_to_client(taskbar, left, top)[0]
        return client_rect(taskbar)[0] - 216

    def _reposition(self, taskbar: int) -> None:
        if not self.hwnd:
            return
        with self._lock:
            visible = self._visible
            bpm = self._bpm
        if self.cfg.widget_hide_without_data and bpm is None and visible:
            user32.ShowWindow(wintypes.HWND(self.hwnd), 0)
            return
        x, y, width, height = self._geometry(taskbar)
        self._size = (width, height)
        set_position(self.hwnd, x, y, width, height)
        screen_x, screen_y = client_to_screen(taskbar, x, y)
        self._screen_rect = (screen_x, screen_y, screen_x + width, screen_y + height)

    # ---------------------------------------------------------------- 绘制
    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_PAINT:
            self._on_paint(hwnd)
            return 0
        if msg in SWALLOWED_MESSAGES:
            return 0
        if msg == WM_ERASEBKGND:
            return 1
        if msg == WM_MOUSEACTIVATE:
            return MA_NOACTIVATE
        if msg == WM_DPICHANGED:
            self._font = 0
            self._bg_cache = None
            taskbar = find_taskbar()
            if taskbar:
                self._reposition(taskbar)
            user32.InvalidateRect(hwnd, None, True)
            return 0
        if msg == WM_DESTROY:
            self.hwnd = 0
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _on_paint(self, hwnd) -> None:
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        width, height = self._size
        mem = gdi32.CreateCompatibleDC(hdc)
        bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
        old_bitmap = gdi32.SelectObject(mem, bitmap)
        try:
            self._draw(mem, hwnd, width, height)
            gdi32.BitBlt(hdc, 0, 0, width, height, mem, 0, 0, 0x00CC0020)
        finally:
            gdi32.SelectObject(mem, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem)
            user32.EndPaint(hwnd, ctypes.byref(ps))

    def _draw(self, mem, hwnd, width: int, height: int) -> None:
        bpm, zone = self._snapshot()
        mode = self.cfg.widget_background
        background = self._background(hwnd, width, height) if mode == "auto" else ""
        key_color = self._clear_key(hwnd, width, height) if mode == "clear" else KEY_COLOR
        draw_reading(
            mem, width, height, bpm, zone, self.light_theme, mode, background,
            getattr(self.cfg, "heart_color", HEART_COLOR),
            self.font_face,
            key_color,
        )

    def _sample_color(self, hwnd, width: int, height: int) -> Optional[tuple[int, int, int]]:
        """取组件**右边**空任务栏处的底色（左边紧挨着 FluentFlyout 的组件）。"""
        now = time.monotonic()
        if self._bg_cache and now - self._bg_sampled_at < 5.0:
            return self._bg_cache
        x, y = client_to_screen(hwnd, width + 60, height // 2)
        sample = screen_pixel(x, y) or screen_pixel(max(0, x - (width + 120)), y)
        self._bg_sampled_at = now
        if sample:
            self._bg_cache = sample
        return self._bg_cache

    def _clear_key(self, hwnd, width: int, height: int) -> int:
        """clear 模式：拿任务栏底色当色键（红色通道 +3，避免和内容撞色）。

        直接用洋红当色键的话，文字抗锯齿的边缘会往洋红混、出现紫边；
        用任务栏自己的颜色当色键，边缘就是往背景色混，看起来自然。
        """
        sample = self._sample_color(hwnd, width, height)
        if sample is None:
            return KEY_COLOR
        red, green, blue = sample
        key = _rgb(min(255, red + 3), green, blue)
        if key != self._key_color:
            self._key_color = key
            if self.hwnd:
                user32.SetLayeredWindowAttributes(wintypes.HWND(self.hwnd), key, 0, LWA_COLORKEY)
        return key

    def _background(self, hwnd, width: int, height: int) -> str:
        """返回 #RRGGBB。auto 模式下取任务栏自己的底色，让卡片融进去。"""
        if self.cfg.widget_background != "auto":
            return CARD_LIGHT_BG if self.light_theme else CARD_DARK_BG
        sample = self._sample_color(hwnd, width, height)
        if sample is None:
            return CARD_LIGHT_BG if self.light_theme else CARD_DARK_BG
        return "#%02X%02X%02X" % sample
