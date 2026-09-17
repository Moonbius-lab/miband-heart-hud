# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""休息提醒。

规则：
- 进入设定的"不健康时段"（默认 23:00 → 07:00，可跨零点）后开始提醒
- 每小时提醒一次：按时休息 + 打开手环心率广播确认心率
- **如果心率广播已经开着（正在收到数据），就完全不打扰，正常工作**
- 离开时段后计时清零，下次进入时段重新开始算
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as clock_time, timedelta
from typing import Optional


def parse_hhmm(value: str) -> Optional[clock_time]:
    try:
        hour_text, minute_text = str(value).strip().split(":")
        hour, minute = int(hour_text), int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return clock_time(hour, minute)
    except (ValueError, AttributeError):
        pass
    return None


def in_window(now: clock_time, start: clock_time, end: clock_time) -> bool:
    """判断当前时间是否落在时段内（支持跨零点，如 23:00 → 07:00）。"""
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


@dataclass
class RestReminder:
    start: str = "23:00"
    end: str = "07:00"
    interval_minutes: int = 60
    enabled: bool = True
    last_reminded: Optional[datetime] = field(default=None, repr=False)

    def window(self) -> tuple[Optional[clock_time], Optional[clock_time]]:
        return parse_hhmm(self.start), parse_hhmm(self.end)

    def due(self, now: datetime, receiving: bool) -> bool:
        """现在该不该提醒？receiving=True 表示心率广播已经开着。"""
        if not self.enabled:
            return False
        start, end = self.window()
        if start is None or end is None:
            return False
        if not in_window(now.time(), start, end):
            self.last_reminded = None  # 离开时段，下次进来重新计时
            return False
        if receiving:
            return False  # 广播已经开着 → 不打扰，正常工作
        if self.last_reminded is None:
            return True
        return now - self.last_reminded >= timedelta(minutes=max(1, int(self.interval_minutes)))

    def mark(self, now: datetime) -> None:
        self.last_reminded = now

    def describe(self) -> str:
        state = "开启" if self.enabled else "关闭"
        return f"{self.start} → {self.end}，每 {int(self.interval_minutes)} 分钟一次（{state}）"
