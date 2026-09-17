"""临时诊断：检查打包目录里 Qt 扩展模块的导入表，找出缺符号的依赖。"""

from __future__ import annotations

import os
import sys

import pefile

BASE = sys.argv[1]
SEARCH = [os.path.join(BASE, "PySide6"), os.path.join(BASE, "shiboken6"), BASE, r"C:\Windows\System32"]


def find(name: str) -> str | None:
    for directory in SEARCH:
        candidate = os.path.join(directory, name)
        if os.path.exists(candidate):
            return candidate
    return None


def imports(path: str) -> dict[str, list[str]]:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    )
    result: dict[str, list[str]] = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        names = []
        for item in entry.imports:
            names.append(item.name.decode() if item.name else f"#{item.ordinal}")
        result[entry.dll.decode()] = names
    return result


def exports(path: str) -> set[str]:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        return set()
    return {e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}


def check(path: str, depth: int = 0, seen: set[str] | None = None) -> None:
    seen = seen if seen is not None else set()
    if path in seen or depth > 2:
        return
    seen.add(path)
    print(f"{'  ' * depth}检查 {os.path.basename(path)}")
    for dll, names in imports(path).items():
        resolved = find(dll)
        if resolved is None:
            print(f"{'  ' * depth}  [缺少 DLL] {dll}")
            continue
        available = exports(resolved)
        if not available:
            continue
        missing = [n for n in names if not n.startswith("#") and n not in available]
        if missing:
            print(f"{'  ' * depth}  [缺符号] {dll}: {missing[:6]}  ← 解析到 {resolved}")
        if dll.lower().startswith(("qt6", "pyside6", "shiboken6")):
            check(resolved, depth + 1, seen)


check(sys.argv[2])
