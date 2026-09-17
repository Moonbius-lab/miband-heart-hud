# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""读取 BLE 心率广播（标准心率服务 0x180D / 特征 0x2A37）。

手环侧必须先在 设置 → 心率广播 里打开广播，否则这里什么都扫不到。
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .util import log

HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"

XIAOMI_HINTS = ("mi band", "miband", "xiaomi", "smart band", "redmi", "小米")


def parse_hr_measurement(data: bytes) -> Optional[int]:
    """解析 Heart Rate Measurement 特征值。bit0=1 表示 16 位心率。"""
    if not data:
        return None
    flags = data[0]
    if flags & 0x01:
        return int.from_bytes(data[1:3], "little") if len(data) >= 3 else None
    return data[1] if len(data) >= 2 else None


@dataclass
class DeviceInfo:
    address: str
    name: str
    rssi: int
    has_hrs: bool = False

    @property
    def likely_xiaomi(self) -> bool:
        low = self.name.lower()
        return any(hint in low for hint in XIAOMI_HINTS)

    def label(self) -> str:
        marks = []
        if self.has_hrs:
            marks.append("心率服务")
        if self.likely_xiaomi:
            marks.append("小米系")
        suffix = f"  [{'/'.join(marks)}]" if marks else ""
        return f"{(self.name or '(无名)'):<28} {self.address}  {self.rssi:>4} dBm{suffix}"


async def scan(timeout: float = 8.0) -> list[DeviceInfo]:
    """扫描 BLE 设备。不只看广播里带 0x180D 的——小米手环不一定把它放进广播包。"""
    from bleak import BleakScanner

    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    devices: list[DeviceInfo] = []
    for device, adv in found.values():
        uuids = {str(u).lower() for u in (adv.service_uuids or [])}
        devices.append(
            DeviceInfo(
                address=device.address,
                name=adv.local_name or device.name or "",
                rssi=adv.rssi,
                has_hrs=HR_SERVICE in uuids,
            )
        )
    devices.sort(key=lambda d: (not d.has_hrs, not d.likely_xiaomi, -d.rssi))
    return devices


def pick_device(devices: list[DeviceInfo]) -> Optional[DeviceInfo]:
    """优先选：广播带心率服务的小米设备 → 带心率服务的 → 小米系的。

    一个都不符合就返回 None——绝不随便连一台没有名字、也不广播心率服务的设备。
    """
    for predicate in (
        lambda d: d.has_hrs and d.likely_xiaomi,
        lambda d: d.has_hrs,
        lambda d: d.likely_xiaomi,
    ):
        for device in devices:
            if predicate(device):
                return device
    return None


