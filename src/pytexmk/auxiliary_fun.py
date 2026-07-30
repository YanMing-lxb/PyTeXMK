"""辅助工具函数：PyTeXMK 应用路径获取、统一退出流程等小工具。"""
import sys
from pathlib import Path

from rich import print

from pytexmk.language import set_language

_ = set_language("auxiliary_fun")


# --------------------------------------------------------------------------------
# 获取 PyTeXMK 路径
# --------------------------------------------------------------------------------
def get_app_path():
    """获取 PyTeXMK 应用根路径（兼容 Nuitka 打包/frozen 运行）。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    import importlib.resources
    return Path(importlib.resources.files("pytexmk"))


# --------------------------------------------------------------------------------
# 定义 PyTeXMK 退出函数
# --------------------------------------------------------------------------------
def exit_pytexmk():
    """打印退出提示并以 sys.exit 终止 PyTeXMK 进程。"""
    print(_("[bold red]正在退出 PyTeXMK..."))
    sys.exit()  # 退出程序
