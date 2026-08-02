"""PyTeXMK 应用路径相关工具。"""
import importlib.resources
import sys
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("auxiliary_fun")


def get_app_path():
    """获取 PyTeXMK 应用根路径（兼容 Nuitka 打包/frozen 运行）。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(importlib.resources.files("pytexmk"))