class HeartRateReader:
    """后台线程里跑 asyncio，持续读心率；断线自动重连。

    on_bpm(bpm)          每次收到心率
    on_status(ok, text)  连接状态变化
    """

    STALE_SECONDS = 15.0

    def __init__(
        self,
        address: str = "",
        name_hint: str = "",
        on_bpm: Optional[Callable[[int], None]] = None,
        on_status: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        self.address = address
        self.name_hint = name_hint
        self._on_bpm = on_bpm or (lambda bpm: None)
        self._on_status = on_status or (lambda ok, text: None)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_data = 0.0
        self._last_missing_log = 0.0
        self.connected = False
        # Windows 报的设备名有时是乱码，优先用广播包里读到的名字
        self.display_name = name_hint

    # ------------------------------------------------------------- 生命周期
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="ble-reader", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout)

    def _status(self, ok: bool, text: str) -> None:
        self.connected = ok
        try:
            self._on_status(ok, text)
        except Exception:  # noqa: BLE001 - 回调不能拖垮读取线程
            log("状态回调异常")

    # ---------------------------------------------------------------- 线程体
    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:  # noqa: BLE001
            log(f"BLE 线程退出：{exc!r}")

    async def _run(self) -> None:
        from bleak import BleakClient

        backoff = 2.0
        while not self._stop.is_set():
            device = await self._resolve_device()
            if device is None:
                self._status(False, "未找到设备")
                if await self._sleep(backoff):
                    return
                backoff = min(backoff * 1.6, 30.0)
                continue

            try:
                label = self.display_name or device.name or device.address
                log(f"正在连接 {label} ({device.address})")
                async with BleakClient(device, timeout=25.0) as client:
                    backoff = 2.0
                    self._status(True, f"已连接 {label}")
                    self._last_data = time.monotonic()
                    await client.start_notify(HR_MEASUREMENT, self._handle)
                    while not self._stop.is_set():
                        if await self._sleep(1.0):
                            break
                        if not client.is_connected:
                            self._status(False, "连接断开")
                            break
                        if time.monotonic() - self._last_data > self.STALE_SECONDS:
                            self._status(False, "数据超时")
                            break
                    if client.is_connected:
                        try:
                            await client.stop_notify(HR_MEASUREMENT)
                        except Exception:  # noqa: BLE001
                            pass
            except Exception as exc:  # noqa: BLE001
                self._status(False, f"连接失败：{exc}")
                self._explain(exc)
                if await self._sleep(backoff):
                    return
                backoff = min(backoff * 1.6, 30.0)
            else:
                if self._stop.is_set():
                    return
                if await self._sleep(2.0):
                    return

    async def _sleep(self, seconds: float) -> bool:
        """可被打断的休眠，返回 True 表示应当退出。"""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._stop.is_set():
                return True
            await asyncio.sleep(0.1)
        return False

    async def _resolve_device(self):
        """返回要连接的 BLEDevice；已记住地址时优先按地址找。"""
        devices = await scan(timeout=6.0)
        if not devices:
            return None
        if self.address:
            for device in devices:
                if device.address.lower() == self.address.lower():
                    if device.name:
                        self.display_name = device.name
                    return await self._to_ble_device(device.address, devices)
            # 记住过设备就只认它，没扫到就等它——不连别的设备
            if time.monotonic() - self._last_missing_log > 60.0:
                self._last_missing_log = time.monotonic()
                log(f"没扫到已记住的设备 {self.address}，继续等它广播（不会连其他设备）")
            return None
        chosen = pick_device(devices)
        if chosen is None:
            log("附近没有看起来像心率广播的设备（没有 0x180D、也不是小米系）")
            return None
        if chosen and chosen.name:
            self.display_name = chosen.name
        return await self._to_ble_device(chosen.address, devices) if chosen else None

    async def _to_ble_device(self, address: str, devices: list[DeviceInfo]):
        from bleak import BleakScanner

        device = await BleakScanner.find_device_by_address(address, timeout=6.0)
        if device is None:
            # 有些设备（尤其刚配对过的）只能通过再次扫描拿到句柄
            for info in devices:
                if info.address.lower() == address.lower():
                    log(f"未能通过地址获取设备句柄：{info.label()}")
                    break
        if device:
            self.address = device.address
        return device

    def _handle(self, _sender, data: bytearray) -> None:
        bpm = parse_hr_measurement(bytes(data))
        if bpm is None:
            return
        self._last_data = time.monotonic()
        try:
            self._on_bpm(bpm)
        except Exception:  # noqa: BLE001
            log("心率回调异常")

    @staticmethod
    def _explain(exc: Exception) -> None:
        text = str(exc).lower()
        if "0x0e" in text or "authentication" in text or "insufficient" in text:
            log("提示：设备要求加密/配对。请在 Windows 设置 → 蓝牙里先配对这块手环，再重试。")
        elif "not found" in text or "unreachable" in text:
            log("提示：设备不可达。确认手环已开启「心率广播」且没有走远。")
        elif "access is denied" in text or "unauthorized" in text:
            log("提示：被系统拒绝访问蓝牙。检查 Windows 蓝牙是否打开、权限是否被策略限制。")
