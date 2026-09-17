# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""从 hr_hud/__init__.py 的 __version__ 生成 PyInstaller 的版本资源文件。

产物：packaging/out/version_info.txt（EXE 的"属性 → 详细信息"就来自这里）
这样版本号只有 hr_hud/__init__.py 一个来源，exe / MSIX / README 不会各说各话。

用法：python packaging/pyinstaller/make_version_info.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "packaging" / "out" / "version_info.txt"

COMPANY = "Moonbius Lab"
PRODUCT = "MiBandHeartHUD"
DESCRIPTION = "小米手环心率 · Windows 任务栏组件"
COPYRIGHT = "Copyright (C) 2026 Moonbius Lab · GPL-3.0-or-later"

TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={filevers},
    prodvers={filevers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{company}'),
        StringStruct('FileDescription', '{description}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{product}'),
        StringStruct('LegalCopyright', '{copyright}'),
        StringStruct('OriginalFilename', '{product}.exe'),
        StringStruct('ProductName', '{description}'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def read_version() -> str:
    text = (ROOT / "hr_hud" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("hr_hud/__init__.py 里找不到 __version__")
    return match.group(1)


def main() -> int:
    version = read_version()
    parts = [int(p) for p in re.findall(r"\d+", version)[:4]]
    while len(parts) < 4:
        parts.append(0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        TEMPLATE.format(
            filevers=tuple(parts),
            version=version,
            company=COMPANY,
            product=PRODUCT,
            description=DESCRIPTION,
            copyright=COPYRIGHT,
        ),
        encoding="utf-8",
    )
    print(f"已写入 {OUT}（version={version}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
