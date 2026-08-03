"""PyTeXMK 生命周期管理：统一退出流程。"""
import sys

from rich import print

from pytexmk.language import set_language

_ = set_language("lifecycle")


def exit_pytexmk():
    """打印退出提示并以 sys.exit 终止 PyTeXMK 进程。"""
    print(_("[bold red]正在退出 PyTeXMK..."))
    sys.exit()
