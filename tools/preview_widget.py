# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""把任务栏组件渲染成图片。

用的是线上同一段绘制代码（hr_hud.taskbar.draw_reading），所以看到的就是它
挂在任务栏上时的真实样子——不需要程序在跑，也不用截你的屏幕。

用法：python tools/preview_widget.py
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_hud.flyout import pick_family, reading_width  # noqa: E402
from hr_hud.taskbar import draw_reading  # noqa: E402
from hr_hud.zones import HEART_COLOR  # noqa: E402
from hr_hud.win32 import gdi32, user32  # noqa: E402

OUT = Path(__file__).resolve().parent
HEIGHT = 40

user32.GetDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    ctypes.c_void_p,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.UINT,
]


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


def render(
    out_name: str,
    bpm,
    zone: str,
    light: bool,
    scale: int = 4,
    mode: str = "card",
    background: str = "",
) -> None:
    from PySide6.QtGui import QImage, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication(["preview"])
    heart_color = HEART_COLOR
    font_face = pick_family()
    WIDTH = reading_width(font_face)  # 和弹窗同宽

    screen_dc = user32.GetDC(None)
    memory_dc = gdi32.CreateCompatibleDC(screen_dc)
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, WIDTH, HEIGHT)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        draw_reading(
            memory_dc, WIDTH, HEIGHT, bpm, zone, light, mode, background, heart_color, font_face
        )
        # GetDIBits 要求位图不能处于"已选入 DC"的状态，先换出来
        gdi32.SelectObject(memory_dc, previous)

        header = BITMAPINFOHEADER()
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = WIDTH
        header.biHeight = -HEIGHT
        header.biPlanes = 1
        header.biBitCount = 32
        buffer = ctypes.create_string_buffer(WIDTH * HEIGHT * 4)
        gdi32.GetDIBits(memory_dc, bitmap, 0, HEIGHT, buffer, ctypes.byref(header), 0)
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)

    # GDI 画出来的像素不带 alpha（全是 0），用 RGB32 直接当不透明图看待
    image = QImage(bytes(buffer.raw), WIDTH, HEIGHT, QImage.Format_RGB32)
    canvas = QPixmap(WIDTH * scale + 40, HEIGHT * scale + 40)
    from PySide6.QtGui import QColor as _QColor

    if background:
        canvas.fill(_QColor(background))  # 模拟任务栏底色，好判断有没有融进去
    else:
        canvas.fill(0xFF3A3A3A if not light else 0xFFD8D8D8)
    painter = QPainter(canvas)
    from PySide6.QtCore import Qt

    painter.drawImage(
        20, 20,
        image.scaled(WIDTH * scale, HEIGHT * scale, Qt.KeepAspectRatio, Qt.SmoothTransformation),
    )
    painter.end()
    canvas.save(str(OUT / out_name))
    print(f"  已渲染 {out_name}")


def main() -> int:
    cases = [
        ("_preview_widget_normal.png", 86, "normal", False, "card", ""),
        ("_preview_widget_high.png", 158, "high", False, "card", ""),
        ("_preview_widget_low.png", 42, "low", False, "card", ""),
        ("_preview_widget_light.png", 86, "normal", True, "card", ""),
        # 融进任务栏：底色取任务栏自己的颜色（这里用你那张截图里的浅灰模拟）
        ("_preview_widget_blend.png", 78, "normal", True, "auto", "#E8E4E0"),
    ]
    for name, bpm, zone, light, mode, background in cases:
        render(name, bpm, zone, light, mode=mode, background=background)
    print("任务栏组件预览已保存到 tools/_preview_widget_*.png")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
