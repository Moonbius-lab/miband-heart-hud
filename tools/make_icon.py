"""从 Fluent UI System Icons 的爱心 SVG 生成多尺寸 app.ico。

用法：python tools/make_icon.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hr_hud import icons  # noqa: E402
from hr_hud.zones import HEART_COLOR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "app.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(size: int, color: str) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(icons.svg_bytes(icons.HEART_FILLED, color)))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def write_ico(path: Path, images: list[QImage]) -> None:
    """ICO 容器：目录项 + 内嵌 PNG（Vista 以后都支持）。"""
    blobs = [png_bytes(image) for image in images]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    directory = b""
    for image, blob in zip(images, blobs):
        width = 0 if image.width() >= 256 else image.width()
        height = 0 if image.height() >= 256 else image.height()
        directory += struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(header + directory + b"".join(blobs))


def main() -> int:
    QApplication(["icon"])
    images = [render(size, HEART_COLOR) for size in SIZES]
    write_ico(OUT, images)
    print(f"已生成 {OUT}（{OUT.stat().st_size} 字节，尺寸 {SIZES}）")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
