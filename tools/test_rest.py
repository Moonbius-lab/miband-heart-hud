# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""自检：休息提醒的时段判断与提醒节奏（不依赖真实时间）。"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_hud.rest import RestReminder, in_window, parse_hhmm  # noqa: E402
from hr_hud.util import setup_console  # noqa: E402


def at(hour: int, minute: int, day: int = 17) -> datetime:
    return datetime(2026, 9, day, hour, minute)


def main() -> int:
    setup_console()
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'✅' if condition else '❌'} {name}{'' if condition else '  ' + detail}")
        if not condition:
            failures.append(name)

    check("非法时间返回 None", parse_hhmm("25:99") is None and parse_hhmm("abc") is None)

    start, end = parse_hhmm("23:00"), parse_hhmm("07:00")
    check("23:30 在时段内", in_window(parse_hhmm("23:30"), start, end))
    check("02:00 在时段内（跨零点）", in_window(parse_hhmm("02:00"), start, end))
    check("12:00 不在时段内", not in_window(parse_hhmm("12:00"), start, end))
    check("07:00 边界已离开", not in_window(parse_hhmm("07:00"), start, end))
    check("23:00 边界刚进入", in_window(parse_hhmm("23:00"), start, end))

    reminder = RestReminder(start="23:00", end="07:00", interval_minutes=60)
    check("22:59 不提醒", not reminder.due(at(22, 59), receiving=False))
    check("23:00 进入时段立刻提醒", reminder.due(at(23, 0), receiving=False))
    reminder.mark(at(23, 0))
    check("23:30 一小时内不重复", not reminder.due(at(23, 30), receiving=False))
    check("23:59 仍不重复", not reminder.due(at(23, 59), receiving=False))
    check("00:00 满一小时再提醒", reminder.due(at(0, 0, day=18), receiving=False))
    reminder.mark(at(0, 0, day=18))

    check("广播开着时 02:00 不提醒", not reminder.due(at(2, 0, day=18), receiving=True))
    check("广播开着时也不清零计时", reminder.last_reminded == at(0, 0, day=18))

    check("07:00 离开时段不提醒", not reminder.due(at(7, 0, day=18), receiving=False))
    check("离开时段会清零计时", reminder.last_reminded is None)
    check("晚上 23:00 重新立刻提醒", reminder.due(at(23, 0, day=18), receiving=False))
    reminder.mark(at(23, 0, day=18))
    check("跨零点后再满一小时提醒", reminder.due(at(23, 0, day=18) + timedelta(hours=1), receiving=False))

    reminder.enabled = False
    check("关闭开关后不提醒", not reminder.due(at(23, 30, day=18), receiving=False))
    reminder.enabled = True
    reminder.start = "25:00"
    check("时段配置非法时不提醒", not reminder.due(at(23, 30, day=18), receiving=False))

    print()
    if failures:
        print(f"{len(failures)} 项未通过：{', '.join(failures)}")
        return 1
    print("休息提醒逻辑全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
