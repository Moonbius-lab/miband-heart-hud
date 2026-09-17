# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""心率提示弹窗。

动画完全照 FluentFlyout 的 OpenAnimation / CloseAnimation 实现（数值取自其源码）：

    开：位移 20px（从目标位置下方 +20 处滑上来）+ 透明度 0 → 1
    关：位移 20px（向下滑走）+ 透明度 1 → 0
    时长：300ms（FluentFlyout 的"1x"速度就是 300ms，可选 150/300/450/600/900）
    缓动：进场 CubicEase EaseOut，出场 CubicEase EaseIn
    位置：workArea 底部再留 16px —— 即任务栏正上方，右下角对齐

两种形态：
- reading：[♥ 心率 158]  数值按区间变色，卡片宽度按三位的最大宽度预留，不会挤出去
- message：[♥ 休息提醒 · …]  文字提醒
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from . import icons
from .util import log
from .win32 import find_taskbar, make_no_activate, system_uses_light_theme, window_rect
from .widget_render import (
    ICON,
    LABEL_PT,
    PADDING,
    RADIUS,
    draw_content,
    pick_family,
    reading_width,
)
from .zones import HEART_COLOR, ZONE_COLOR

HEIGHT = 46
SLIDE = 20            # 位移距离，取自 FluentFlyout
TASKBAR_MARGIN = 16   # 与任务栏的间距，FluentFlyout 用的是 16
DEFAULT_ANIM_MS = 300


