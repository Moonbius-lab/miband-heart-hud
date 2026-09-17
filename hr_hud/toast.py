# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Moonbius-lab
"""Windows 11 原生通知（Toast Notification）。

非打包应用要发 Toast，需要先注册一个 AppUserModelID，否则通知会被系统静默丢弃。
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .util import log

AUMID = "MiBandHeartHUD.HeartRate"
DISPLAY_NAME = "小米手环心率"

_registered = False


def ensure_registered() -> bool:
    global _registered
    if _registered:
        return True
    import winreg

    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Classes\AppUserModelId\{AUMID}", 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, DISPLAY_NAME)
            winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 1)
        _registered = True
        return True
    except OSError as exc:
        log(f"注册通知应用 ID 失败：{exc}")
        return False


def show(title: str, body: str, silent: bool = True, tag: str = "heart") -> bool:
    ensure_registered()
    try:
        from winrt.windows.data.xml.dom import XmlDocument
        from winrt.windows.ui.notifications import ToastNotification, ToastNotificationManager
    except ImportError as exc:
        log(f"缺少 winrt 通知组件（pip install winrt-Windows.UI.Notifications）：{exc}")
        return False

    audio = '<audio silent="true"/>' if silent else ""
    xml = (
        "<toast>"
        '<visual><binding template="ToastGeneric">'
        f"<text>{escape(title)}</text>"
        f"<text>{escape(body)}</text>"
        "</binding></visual>"
        f"{audio}"
        "</toast>"
    )
    try:
        document = XmlDocument()
        document.load_xml(xml)
        toast = ToastNotification(document)
        toast.tag = tag
        toast.group = "miband-heart"
        ToastNotificationManager.create_toast_notifier_with_id(AUMID).show(toast)
        return True
    except Exception as exc:  # noqa: BLE001 - 通知失败不该影响主流程
        log(f"发送 Windows 通知失败：{exc!r}")
        return False


def recent_titles() -> list[str]:
    """读取通知中心历史（用于自检通知是否真的送达）。"""
    try:
        from winrt.windows.ui.notifications import ToastNotificationManager

        try:  # 必须按自己的 AppID 查，否则查的是"当前进程"的身份，永远是空的
            items = ToastNotificationManager.history.get_history_with_id(AUMID)
        except AttributeError:
            items = ToastNotificationManager.history.get_history()
        titles: list[str] = []
        for item in items:
            text = item.content.get_elements_by_tag_name("text")
            titles.append(text.item(0).inner_text if text.length else "<空>")
        return titles
    except Exception as exc:  # noqa: BLE001 - 没有历史时会报"找不到元素"，属于正常情况
        if "找不到元素" not in str(exc) and "Not Found" not in str(exc) and "0x80070490" not in str(exc):
            log(f"读取通知历史失败：{exc!r}")
        return []
