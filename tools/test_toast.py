# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""自检：Windows 11 原生通知能不能发出去（发完立刻读通知中心历史核对）。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_hud import toast  # noqa: E402


def main() -> int:
    print("注册通知应用 ID…")
    print("  注册结果：", toast.ensure_registered())

    title = "❤ 心率过高 158"
    body = "158 BPM · 已持续 14 秒（自检）"
    print("发送通知…")
    sent = toast.show(title, body, silent=True, tag="selftest")
    print("  发送结果：", sent)

    time.sleep(1.5)
    history = toast.recent_titles()
    print(f"通知中心历史（{len(history)} 条）：")
    for item in history[:6]:
        print("   ·", item)
    ok = any("心率过高" in item for item in history)
    print()
    print("通知已进入通知中心 ✅" if ok else "没在通知历史里找到这条 ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
