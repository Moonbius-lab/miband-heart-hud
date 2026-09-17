# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""心率区间划分 + 异常事件判定（带去抖、冷却与加剧提醒）。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal, Optional

Zone = Literal["low", "normal", "high"]
AlertKind = Literal["low", "high", "recover"]

# 与 FluentFlyout 的 Fluent 2 配色接近
ZONE_COLOR = {
    "low": "#4CC2FF",
    "normal": "#4ADE80",
    "high": "#FF6B5E",
}

ZONE_LABEL = {
    "low": "心率偏低",
    "normal": "心率正常",
    "high": "心率偏高",
}

# 爱心统一用这个红色（弹窗、任务栏组件、托盘图标都是它）
HEART_COLOR = "#E81123"


@dataclass(frozen=True)
class Alert:
    """一次需要打扰用户的异常事件。"""

    kind: AlertKind      # high / low / recover
    bpm: int             # 触发瞬间的心率
    extreme: int         # 本次异常期间的极值
    duration: float      # 持续秒数
    escalated: bool = False  # True = 异常加剧后的追加提醒

    @property
    def title(self) -> str:
        if self.kind == "recover":
            return "心率已恢复"
        if self.kind == "high":
            return "心率持续偏高" if self.escalated else "心率过高"
        return "心率偏低"

    @property
    def body(self) -> str:
        if self.kind == "recover":
            return f"{self.bpm} BPM · 峰值 {self.extreme}"
        return f"{self.bpm} BPM · 已持续 {int(self.duration)} 秒"

    def toast_title(self) -> str:
        return self.title


class HeartMonitor:
    """把连续 BPM 采样翻译成异常事件。

    判定规则：
    - 进入异常区间后必须连续保持 ``confirm_seconds`` 才提醒（滤掉瞬时抖动手环误报）
    - 恢复后 ``rearm_seconds`` 内不对同一异常重复提醒
    - 异常期间如果又加剧了 ``escalate_step`` BPM，且距上次提醒超过
      ``escalate_interval`` 秒，再提醒一次
    """

    def __init__(
        self,
        high_bpm: int = 150,
        low_bpm: int = 45,
        confirm_seconds: float = 10.0,
        rearm_seconds: float = 30.0,
        escalate_step: int = 15,
        escalate_interval: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.high_bpm = high_bpm
        self.low_bpm = low_bpm
        self.confirm_seconds = confirm_seconds
        self.rearm_seconds = rearm_seconds
        self.escalate_step = escalate_step
        self.escalate_interval = escalate_interval
        self._clock = clock

        self.zone: Zone = "normal"
        self._zone_since = clock()
        self._extreme: Optional[int] = None
        self._alerted: Optional[Zone] = None
        self._alert_since = 0.0
        self._alert_extreme = 0
        self._last_fire: dict[str, float] = {}

    # ------------------------------------------------------------------ 区间
    def zone_of(self, bpm: int) -> Zone:
        if bpm >= self.high_bpm:
            return "high"
        if bpm <= self.low_bpm:
            return "low"
        return "normal"

    def apply(self, bpm: int) -> Optional[Alert]:
        """喂入一个心率采样，返回需要提醒的事件（没有则 None）。"""
        now = self._clock()
        new_zone = self.zone_of(bpm)

        # ---- 区间发生切换 ----
        if new_zone != self.zone:
            previous = self.zone
            self.zone = new_zone
            self._zone_since = now
            self._extreme = bpm

            if new_zone == "normal" and self._alerted is not None:
                alert = Alert(
                    kind="recover",
                    bpm=bpm,
                    extreme=self._alert_extreme,
                    duration=now - self._alert_since,
                )
                self._alerted = None
                return alert
            return None

        # ---- 同一区间内，记录极值 ----
        if self._extreme is None:
            self._extreme = bpm
        elif new_zone == "high":
            self._extreme = max(self._extreme, bpm)
        elif new_zone == "low":
            self._extreme = min(self._extreme, bpm)

        if new_zone == "normal":
            return None

        # ---- 第一次触发 ----
        if self._alerted is None:
            if now - self._zone_since < self.confirm_seconds:
                return None
            if now - self._last_fire.get(new_zone, -1e18) < self.rearm_seconds:
                return None
            self._alerted = new_zone
            self._alert_since = self._zone_since
            self._alert_extreme = self._extreme
            self._last_fire[new_zone] = now
            return Alert(kind=new_zone, bpm=bpm, extreme=self._extreme, duration=now - self._zone_since)

        # ---- 已经在异常中，看是否加剧到值得再提醒一次 ----
        if now - self._last_fire[new_zone] < self.escalate_interval:
            return None
        if new_zone == "high" and self._extreme >= self._alert_extreme + self.escalate_step:
            self._alert_extreme = self._extreme
            self._last_fire[new_zone] = now
            return Alert(
                kind="high",
                bpm=bpm,
                extreme=self._extreme,
                duration=now - self._alert_since,
                escalated=True,
            )
        if new_zone == "low" and self._extreme <= self._alert_extreme - self.escalate_step:
            self._alert_extreme = self._extreme
            self._last_fire[new_zone] = now
            return Alert(
                kind="low",
                bpm=bpm,
                extreme=self._extreme,
                duration=now - self._alert_since,
                escalated=True,
            )
        return None
