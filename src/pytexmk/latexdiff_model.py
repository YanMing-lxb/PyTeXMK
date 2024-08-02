'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-08-02 10:44:16 +0800
LastEditTime : 2024-08-02 13:42:31 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/latexdiff_model.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import sys
import logging
import subprocess
from rich import print  # 导入rich库的print函数
from pathlib import Path  # 导入Path模块
from rich import console  # 导入rich库的console模块
from .additional_operation import MoveRemoveClean
console = console.Console()

class LaTeXDiff_Aux:
    def __init__(self, new_tex_file, old_tex_file, diff_file):
        
        self.logger = logging.getLogger(__name__)  # 调用_setup_logger方法设置日志记录器

        self.new_tex_file = new_tex_file
        self.old_tex_file = old_tex_file
        self.diff_file = diff_file

        self.MRC = MoveRemoveClean()  # 初始化 MoveRemoveClean 类对象
    

    # --------------------------------------------------------------------------------
    # 定义 指定的旧TeX文件存在检查函数
    # --------------------------------------------------------------------------------
    def _old_tex_files_exist(self): # TODO 检查旧的tex文件的辅助文件是否存在，如果存在返回True，否则返回False
        """
        检查旧的tex文件是否存在。

        返回:
        - bool: 旧tex文件是否存在。

        行为逻辑:
        1. 遍历旧tex文件列表，如果存在则返回True，否则返回False。
        """
        for file_name in self.old_tex_files:
            if Path(file_name).exists():
                return True
        return False

    # --------------------------------------------------------------------------------
    # 定义 LaTeXDiff 编译函数
    # --------------------------------------------------------------------------------
    def compile_LaTeXDiff(self, flatten_blooen):
        options = ["LaTeXDiff", f"{self.old_file}.tex", f"{self.new_file}.tex", ">", f"{self.project_name}-diff.tex"]
        if not flatten_blooen:
            options.append("--flatten") # 包含 \include 和 \input 命令指定的文件，将文件展开
        console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
        except:
            self.logger.error(f"LaTeXDiff 编译失败，请查看日志文件 {self.auxdir}{self.project_name}.log 以获取详细信息。")
            self.MRC.move_to_folder(self.aux_files, self.auxdir)
            self.MRC.move_to_folder(self.out_files, self.outdir)
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit(1) # 退出程序