import sys
from rich import print
from pathlib import Path

from pytexmk.language import set_language

_ = set_language('auxiliary_fun')
# --------------------------------------------------------------------------------
# 获取 PyTeXMK 路径
# --------------------------------------------------------------------------------
def get_app_path():
    # Nuitka 打包后的路径处理
    if getattr(sys, 'frozen', False):  # 判断程序是否被打包冻结
        # Nuitka 打包后资源路径
        app_path = Path(sys.executable).parent
    else:
        # 程序未被打包冻结
        import importlib.resources  # 用于访问打包资源
        app_path = Path(importlib.resources.files('pytexmk'))  # 使用 pathlib 获取包数据路径
    return app_path

# --------------------------------------------------------------------------------
# 定义 PyTeXMK 退出函数
# --------------------------------------------------------------------------------
def exit_pytexmk():
    print(_("[bold red]正在退出 PyTeXMK..."))
    sys.exit()  # 退出程序