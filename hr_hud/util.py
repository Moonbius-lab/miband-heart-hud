# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""日志与杂项工具。"""

from __future__ import annotations

import datetime as _dt
import sys

from .config import LOG_DIR

_log_file = LOG_DIR / "app.log"


def setup_console() -> None:
    """控制台打印 ★ ✅ 这类字符时的自保。

    Windows 中文控制台默认是 GBK 代码页，GBK 里没有的字符（emoji、部分符号）
    会让 print 直接抛 UnicodeEncodeError，把脚本整个打断。这里只把编码错误
    降级成 '?'，中文该显示什么还是显示什么。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def log(message: str) -> None:
    line = f"{_dt.datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
    print(line, flush=True)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if _log_file.exists() and _log_file.stat().st_size > 1_000_000:
            _log_file.unlink()
        with _log_file.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
