# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""把 BLE 读取、任务栏组件、通知与托盘串起来。"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from . import toast
from .ble import HeartRateReader
from .flyout import AlertFlyout
from .rest import RestReminder
from .taskbar import TaskbarWidget
from .tray import TrayIcon
from .util import log
from .win32 import is_taskbar_visible, system_uses_light_theme
from .zones import HEART_COLOR, ZONE_COLOR, ZONE_LABEL, Alert, HeartMonitor

# 演示模式的心率曲线：(持续秒数, 目标 BPM)
DEMO_SEGMENTS = [
    (12.0, 74.0),
    (14.0, 152.0),
    (22.0, 176.0),
    (12.0, 120.0),
    (14.0, 76.0),
]


class HeartApp(QObject):
    bpm_received = Signal(int)
    status_received = Signal(bool, str)

    def __init__(self, config, demo: bool = False, test_alert: bool = False) -> None:
        super().__init__()
        self.cfg = config
        self.demo = demo
        self._connected = False
        self._status_text = "演示模式" if demo else "启动中…"
        self._bpm: Optional[int] = None
        self._demo_t = 0.0
        self._reader: Optional[HeartRateReader] = None
        self._started_at = time.monotonic()
        self._ever_connected = False
        self._last_reading_popup = 0.0

        self.monitor = HeartMonitor(
            high_bpm=config.high_bpm,
            low_bpm=config.low_bpm,
            confirm_seconds=config.confirm_seconds,
            rearm_seconds=config.rearm_seconds,
            escalate_step=config.escalate_step,
            escalate_interval=config.escalate_interval,
        )

        self.widget = TaskbarWidget(config)
        self.widget.light_theme = system_uses_light_theme()
        self.flyout = AlertFlyout(config)
        # 弹窗水平居中在任务栏心率组件正上方
        self.flyout.anchor_provider = self.widget.current_rect
        self.tray = TrayIcon(config)
        self.rest = RestReminder(
            start=config.rest_start,
            end=config.rest_end,
            interval_minutes=config.rest_interval_minutes,
            enabled=config.rest_reminder,
        )

        self.bpm_received.connect(self._on_bpm)
        self.status_received.connect(self._on_status)
        self.tray.quit_requested.connect(self.shutdown)
        self.tray.reconnect_requested.connect(self.reconnect)
        self.tray.widget_toggled.connect(self._on_widget_toggled)
        self.tray.toast_toggled.connect(self._on_toast_toggled)
        self.tray.flyout_toggled.connect(self._on_flyout_toggled)
        self.tray.notify_mode_changed.connect(self._on_notify_mode_changed)
        self.tray.thresholds_changed.connect(self._on_thresholds)
        self.tray.rest_toggled.connect(self._on_rest_toggled)
        self.tray.rest_window_changed.connect(self._on_rest_window_changed)
        self.tray.test_alert_requested.connect(self._fire_test_alert)

        if test_alert:
            QTimer.singleShot(1200, self._fire_test_alert)

    # ------------------------------------------------------------ 生命周期
    def start(self) -> None:
        self._warm_icons()
        self.widget.set_visible(self.cfg.widget_enabled)
        self.widget.start()
        toast.ensure_registered()
        self._rest_timer = QTimer(self)
        self._rest_timer.timeout.connect(self._check_rest)
        self._rest_timer.start(60_000)  # 每分钟检查一次，到点才提醒
        QTimer.singleShot(6_000, self._check_rest)  # 启动时先看一眼，别等满一分钟
        if self.demo:
            self._demo_timer = QTimer(self)
            self._demo_timer.timeout.connect(self._demo_tick)
            self._demo_timer.start(1000)
            self._on_status(True, "演示模式（模拟心率）")
            log("已进入演示模式：用模拟心率验证任务栏组件与提醒")
            return
        self._start_reader()

    @staticmethod
    def _warm_icons() -> None:
        """先把 SVG 图标渲染进缓存：组件在自己的线程里绘制，首次渲染放主线程更稳妥。"""
        from . import icons
        from .taskbar import HEART

        for color in (*ZONE_COLOR.values(), "#909090", "#8C8C8C", HEART_COLOR):
            icons.render_argb(icons.HEART_FILLED, color, HEART)

    def _start_reader(self) -> None:
        self._reader = HeartRateReader(
            address=self.cfg.device_address,
            name_hint=self.cfg.device_name,
            on_bpm=self.bpm_received.emit,
            on_status=self.status_received.emit,
        )
        self._reader.start()
        log("已启动蓝牙心率读取线程")

    def reconnect(self) -> None:
        if self.demo:
            self._on_status(True, "演示模式（模拟心率）")
            return
        if self._reader:
            self._reader.stop()
        self._on_status(False, "正在重新连接…")
        QTimer.singleShot(500, self._start_reader)

    def shutdown(self) -> None:
        log("正在退出…")
        if self._reader:
            self._reader.stop()
        self.widget.stop()
        self.tray.hide()
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def teardown(self) -> None:
        """按顺序销毁 Qt 对象。进程关停时顺序乱了会踩内存，必须显式做。"""
        from PySide6.QtWidgets import QApplication

        try:
            self.flyout.hide()
            self.flyout.deleteLater()
            self.tray.hide()
            self.tray.deleteLater()
            QApplication.processEvents()
        except Exception as exc:  # noqa: BLE001
            log(f"清理界面对象时出错（可忽略）：{exc!r}")

    # ---------------------------------------------------------------- 数据
    def _demo_tick(self) -> None:
        self._demo_t += 1.0
        total = sum(duration for duration, _ in DEMO_SEGMENTS)
        position = self._demo_t % total
        previous = DEMO_SEGMENTS[-1][1]
        for duration, target in DEMO_SEGMENTS:
            if position <= duration:
                fraction = position / duration
                value = previous + (target - previous) * fraction
                self.bpm_received.emit(int(value + random.uniform(-2.5, 2.5)))
                return
            position -= duration
            previous = target
        self.bpm_received.emit(int(previous))

    def _on_bpm(self, bpm: int) -> None:
        self._bpm = bpm
        alert = self.monitor.apply(bpm)
        zone = self.monitor.zone
        self.widget.set_values(bpm, zone)
        self.tray.update_state(self._connected, bpm, zone, self._status_text)

        # 优先级：危险心率 > 定时/每次读数。
        # 紧急情况直接弹，不受"定时显示"的间隔限制；同时把定时重新起算，
        # 避免刚弹完危险提醒又紧接着弹一次例行读数。
        if alert is not None and self._alert_enabled(alert):
            self._last_reading_popup = time.monotonic()
            self._emit_alert(alert)
            return

        mode = str(getattr(self.cfg, "notify_mode", "alert"))
        if mode == "every" and self._routine_popup_allowed():
            # 每次手环上报都刷新卡片
            if self.cfg.notify_flyout:
                self.flyout.show_reading(bpm, zone)
            if self.cfg.notify_every_toast:
                toast.show(
                    f"{bpm} BPM", ZONE_LABEL.get(zone, ""), silent=bool(self.cfg.toast_silent), tag="reading"
                )
        elif mode == "periodic" and self._routine_popup_allowed():
            # 定时报一下当前心率（默认每分钟一次，可配）
            interval = max(5, int(getattr(self.cfg, "reading_interval_seconds", 60)))
            if time.monotonic() - self._last_reading_popup >= interval:
                self._last_reading_popup = time.monotonic()
                if self.cfg.notify_flyout:
                    self.flyout.show_reading(bpm, zone)

    def _routine_popup_allowed(self) -> bool:
        """例行读数弹窗是否该出现。

        任务栏看得见时就不弹——组件上已经显示着心率了，弹窗纯属重复打扰。
        只有任务栏被全屏游戏盖住/隐藏时才需要弹窗兜底。
        """
        if not bool(getattr(self.cfg, "popup_only_when_taskbar_hidden", True)):
            return True
        if not self.cfg.widget_enabled or self.widget.current_rect() is None:
            return True  # 组件没在显示，弹窗就是唯一出口
        return not is_taskbar_visible()

    def _on_status(self, connected: bool, text: str) -> None:
        changed = (connected, text) != (self._connected, self._status_text)
        self._connected = connected
        self._status_text = text
        if connected:
            self._ever_connected = True
        if not connected:
            self._bpm = None
            self.widget.set_values(None, "normal")
            self.tray.update_state(False, None, "normal", text)
        else:
            self.tray.update_state(True, self._bpm, self.monitor.zone, text)
            if self._reader and self._reader.address and self._reader.address != self.cfg.device_address:
                self.cfg.device_address = self._reader.address
                self.cfg.save()
        if changed:  # 状态没变就别刷屏（比如反复"未找到设备"）
            log(f"连接状态：{'已连接' if connected else '未连接'} · {text}")

    # ---------------------------------------------------------------- 提醒
    def _emit_alert(self, alert: Alert) -> None:
        if not self._alert_enabled(alert):
            return
        log(f"触发提醒：{alert.title} {alert.bpm} BPM（{alert.body}）")
        if self.cfg.notify_toast:
            toast.show(alert.toast_title(), alert.body, silent=bool(self.cfg.toast_silent))
        if self.cfg.notify_flyout:
            self.flyout.show_alert(alert)

    def _alert_enabled(self, alert: Alert) -> bool:
        if alert.kind == "recover" and not self.cfg.notify_recover:
            return False
        if alert.kind == "high" and not self.cfg.notify_high:
            return False
        if alert.kind == "low" and not self.cfg.notify_low:
            return False
        return True

    def _fire_test_alert(self) -> None:
        self._emit_alert(Alert(kind="high", bpm=158, extreme=163, duration=14.0))


    # ---------------------------------------------------------------- 设置
    def _on_widget_toggled(self, enabled: bool) -> None:
        self.cfg.widget_enabled = enabled
        self.cfg.save()
        self.widget.set_visible(enabled)

    def _on_toast_toggled(self, enabled: bool) -> None:
        self.cfg.notify_toast = enabled
        self.cfg.save()

    def _on_flyout_toggled(self, enabled: bool) -> None:
        self.cfg.notify_flyout = enabled
        self.cfg.save()

    def _on_thresholds(self, high: int, low: int) -> None:
        self.monitor.high_bpm = high
        self.monitor.low_bpm = low
        log(f"阈值已更新：高 {high} / 低 {low}")

    def _on_notify_mode_changed(self, mode: str, interval: int = 0) -> None:
        self.cfg.notify_mode = mode if mode in ("alert", "periodic", "every") else "alert"
        if interval:
            self.cfg.reading_interval_seconds = int(interval)
        self._last_reading_popup = 0.0
        self.cfg.save()
        if self.cfg.notify_mode != "every":
            self.flyout.hide()
        describe = {
            "alert": "仅心率异常时",
            "periodic": f"每 {int(self.cfg.reading_interval_seconds)} 秒显示一次",
            "every": "每次心率更新",
        }[self.cfg.notify_mode]
        log(f"提醒时机已切换：{describe}")

    # ------------------------------------------------------------ 休息提醒
    def _check_rest(self) -> None:
        """每分钟看一眼：在不健康时段里、且心率广播没开，才每小时提醒一次。"""
        now = datetime.now()
        receiving = self._connected and self._bpm is not None
        if not receiving and not self._ever_connected:
            grace = int(getattr(self.cfg, "rest_startup_grace_seconds", 90))
            if time.monotonic() - self._started_at < grace:
                return  # 刚启动、蓝牙还在连，先别急着判定"没开心率广播"
        if self.rest.due(now, receiving):
            self.rest.mark(now)
            self._fire_rest_reminder()

    def _fire_rest_reminder(self) -> None:
        log(f"休息提醒：请开启手环心率广播（时段 {self.rest.describe()}）")
        if self.cfg.notify_flyout:
            self.flyout.show_message("休息提醒 · 请开启心率广播")
        if self.cfg.notify_toast:
            toast.show(
                "休息提醒",
                "请开启手环「心率广播」，以确认当前心率状态",
                silent=bool(self.cfg.toast_silent),
                tag="rest",
            )

    def _on_rest_toggled(self, enabled: bool) -> None:
        self.cfg.rest_reminder = enabled
        self.rest.enabled = enabled
        self.rest.last_reminded = None
        self.cfg.save()
        log(f"休息提醒已{'开启' if enabled else '关闭'}（{self.rest.describe()}）")

    def _on_rest_window_changed(self, start: str, end: str) -> None:
        self.cfg.rest_start, self.cfg.rest_end = start, end
        self.rest.start, self.rest.end = start, end
        self.rest.last_reminded = None
        self.cfg.save()
        log(f"休息时段已改为 {self.rest.describe()}")
