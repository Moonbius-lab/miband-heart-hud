# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""图标统一来自微软 Fluent UI System Icons（MIT 协议）。

来源：https://github.com/microsoft/fluentui-system-icons
文件放在 assets/icons/ 下，用的时候把 SVG 里的填充色替换成需要的颜色再渲染。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "icons"
HEART_FILLED = "ic_fluent_heart_24_filled.svg"
HEART_REGULAR = "ic_fluent_heart_20_regular.svg"


@lru_cache(maxsize=32)
def svg_bytes(name: str, color: str) -> bytes:
    """读出 SVG 并把填充色换成指定颜色。"""
    text = (ASSETS / name).read_text(encoding="utf-8")
    return text.replace('fill="#212121"', f'fill="{color}"').encode("utf-8")


def _render_image(name: str, color: str, pixels: int):
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(pixels, pixels, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    renderer = QSvgRenderer(QByteArray(svg_bytes(name, color)))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


@lru_cache(maxsize=32)
def render_argb(name: str, color: str, pixels: int) -> bytes:
    """32 位预乘 ARGB 像素，GDI 的 AlphaBlend 可以直接用。"""
    return bytes(_render_image(name, color, pixels).constBits())


@lru_cache(maxsize=32)
def render_pixmap(name: str, color: str, size: int, dpr: float = 1.0):
    from PySide6.QtGui import QPixmap

    image = _render_image(name, color, max(8, int(round(size * dpr))))
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(dpr)
    return pixmap
