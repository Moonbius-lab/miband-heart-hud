# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""M0 链路验证：扫描手环 → 连上 → 在控制台打印心率。

用法：
    python probe.py                 # 自动挑一块最像手环的设备
    python probe.py --list          # 只扫描，不动连接
    python probe.py --address AA:BB:CC:DD:EE:FF --seconds 60
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from hr_hud.ble import HeartRateReader, scan
from hr_hud.util import setup_console


def _bar(bpm: int) -> str:
    filled = max(0, min(40, (bpm - 40) // 4))
    return "█" * filled + "·" * (40 - filled)


async def list_devices(timeout: float) -> list:
    print(f"扫描 BLE 设备中（{timeout:.0f} 秒）…\n")
    devices = await scan(timeout=timeout)
    if not devices:
        print("没有扫到任何 BLE 设备。先确认电脑蓝牙是开着的。")
        return []
    print(f"共 {len(devices)} 台设备（★ 表示广播里带标准心率服务）：\n")
    for device in devices:
        star = "★" if device.has_hrs else " "
        print(f" {star} {device.label()}")
    print()
    return devices


async def main() -> int:
    setup_console()
    parser = argparse.ArgumentParser(description="小米手环心率链路验证")
    parser.add_argument("--address", default="", help="指定设备地址，默认自动挑选")
    parser.add_argument("--seconds", type=float, default=45.0, help="连接后观察多少秒")
    parser.add_argument("--scan-timeout", type=float, default=8.0)
    parser.add_argument("--list", action="store_true", help="只扫描不连接")
    args = parser.parse_args()

    devices = await list_devices(args.scan_timeout)
    if args.list or not devices:
        return 0 if devices else 2

    if args.address:
        target = args.address
    else:
        from hr_hud.ble import pick_device

        picked = pick_device(devices)
        if picked is None:
            print("没有可用设备。")
            return 2
        target = picked.address
        print(f"目标设备：{picked.name or '(无名)'}  {picked.address}\n")
        print("提示：如果一直连不上，先在 Windows 设置 → 蓝牙 里配对这块手环再试。\n")

    samples: list[int] = []
    status = {"text": "启动中…"}

    def on_bpm(bpm: int) -> None:
        samples.append(bpm)
        print(f"\r  {bpm:>3} BPM  {_bar(bpm)}", end="", flush=True)

    def on_status(ok: bool, text: str) -> None:
        status["text"] = text
        print(f"\n[{ 'OK ' if ok else '!! ' }] {text}", flush=True)

    reader = HeartRateReader(address=target, on_bpm=on_bpm, on_status=on_status)
    reader.start()
    try:
        await asyncio.sleep(args.seconds)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        reader.stop()
        await asyncio.sleep(0.5)

    print()
    if samples:
        print(
            f"\n收到 {len(samples)} 个采样："
            f"最低 {min(samples)} / 最高 {max(samples)} / "
            f"平均 {sum(samples) / len(samples):.0f} BPM  —— 链路 OK ✅"
        )
        return 0
    print(f"\n没有收到任何心率数据。最后状态：{status['text']} ❌")
    print("排查顺序：1) 手环已开「心率广播」 2) 手环戴在手上 3) 距离电脑近一点 4) 必要时在系统里配对")
    return 3


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
