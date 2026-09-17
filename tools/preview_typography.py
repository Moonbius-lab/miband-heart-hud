# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""字号对比表：把"心率"与数字的几种字号组合画在一起，挑一个。

用法：python tools/preview_typography.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hr_hud import widget_render  # noqa: E402
from hr_hud.widget_render import pick_family  # noqa: E402
from hr_hud.zones import HEART_COLOR  # noqa: E402

OUT = Path(__file__).resolve().parent
TASKBAR = "#E8E4E0"   # 模拟任务栏底色
CARD_HEIGHT = 40
SCALE = 3

# (心率字号, 数字字号, 备注)
COMBOS = [
    (12, 16, "← 当前"),
    (11, 16, ""),
    (12, 15, ""),
    (13, 16, ""),
    (13, 15, ""),
    (14, 16, ""),
    (12, 14, ""),
    (14, 14, ""),
]


def main() -> int:
    app = QApplication(["preview"])
    family = pick_family()
    print(f"字体：{family}")

    rows = []
    for label_pt, value_pt, note in COMBOS:
        width = widget_render.reading_width(family, label_pt, value_pt)
        card = widget_render.render_card(
            width,
            CARD_HEIGHT,
            78,
            "normal",
            True,
            HEART_COLOR,
            family,
            "auto",
            TASKBAR,
            1.0,
            label_pt,
            value_pt,
        )
        rows.append((width, card, label_pt, value_pt, note))

    row_height = CARD_HEIGHT + 26
    sheet_width = max(row[0] for row in rows) + 260
    sheet_height = row_height * len(rows) + 30
    sheet = QImage(sheet_width, sheet_height, QImage.Format_ARGB32_Premultiplied)
    sheet.fill(QColor(TASKBAR))

    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.Antialiasing)
    caption_font = QFont(family, 11, QFont.Medium)
    for index, (width, card, label_pt, value_pt, note) in enumerate(rows):
        y = 15 + index * row_height
        painter.drawImage(QPointF(20, y), card)
        painter.setPen(QColor("#333333"))
        painter.setFont(caption_font)
        painter.drawText(
            QPointF(width + 50, y + CARD_HEIGHT / 2 + 6), f"心率 {label_pt}pt / 数字 {value_pt}pt  {note}"
        )
    painter.end()

    sheet.scaled(
        sheet_width * SCALE, sheet_height * SCALE, Qt.KeepAspectRatio, Qt.SmoothTransformation
    ).save(str(OUT / "_preview_typography.png"))
    print("已保存 tools/_preview_typography.png")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
