# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""日志与杂项工具。"""

from __future__ import annotations

import datetime as _dt

from .config import LOG_DIR

_log_file = LOG_DIR / "app.log"


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
