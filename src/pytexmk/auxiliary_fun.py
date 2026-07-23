# -*- coding: utf-8 -*-
import sys
import signal
import warnings
import threading
from rich import print
from pathlib import Path

from pytexmk.language import set_language
from pytexmk.exceptions import PyTeXMKError

_ = set_language("auxiliary_fun")

_shutdown_requested = threading.Event()


def setup_console_encoding() -> None:
    """设置控制台 stdout/stderr 编码为 UTF-8（Windows GBK 编码兼容性）"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


setup_console_encoding()


def get_app_path() -> Path:
    """获取 PyTeXMK 应用程序路径"""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "pytexmk"
        return Path(sys.executable).parent / "pytexmk"
    import importlib.resources

    return Path(importlib.resources.files("pytexmk"))


def is_shutdown_requested() -> bool:
    """检查是否收到了关闭请求"""
    return _shutdown_requested.is_set()


def _signal_handler(signum, frame):
    """优雅的信号处理器，支持 Windows 兼容"""
    if not _shutdown_requested.is_set():
        _shutdown_requested.set()
        print(_("\n[bold yellow]收到中断信号，正在优雅退出...[/bold yellow]"))
        try:
            signal.default_int_handler(signum, frame)
        except (KeyboardInterrupt, SystemExit):
            raise PyTeXMKError(message=_("用户中断操作"), exit_code=130)


def setup_signal_handlers():
    """注册信号处理器，支持 Ctrl+C 优雅退出（Windows 兼容）"""
    if sys.platform == "win32":
        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, OSError):
            pass
    else:
        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
            signal.signal(signal.SIGHUP, _signal_handler)
        except (ValueError, OSError):
            pass


def exit_pytexmk(message: str = "", exit_code: int = 1):
    """
    退出 PyTeXMK 程序（已废弃，请使用异常机制替代）

    .. deprecated::
        请使用抛出 PyTeXMKError 或其子类异常替代直接调用此函数。

    参数:
        message: 退出时显示的消息
        exit_code: 退出码
    """
    warnings.warn("exit_pytexmk() 已废弃，请使用抛出 PyTeXMKError 异常替代", DeprecationWarning, stacklevel=2)
    if message:
        print(message)
    print(_("[bold red]正在退出 PyTeXMK..."))
    raise PyTeXMKError(message=message or _("程序正常退出"), exit_code=exit_code)