class AlertFlyout(QWidget):
    def __init__(self, config) -> None:
        super().__init__(None)
        self.cfg = config
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._family = pick_family(getattr(config, "font_family", ""))
        self._mode = "reading"
        self._value = ""
        self._text = ""
        self._accent = QColor(ZONE_COLOR["normal"])
        self._heart = QColor(getattr(config, "heart_color", HEART_COLOR))
        self._light = False
        self._native_configured = False
        # 由 app 设置：返回任务栏组件的屏幕矩形，弹窗据此居中对齐
        self.anchor_provider = None
        self._label_font = QFont(self._family, LABEL_PT, QFont.Medium)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._animate_out)

        self._build_animations()

    # -------------------------------------------------------------- 动画搭建
    def _build_animations(self) -> None:
        ms = int(getattr(self.cfg, "animation_ms", DEFAULT_ANIM_MS))

        self._pos_in = QPropertyAnimation(self, b"pos", self)
        self._pos_in.setDuration(ms)
        self._pos_in.setEasingCurve(QEasingCurve.OutCubic)   # CubicEase EaseOut
        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(ms)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_in = QParallelAnimationGroup(self)
        self._anim_in.addAnimation(self._pos_in)
        self._anim_in.addAnimation(self._fade_in)

        self._pos_out = QPropertyAnimation(self, b"pos", self)
        self._pos_out.setDuration(ms)
        self._pos_out.setEasingCurve(QEasingCurve.InCubic)   # CubicEase EaseIn
        self._fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out_anim.setDuration(ms)
        self._fade_out_anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out = QParallelAnimationGroup(self)
        self._anim_out.addAnimation(self._pos_out)
        self._anim_out.addAnimation(self._fade_out_anim)
        self._anim_out.finished.connect(self.hide)

    # ------------------------------------------------------------------ 对外
    def show_alert(self, alert) -> None:
        zone = "normal" if alert.kind == "recover" else alert.kind
        self._set_reading(str(alert.bpm), ZONE_COLOR.get(zone, "#4ADE80"))
        self._present()

    def show_reading(self, bpm: int, zone: str) -> None:
        self._set_reading(str(bpm), ZONE_COLOR.get(zone, "#4ADE80"))
        self._present()

    def show_message(self, text: str) -> None:
        self._set_message(text)
        self._present()

    # 内容设置与"弹出来"分开，方便离线渲染预览而不打扰桌面
    def _set_reading(self, value: str, color: str) -> None:
        self._mode = "reading"
        self._value = value
        self._accent = QColor(color)
        # 宽度按三位数的最大宽度预留：心率变成 158 时也不会被挤出去
        self.setFixedSize(reading_width(self._family), HEIGHT)

    def _set_message(self, text: str) -> None:
        self._mode = "message"
        self._text = text
        self._accent = self._heart
        metrics = QFontMetricsF(self._label_font)
        width = int(PADDING * 2 + ICON + 8 + metrics.horizontalAdvance(text) + 10)
        self.setFixedSize(max(140, width), HEIGHT)

    # ------------------------------------------------------------------ 显示
    def _present(self) -> None:
        self._heart = QColor(getattr(self.cfg, "heart_color", HEART_COLOR))
        self._light = system_uses_light_theme()

        target = self._target_pos()
        appearing = not self.isVisible()
        if appearing:
            # 先隐藏再定位，避免看到跳动（FluentFlyout 也是这么处理的）
            self.setWindowOpacity(0.0)
            self.move(target.x(), target.y() + SLIDE)
            self.show()
        self.raise_()
        self._ensure_native()
        self.update()
        self._hide_timer.start(int(self.cfg.flyout_seconds * 1000))

        if appearing:
            self._anim_out.stop()
            self._pos_in.setStartValue(QPoint(target.x(), target.y() + SLIDE))
            self._pos_in.setEndValue(target)
            self._fade_in.setStartValue(0.0)
            self._fade_in.setEndValue(1.0)
            self._anim_in.start()
        else:  # 已经在显示：别重新播动画，否则每秒闪一次
            self._anim_out.stop()
            self.setWindowOpacity(1.0)
            self.move(target)

    def _ensure_native(self) -> None:
        if self._native_configured:
            return
        try:
            make_no_activate(int(self.winId()))
            self._native_configured = True
        except Exception as exc:  # noqa: BLE001
            log(f"弹窗样式设置失败：{exc!r}")

    def _target_pos(self) -> QPoint:
        """任务栏正上方，水平居中对齐任务栏上的心率组件；没有组件时退回右下角。"""
        screen = QApplication.primaryScreen()
        geometry = screen.geometry() if screen else None
        taskbar = find_taskbar()
        if taskbar and geometry is not None:
            left, top, right, bottom = window_rect(taskbar)
            if bottom >= geometry.bottom() - 4 and top > geometry.top() + 100:
                # 任务栏在屏幕底部 → 贴在它上沿
                y = top - self.height() - TASKBAR_MARGIN
                anchor = self._anchor_rect()
                if anchor is not None:
                    # 组件中心 → 弹窗中心（也就是弹窗出现在组件正上方）
                    center = (anchor[0] + anchor[2]) / 2
                else:
                    center = right - TASKBAR_MARGIN - self.width() / 2
                x = int(center - self.width() / 2)
                x = max(int(geometry.left() + 4), min(x, int(right - self.width() - 4)))
                return QPoint(max(geometry.left(), x), max(geometry.top(), y))

        if screen is not None:
            area = screen.availableGeometry()
            return QPoint(
                max(area.left(), area.right() - self.width() - TASKBAR_MARGIN),
                max(area.top(), area.bottom() - self.height() - TASKBAR_MARGIN // 2),
            )
        return QPoint(0, 0)

    def _anchor_rect(self):
        if self.anchor_provider is None:
            return None
        try:
            return self.anchor_provider()
        except Exception:  # noqa: BLE001
            return None

    def _animate_out(self) -> None:
        if not self.isVisible():
            return
        current = self.pos()
        self._pos_out.setStartValue(current)
        self._pos_out.setEndValue(QPoint(current.x(), current.y() + SLIDE))
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._anim_in.stop()
        self._anim_out.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        self._hide_timer.stop()
        self.hide()

    # ------------------------------------------------------------------ 绘制
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        width, height = self.width(), self.height()
        if self._light:
            top, bottom = QColor(250, 250, 250, 240), QColor(242, 242, 242, 240)
            stroke = QColor(0, 0, 0, 22)
            highlight = QColor(255, 255, 255, 220)
            primary = QColor(26, 26, 26)
            muted = QColor(26, 26, 26, 150)
        else:
            top, bottom = QColor(44, 44, 44, 242), QColor(32, 32, 32, 242)
            stroke = QColor(255, 255, 255, 24)
            highlight = QColor(255, 255, 255, 30)
            primary = QColor(255, 255, 255)
            muted = QColor(255, 255, 255, 150)

        card = QPainterPath()
        card.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), RADIUS, RADIUS)
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)
        painter.fillPath(card, gradient)
        painter.setPen(QPen(stroke, 1))
        painter.drawPath(card)

        painter.setClipPath(card)
        painter.setPen(QPen(highlight, 1))
        painter.drawLine(RADIUS, 1, width - RADIUS, 1)
        painter.setClipping(False)

        if self._mode == "message":
            mid = height / 2
            painter.drawPixmap(
                QPointF(PADDING, mid - ICON / 2),
                icons.render_pixmap(
                    icons.HEART_FILLED, self._heart.name(), ICON, self.devicePixelRatioF()
                ),
            )
            metrics = QFontMetricsF(self._label_font)
            baseline = mid + (metrics.ascent() - metrics.descent()) / 2
            painter.setPen(primary)
            painter.setFont(self._label_font)
            painter.drawText(QPointF(PADDING + ICON + 8, baseline), self._text)
            return

        # 读数行：和任务栏组件调用同一段绘制代码，两边排版强制一致
        draw_content(
            painter,
            width,
            height,
            self._value,
            self._accent,
            muted,
            self._heart.name(),
            self._family,
            self.devicePixelRatioF(),
        )
