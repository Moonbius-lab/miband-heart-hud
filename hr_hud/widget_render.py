# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""卡片画面的共用渲染。

弹窗（flyout）和任务栏组件（taskbar）都调用这里的 draw_content，
"爱心 + 心率 + 数值"这一行的排版、字号、基线因此强制保持一致，
不会出现两边长得不一样的问题。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from . import icons
from .zones import ZONE_COLOR

# ---- 共用排版参数（弹窗和组件都用这一套）----
PADDING = 12      # 左边距
ICON = 16         # 爱心图标尺寸
ICON_GAP = 8      # 图标与文字之间
LABEL_PT = 14     # "心率"字号（与数值同号，靠字重和颜色区分）
VALUE_GAP = 10    # "心率"与数值之间
VALUE_PT = 14     # 数值字号
RADIUS = 8        # 卡片圆角（和弹窗一致）

CARD_LIGHT = ("#FCFCFC", "#F0F0F0", "#E1E1E1", "#FFFFFF")
CARD_DARK = ("#2E2E2E", "#232323", "#3D3D3D", "#4A4A4A")


def pick_family(preferred: str = "") -> str:
    """中文字和数字用同一字族，避免两套字形拼在一起不贴合。"""
    available = set(QFontDatabase.families())
    candidates = [preferred] if preferred else []
    candidates += ["Microsoft YaHei UI", "Segoe UI Variable Text", "Segoe UI Variable Display", "Segoe UI"]
    for name in candidates:
        if name and name in available:
            return name
    return "Segoe UI"


def reading_width(family: str, label_pt: int = LABEL_PT, value_pt: int = VALUE_PT) -> int:
    """卡片宽度：按"心率 + 三位数"的最宽情况预留，两边共用同一个宽度。"""
    label = QFontMetricsF(QFont(family, label_pt, QFont.Medium)).horizontalAdvance("心率")
    widest = QFontMetricsF(QFont(family, value_pt, QFont.DemiBold)).horizontalAdvance("888")
    return int(PADDING * 2 + ICON + ICON_GAP + label + VALUE_GAP + widest)


def draw_content(
    painter: QPainter,
    width: int,
    height: int,
    value: str,
    color: QColor,
    muted: QColor,
    heart_color: str,
    family: str,
    dpr: float = 1.0,
    label_pt: int = LABEL_PT,
    value_pt: int = VALUE_PT,
) -> None:
    """"爱心 + 心率 + 数值"这一行 —— 弹窗和任务栏组件共用这段代码。"""
    mid = height / 2
    painter.drawPixmap(
        QPointF(PADDING, mid - ICON / 2),
        icons.render_pixmap(icons.HEART_FILLED, heart_color, ICON, dpr),
    )

    label_font = QFont(family, label_pt, QFont.Medium)
    value_font = QFont(family, value_pt, QFont.DemiBold)
    value_metrics = QFontMetricsF(value_font)
    baseline = mid + (value_metrics.ascent() - value_metrics.descent()) / 2

    cursor = PADDING + ICON + ICON_GAP
    painter.setFont(label_font)
    painter.setPen(muted)
    painter.drawText(QPointF(cursor, baseline), "心率")

    value_x = cursor + QFontMetricsF(label_font).horizontalAdvance("心率") + VALUE_GAP
    painter.setFont(value_font)
    painter.setPen(color)
    painter.drawText(QPointF(value_x, baseline), value)


def render_card(
    width: int,
    height: int,
    bpm,
    zone: str,
    light_theme: bool,
    heart_color: str,
    family: str,
    mode: str = "card",
    background: str = "",
    dpr: float = 1.0,
    label_pt: int = LABEL_PT,
    value_pt: int = VALUE_PT,
) -> QImage:
    """任务栏组件的整张卡片：圆角底 + 与弹窗完全一致的内容行。"""
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    if mode != "clear":
        top, bottom, border, highlight = CARD_LIGHT if light_theme else CARD_DARK
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), RADIUS, RADIUS)
        if background:
            painter.fillPath(path, QColor(background))
        else:
            gradient = QLinearGradient(0, 0, 0, height)
            gradient.setColorAt(0.0, QColor(top))
            gradient.setColorAt(1.0, QColor(bottom))
            painter.fillPath(path, gradient)
        if not background:
            # 自带卡片时才描边+高光；用任务栏底色的"融进去"模式什么都不画
            painter.setPen(QPen(QColor(border), 1))
            painter.drawPath(path)
            painter.setClipPath(path)
            painter.setPen(QPen(QColor(highlight), 1))
            painter.drawLine(RADIUS + 1, 1, width - RADIUS - 1, 1)
            painter.setClipping(False)

    muted = QColor(26, 26, 26, 150) if light_theme else QColor(255, 255, 255, 150)
    color = QColor(ZONE_COLOR.get(zone, "#4ADE80")) if bpm else QColor("#909090")
    draw_content(
        painter,
        width,
        height,
        str(bpm) if bpm else "--",
        color,
        muted,
        heart_color,
        family,
        dpr,
        label_pt,
        value_pt,
    )
    painter.end()
    return image
