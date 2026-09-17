# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""配置读写：%LOCALAPPDATA%\\MiBandHeartHUD\\config.json"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_NAME = "MiBandHeartHUD"
APP_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_NAME
# 允许用环境变量换一份配置（多套配置 / 测试用）
CONFIG_PATH = Path(os.environ.get("HRHUD_CONFIG") or (APP_DIR / "config.json"))
LOG_DIR = APP_DIR / "logs"


@dataclass
class Config:
    # ---- 设备 ----
    device_address: str = ""
    device_name: str = ""

    # ---- 异常判定 ----
    high_bpm: int = 150          # 高于此值算心率过高
    low_bpm: int = 45            # 低于此值算心率偏低
    confirm_seconds: float = 10.0   # 需要持续这么久才判定为异常
    rearm_seconds: float = 30.0     # 恢复后多久才允许对同一异常再次提醒
    escalate_step: int = 15         # 异常加剧多少 BPM 再提醒一次
    escalate_interval: float = 60.0  # 两次"加剧"提醒的最小间隔

    # ---- 提醒内容 ----
    notify_mode: str = "alert"      # alert=仅在异常时提醒 | every=每次心率更新都提醒
    reading_interval_seconds: int = 60   # periodic 模式下每隔多少秒显示一次当前心率
    # 任务栏看得见时不弹例行读数弹窗（组件上已经显示着了，没必要重复）
    popup_only_when_taskbar_hidden: bool = True
    notify_high: bool = True
    notify_low: bool = True
    notify_recover: bool = True
    notify_toast: bool = True       # Windows 11 通知中心
    notify_flyout: bool = True      # FluentFlyout 风格弹窗
    notify_every_toast: bool = False  # "每次更新"模式下是否也发 Windows 通知（默认关，否则每秒一条会刷屏）
    toast_silent: bool = True       # 提醒静音，别打断游戏
    flyout_seconds: float = 5.0     # 弹窗停留秒数
    animation_ms: int = 300         # 弹窗动画时长（FluentFlyout 的 1x 速度就是 300ms）
    heart_color: str = "#E81123"    # 爱心颜色（统一，不随心率变化）
    font_family: str = ""           # 留空 = 自动（优先 Microsoft YaHei UI，中英文数字同一字族）

    # ---- 不健康时段的休息提醒 ----
    rest_reminder: bool = True
    rest_start: str = "23:00"
    rest_end: str = "07:00"
    rest_interval_minutes: int = 60
    # 启动后留给蓝牙连接的时间：这段时间内没连上也不算"没开心率广播"，避免刚开程序就误报
    rest_startup_grace_seconds: int = 90

    # ---- 任务栏组件 ----
    widget_enabled: bool = True
    widget_background: str = "auto"  # auto(取任务栏底色,默认,融进任务栏) | card(自带卡片) | clear(纯透明)
    widget_side: str = "left"        # left(和 FluentFlyout 组件并排) | right(贴着系统托盘)
    widget_gap: int = 8              # 与系统托盘的间距
    widget_extra_gap: float = 0.0    # 与 FluentFlyout 组件之间的额外留白
    widget_hide_without_data: bool = False  # 无数据时隐藏组件

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        if not isinstance(raw, dict):
            return cfg
        known = {f.name for f in fields(cls)}
        for key, value in raw.items():
            if key in known and value is not None:
                setattr(cfg, key, value)
        return cfg

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )
