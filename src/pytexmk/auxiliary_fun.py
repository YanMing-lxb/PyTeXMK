import sys
from pathlib import Path

from rich import print

from pytexmk.language import set_language

_ = set_language("auxiliary_fun")


# --------------------------------------------------------------------------------
# 获取 PyTeXMK 路径
# --------------------------------------------------------------------------------
def get_app_path():
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
    print(_("[bold red]正在退出 PyTeXMK..."))
    sys.exit()  # 退出程序
