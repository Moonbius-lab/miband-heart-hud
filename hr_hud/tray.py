# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""系统托盘图标与菜单。"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QActionGroup, QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QInputDialog, QMenu, QSystemTrayIcon

from .config import APP_DIR, CONFIG_PATH
from . import icons
from .zones import HEART_COLOR, ZONE_COLOR


def make_icon(bpm: Optional[int], zone: str, connected: bool, color: str = HEART_COLOR) -> QIcon:
    """托盘图标同样用 Fluent UI System Icons 的 SVG，多档尺寸保证清晰。"""
    if not connected or bpm is None:
        color = "#8C8C8C"
    icon = QIcon()
    for size in (16, 20, 24, 32, 48):
        icon.addPixmap(icons.render_pixmap(icons.HEART_FILLED, color, size, 1.0))
    return icon


class TrayIcon(QSystemTrayIcon):
    quit_requested = Signal()
    reconnect_requested = Signal()
    widget_toggled = Signal(bool)
    toast_toggled = Signal(bool)
    flyout_toggled = Signal(bool)
    notify_mode_changed = Signal(str, int)
    thresholds_changed = Signal(int, int)
    rest_toggled = Signal(bool)
    rest_window_changed = Signal(str, str)
    test_alert_requested = Signal()

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self.cfg = config
        self.setIcon(make_icon(None, "normal", False))
        self.setToolTip("小米手环心率 · 正在启动…")

        menu = QMenu()
        self._status = menu.addAction("正在启动…")
        self._status.setEnabled(False)
        menu.addSeparator()

        self._widget_action = menu.addAction("显示在任务栏")
        self._widget_action.setCheckable(True)
        self._widget_action.setChecked(bool(config.widget_enabled))
        self._widget_action.toggled.connect(self.widget_toggled.emit)

        self._toast_action = menu.addAction("心率异常时发送系统通知")
        self._toast_action.setCheckable(True)
        self._toast_action.setChecked(bool(config.notify_toast))
        self._toast_action.toggled.connect(self.toast_toggled.emit)

        self._flyout_action = menu.addAction("心率异常时弹出卡片")
        self._flyout_action.setCheckable(True)
        self._flyout_action.setChecked(bool(config.notify_flyout))
        self._flyout_action.toggled.connect(self.flyout_toggled.emit)

        timing = menu.addMenu("提醒时机")
        self._timing_group = QActionGroup(self)
        entries = [
            ("仅在心率异常时提醒", "alert", 0),
            ("定时显示当前心率（每分钟）", "periodic", 60),
            ("定时显示当前心率（每 5 分钟）", "periodic", 300),
            ("每次心率更新都显示", "every", 0),
        ]
        self._mode_actions: list[tuple[object, str, int]] = []
        current = (str(config.notify_mode), int(getattr(config, "reading_interval_seconds", 60)))
        for label, mode, interval in entries:
            action = timing.addAction(label)
            action.setCheckable(True)
            self._timing_group.addAction(action)
            if mode == "periodic":
                checked = current[0] == "periodic" and (
                    current[1] == interval or (interval == 60 and current[1] < 300)
                )
            else:
                checked = current[0] == mode
            action.setChecked(checked)
            action.triggered.connect(
                lambda _checked=False, m=mode, i=interval: self.notify_mode_changed.emit(m, i)
            )
            self._mode_actions.append((action, mode, interval))

        self._rest_action = menu.addAction("不健康时段休息提醒")
        self._rest_action.setCheckable(True)
        self._rest_action.setChecked(bool(config.rest_reminder))
        self._rest_action.toggled.connect(self.rest_toggled.emit)
        menu.addAction("设置休息时段…", self._edit_rest_window)

        menu.addSeparator()
        menu.addAction("重新连接", self.reconnect_requested.emit)
        menu.addAction("发送一条测试提醒", self.test_alert_requested.emit)
        menu.addAction("设置心率阈值…", self._edit_thresholds)
        menu.addAction("打开配置文件夹", self._open_config)
        menu.addSeparator()
        menu.addAction("退出", self.quit_requested.emit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.show()

    # ---------------------------------------------------------------- 交互
    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            menu = self.contextMenu()
            if menu is not None:
                menu.popup(QCursor.pos())

    def popup_menu(self) -> None:
        """在鼠标位置弹出设置菜单（托盘图标或任务栏组件被点击时调用）。"""
        menu = self.contextMenu()
        if menu is not None:
            menu.popup(QCursor.pos())

    def _edit_thresholds(self) -> None:
        high, ok = QInputDialog.getInt(
            None, "心率上限", "高于多少 BPM 算心率过高？", int(self.cfg.high_bpm), 80, 220, 1
        )
        if not ok:
            return
        low, ok = QInputDialog.getInt(
            None, "心率下限", "低于多少 BPM 算心率偏低？", int(self.cfg.low_bpm), 25, 90, 1
        )
        if not ok:
            return
        self.cfg.high_bpm, self.cfg.low_bpm = high, low
        self.cfg.save()
        self.thresholds_changed.emit(high, low)

    @staticmethod
    def _open_config() -> None:
        from .util import log

        APP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(APP_DIR)  # noqa: S606 - 打开配置目录
        except OSError:
            pass

    def _edit_rest_window(self) -> None:
        from .rest import parse_hhmm
        from .util import log

        start, ok = QInputDialog.getText(
            None, "休息时段", "从几点开始提醒？（24 小时制，如 23:00）", text=str(self.cfg.rest_start)
        )
        if not ok:
            return
        if parse_hhmm(start) is None:
            log(f"休息时段格式不对，已忽略：{start!r}（应为 23:00 这种）")
            return
        end, ok = QInputDialog.getText(
            None, "休息时段", "到几点结束？（可跨零点，如 07:00）", text=str(self.cfg.rest_end)
        )
        if not ok:
            return
        if parse_hhmm(end) is None:
            log(f"休息时段格式不对，已忽略：{end!r}（应为 07:00 这种）")
            return
        self.cfg.rest_start, self.cfg.rest_end = start.strip(), end.strip()
        self.rest_window_changed.emit(start.strip(), end.strip())

    # ---------------------------------------------------------------- 状态
    def update_state(self, connected: bool, bpm: Optional[int], zone: str, status: str) -> None:
        self.setIcon(make_icon(bpm, zone, connected, getattr(self.cfg, "heart_color", HEART_COLOR)))
        lines = [f"{bpm} BPM" if bpm else "-- BPM", status]
        if bpm:
            label = {"high": "偏高", "low": "偏低", "normal": "正常"}[zone]
            lines.insert(1, f"状态：{label}")
        lines.append(f"配置：{CONFIG_PATH}")
        self.setToolTip("小米手环心率\n" + "\n".join(lines))
        self._status.setText(f"{bpm} BPM · {status}" if bpm else status)
