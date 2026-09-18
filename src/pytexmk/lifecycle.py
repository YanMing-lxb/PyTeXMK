"""PyTeXMK 生命周期管理：统一退出流程。"""
import sys

from rich import print

from pytexmk.language import set_language

_ = set_language("lifecycle")

# 退出码约定
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PROJECT_NOT_FOUND = 3
EXIT_CONFIG_ERROR = 4
EXIT_COMPILE_FAILED = 5


def exit_pytexmk(exit_code: int = EXIT_OK):
    """打印退出提示并以指定退出码终止 PyTeXMK 进程。"""
    if exit_code != EXIT_OK:
        print(_("[bold red]正在退出 PyTeXMK..."))
    sys.exit(exit_code)
