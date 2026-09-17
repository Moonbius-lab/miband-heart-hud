# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""自检：心率异常判定逻辑（不依赖手环）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_hud.zones import HeartMonitor  # noqa: E402
from hr_hud.util import setup_console  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def tick(self, seconds: float) -> None:
        self.now += seconds


def feed(monitor: HeartMonitor, clock: FakeClock, bpm: int, seconds: float, step: float = 1.0):
    """按 step 秒喂入同一个心率，收集产生的事件。"""
    events = []
    remaining = seconds
    while remaining > 0:
        clock.tick(step)
        event = monitor.apply(bpm)
        if event is not None:
            events.append(event)
        remaining -= step
    return events


def main() -> int:
    setup_console()
    clock = FakeClock()
    monitor = HeartMonitor(
        high_bpm=150, low_bpm=45, confirm_seconds=10, rearm_seconds=30,
        escalate_step=15, escalate_interval=60, clock=clock,
    )
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'✅' if condition else '❌'} {name}{'' if condition else '  ' + detail}")
        if not condition:
            failures.append(name)

    # 1. 正常心率不打扰
    events = feed(monitor, clock, 72, 30)
    check("正常心率 30 秒内不提醒", not events, f"实际 {events}")

    # 2. 瞬时抖动（3 秒）不提醒
    events = feed(monitor, clock, 168, 3)
    check("心率抖动 3 秒不提醒", not events, f"实际 {events}")
    events = feed(monitor, clock, 80, 20)
    check("抖动后回落不提醒", not events, f"实际 {events}")

    # 3. 持续偏高 → 到点提醒一次
    events = feed(monitor, clock, 158, 25)
    check("持续偏高触发 1 次提醒", len(events) == 1, f"实际 {len(events)} 次")
    check("提醒类型是 high", events and events[0].kind == "high", f"实际 {events}")
    check("提醒心率正确", events and events[0].bpm >= 155, f"实际 {events}")

    # 4. 维持同一水平不再刷屏
    events = feed(monitor, clock, 160, 40)
    check("持续同一水平不重复刷屏", not events, f"实际 {events}")

    # 5. 加剧 15 BPM 以上再提醒一次（前提是距上次提醒已超过 escalate_interval）
    events = feed(monitor, clock, 178, 12)
    check("加剧后追加提醒", len(events) == 1 and events[0].escalated, f"实际 {events}")

    # 6. 回落 → 恢复提醒
    events = feed(monitor, clock, 78, 5)
    check("恢复后提醒一次", len(events) == 1 and events[0].kind == "recover", f"实际 {events}")

    # 7. 偏低
    events = feed(monitor, clock, 38, 15)
    check("持续偏低触发提醒", len(events) == 1 and events[0].kind == "low", f"实际 {events}")
    events = feed(monitor, clock, 70, 5)
    check("偏低恢复提醒", len(events) == 1 and events[0].kind == "recover", f"实际 {events}")

    print()
    if failures:
        print(f"{len(failures)} 项未通过：{', '.join(failures)}")
        return 1
    print("判定逻辑全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
