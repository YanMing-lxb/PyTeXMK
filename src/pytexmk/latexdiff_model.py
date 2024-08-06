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
LastEditTime : 2024-08-06 22:15:04 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/latexdiff_model.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
import sys
import logging
import subprocess
from pathlib import Path  # 导入Path模块
from rich import console  # 导入rich库的console模块
from .additional_operation_model import MoveRemoveClean
console = console.Console()



class LaTeXDiff_Aux:
    def __init__(self, suffixes_aux, auxdir):
        
        self.logger = logging.getLogger(__name__)  # 调用_setup_logger方法设置日志记录器
        self.suffixes_aux = suffixes_aux
        self.auxdir = auxdir

        self.MRC = MoveRemoveClean()  # 初始化 MoveRemoveClean 类对象
        
    # --------------------------------------------------------------------------------
    # 定义 指定的旧TeX辅助文件存在检查函数
    # --------------------------------------------------------------------------------
    def check_aux_files(self, file_name):
        """
        指定的旧TeX辅助文件存在检查。

        返回:
        - bool: 指定的旧TeX辅助文件是否存在。

        行为逻辑:        
        1. 遍历指定目录下的所有文件，判断是否存在指定的文件。
        """
        aux_files = [f"{file_name}{suffix}" for suffix in self.suffixes_aux]
        for file in aux_files:
            if os.path.exists(os.path.join(self.auxdir, file)):
                return True
        return False


    # --------------------------------------------------------------------------------
    # 定义 压平多文件的函数
    # --------------------------------------------------------------------------------
    # latexdiff 自带的 --flatten 参数可以用于压平多文件，但如果项目用 BibTeX 管理引用，则会在压平后报错。
    def flatten_Latex(self, file_name):
        """
        将 LaTeX 文件及其所有引用的子文件压平为一个单一文件。
         
        参数:
        file_name (str): 主 LaTeX 文件的名称（不带 .tex 扩展名）。
         
        返回:
        str: 压平后的文件名称。
         
        行为逻辑:
        1. 定义两个正则表达式来匹配 \input 和 \include 命令。
        2. 打开输出文件并将 sys.stdout 重定向到该文件。
        3. 递归地读取主 LaTeX 文件及其引用的所有子文件，并将内容写入输出文件。
        4. 恢复 sys.stdout 并返回压平后的文件名称。
        """
        def flattenLatex(tex_file_name):
            """
            递归地读取 LaTeX 文件及其引用的子文件，并将内容写入 sys.stdout。
             
            参数:
            tex_file_name (str): LaTeX 文件的名称。
             
            行为逻辑:
            1. 检查文件是否存在。
            2. 读取文件内容，匹配 \input 和 \include 命令。
            3. 对于匹配到的命令，递归调用自身处理引用的子文件。
            4. 将未匹配到的行写入 sys.stdout。
            """
            rootPath = Path(tex_file_name)
            if not rootPath.is_file():
                raise FileNotFoundError(f"File {tex_file_name} not found.")
            dirpath = rootPath.parent
            with open(tex_file_name, 'r', encoding='utf-8') as file_handler:
                for line in file_handler:
                    match_input = inputPattern.search(line)
                    match_include = includePattern.search(line)
                    if match_input:
                        newFile = match_input.group(1)
                        if not newFile.endswith('tex'):
                            newFile += '.tex'
                        flattenLatex(dirpath / newFile)
                    elif match_include:
                        newFile = match_include.group(1)
                        if not newFile.endswith('tex'):
                            newFile += '.tex'
                        flattenLatex(dirpath / newFile)
                    else:
                        sys.stdout.write(line)
 
        # 定义正则表达式 匹配命令前面没有%的 \input 和 \include 命令
        inputPattern = re.compile(r'^(?!.*%.*\\input)(?:.*\\input\{(.*?)\})', re.MULTILINE)
        includePattern = re.compile(r'^(?!.*%.*\\include)(?:.*\\include\{(.*?)\})', re.MULTILINE)
 
        # 打开输出文件并将 sys.stdout 重定向到该文件
        output_file_name = f'{file_name}-flatten.tex'
        try:
            with open(output_file_name, 'w', encoding='utf-8') as output_file:
                sys.stdout = output_file
                flattenLatex(f"{file_name}.tex")
            self.logger.info(f"已压平文件：{output_file_name}")
        except Exception as e:
            self.logger.error(f"压平出错：{e}")
        finally:
            # 恢复 sys.stdout
            sys.stdout = sys.__stdout__

        return output_file_name


    # --------------------------------------------------------------------------------
    # 定义 LaTeXDiff 编译函数
    # --------------------------------------------------------------------------------
    def compile_LaTeXDiff(self, old_tex_file, new_tex_file):
        options = ["latexdiff", old_tex_file, new_tex_file]
        command = f"{' '.join(options)} > LaTeXDiff.tex --encoding=utf8"
        console.print(f"[bold]运行命令：[/bold][cyan]{command}[/cyan]\n")
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=False, encoding='utf-8')

        if result.stderr:
            self.logger.error(f"LaTeXDiff 运行出错：{result.stderr}")
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit(1) # 退出程序