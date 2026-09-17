# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""检查弹窗外观与"每次更新都提醒"链路。

- `python tools/preview_flyout.py visual` 用真实渲染引擎把弹窗画成 PNG（只渲染，不显示窗口）
- `python tools/preview_flyout.py logic`  用 offscreen 平台跑一遍每秒刷新的调用链
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hr_hud.config import Config  # noqa: E402
from hr_hud.flyout import AlertFlyout  # noqa: E402
from hr_hud.zones import ZONE_COLOR, Alert  # noqa: E402

OUT = Path(__file__).resolve().parent


def composite(widget, background: str, scale: int = 3) -> QPixmap:
    """把弹窗按 scale 倍放大贴到纯色底上，方便肉眼检查字与排版。"""
    shot = widget.grab()
    shot = shot.scaled(
        shot.width() * scale, shot.height() * scale, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    canvas = QPixmap(shot.width() + 40, shot.height() + 40)
    canvas.fill(QColor(background))
    painter = QPainter(canvas)
    painter.drawPixmap(20, 20, shot)
    painter.end()
    return canvas


def visual() -> int:
    """用真实平台渲染到位图。只 grab()，不 show()，屏幕上不会出现任何窗口。"""
    app = QApplication(["preview"])
    config = Config()

    cases = [
        ("dark_reading_normal", False, lambda f: f._set_reading("86", ZONE_COLOR["normal"])),
        ("dark_reading_high", False, lambda f: f._set_reading("158", ZONE_COLOR["high"])),
        ("dark_reading_low", False, lambda f: f._set_reading("42", ZONE_COLOR["low"])),
        ("dark_message_rest", False, lambda f: f._set_message("休息提醒 · 请开启心率广播")),
        ("light_reading_high", True, lambda f: f._set_reading("158", ZONE_COLOR["high"])),
        ("light_message_rest", True, lambda f: f._set_message("休息提醒 · 请开启心率广播")),
    ]
    for name, light, setup in cases:
        flyout = AlertFlyout(config)
        flyout._light = light
        setup(flyout)
        app.processEvents()
        composite(flyout, "#D8D8D8" if light else "#4A4A4A").save(str(OUT / f"_preview_{name}.png"))
        print(f"  已渲染 {name}（{flyout.width()}x{flyout.height()}）")
        flyout.deleteLater()
    print("外观预览已保存到 tools/_preview_*.png")
    return 0


def logic() -> int:
    app = QApplication(["preview", "-platform", "offscreen"])
    config = Config()
    flyout = AlertFlyout(config)

    flyout.show_alert(Alert(kind="high", bpm=158, extreme=163, duration=14.0))
    app.processEvents()
    print(f"  异常弹窗：数值={flyout._value!r}")

    for index in range(60):  # 模拟每秒一次的心率更新
        flyout.show_reading(80 + index % 60, "high" if index % 60 > 40 else "normal")
        app.processEvents()
    print(f"  连续刷新 60 次后仍可见：{flyout.isVisible()}（每次更新模式要求一直挂着）")

    flyout.show_message("休息提醒 · 请开启心率广播")
    app.processEvents()
    print(f"  休息提醒卡片宽度：{flyout.width()}")

    try:
        from hr_hud.app import HeartApp

        config.notify_mode = "every"
        hub = HeartApp(config, demo=True)
        hub.start()
        for bpm in (78, 92, 120, 151, 168, 172, 90):
            hub._on_bpm(bpm)
            app.processEvents()
        print(f"  链路测试（每次更新模式）：卡片可见={hub.flyout.isVisible()} 当前数值={hub.flyout._value!r}")
        hub.shutdown()
        hub.teardown()
        app.processEvents()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1
    print("逻辑测试通过 ✅")
    sys.stdout.flush()
    os._exit(0)  # 绕开 Qt 关停阶段的踩内存


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "visual"
    return logic() if mode == "logic" else visual()


if __name__ == "__main__":
    sys.exit(main())
