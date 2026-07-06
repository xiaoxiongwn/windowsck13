"""
开机自启动管理。

只在 Windows 上真正生效（通过写入注册表的 Run 键实现）。
在其他系统上这些函数直接返回 False / 不做任何事，
不会导致程序在非 Windows 环境下报错。
"""

import os
import sys
import platform

from utils.app_info import APP_NAME


def _is_windows():
    return platform.system() == "Windows"


def _get_launch_command():
    """
    返回应该写入注册表的启动命令。
    如果是 PyInstaller 打包后的 exe（sys.frozen 为 True），直接用 exe 路径；
    否则（用 python 直接跑 main.py 的开发模式）带上脚本路径。
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script}"'


def is_autostart_enabled():
    if not _is_windows():
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def enable_autostart():
    if not _is_windows():
        return False
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
    return True


def disable_autostart():
    if not _is_windows():
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    return True
