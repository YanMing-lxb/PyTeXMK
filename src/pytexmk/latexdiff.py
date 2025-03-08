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
LastEditTime : 2025-02-07 13:44:10 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/latexdiff_module.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import re
import sys
import logging
import subprocess
from pathlib import Path
from rich import console

from pytexmk.language import set_language
from pytexmk.additional import MoveRemoveOperation, exit_pytexmk

_ = set_language('latexdiff')

console = console.Console()



class LaTeXDiff_Aux:
    def __init__(self, suffixes_aux, auxdir):
        
        self.logger = logging.getLogger(__name__)  # 调用_setup_logger方法设置日志记录器
        self.suffixes_aux = suffixes_aux
        self.auxdir = Path(auxdir)

        self.MRO = MoveRemoveOperation()  # 初始化 MoveRemoveOperation 类对象


    # --------------------------------------------------------------------------------
    # 定义 指定的旧TeX辅助文件存在检查函数
    # --------------------------------------------------------------------------------
    def check_aux_files(self, file_name):
        """
        指定的旧TeX辅助文件存在检查.

        返回:
        - bool: 指定的旧TeX辅助文件是否存在.

        行为逻辑:        
        1. 遍历指定目录下的所有文件,判断是否存在指定的文件.
        """
        aux_files = [f"{file_name}{suffix}" for suffix in self.suffixes_aux]
        for file in aux_files:
            if (self.auxdir / file).exists():
                return True
        return False


    # --------------------------------------------------------------------------------
    # 定义 压平多文件的函数
    # --------------------------------------------------------------------------------
    # latexdiff 自带的 --flatten 参数可以用于压平多文件,但如果项目用 BibTeX 管理引用,则会在压平后报错.
    def flatten_Latex(self, file_name):
        """
        将 LaTeX 文件及其所有引用的子文件压平为一个单一文件.
         
        参数:
        file_name (str): 主 LaTeX 文件的名称(不带 .tex 扩展名).
         
        返回:
        str: 压平后的文件名称.
         
        行为逻辑:
        1. 定义两个正则表达式来匹配 \input 和 \include 命令.
        2. 打开输出文件并将 sys.stdout 重定向到该文件.
        3. 递归地读取主 LaTeX 文件及其引用的所有子文件,并将内容写入输出文件.
        4. 恢复 sys.stdout 并返回压平后的文件名称.
        """
        def flattenLatex(tex_file_name): # TODO 递归读取 flatten 文件功能有问题,未考虑用户自定义命令中存在 \input 和 \include 命令的情况
            """
            递归地读取 LaTeX 文件及其引用的子文件,并将内容写入 sys.stdout.
             
            参数:
            tex_file_name (str): LaTeX 文件的名称.
             
            行为逻辑:
            1. 检查文件是否存在.
            2. 读取文件内容,匹配 \input 和 \include 命令.
            3. 对于匹配到的命令,递归调用自身处理引用的子文件.
            4. 将未匹配到的行写入 sys.stdout.
            """
            rootPath = Path(tex_file_name)
            if not rootPath.is_file():
                self.logger.error(_('文件不存在: ') + tex_file_name)
                exit_pytexmk()
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
        output_file_name = f'{file_name}-flatten'
        try:
            with open(output_file_name+'.tex', 'w', encoding='utf-8') as output_file:
                sys.stdout = output_file
                flattenLatex(f"{file_name}.tex")
            sys.stdout = sys.__stdout__
            self.logger.info(_("已压平文件: ") + output_file_name + '.tex')
        except Exception as e:
            self.logger.error(_("压平出错: ") + str(e))
            exit_pytexmk()

        return output_file_name
    
    # --------------------------------------------------------------------------------
    # 判断在指定后缀的新旧辅助文件是否同时存在
    # --------------------------------------------------------------------------------
    def aux_files_both_exist(self, old_file, new_file, suffix):
        """
        删除匹配正则表达式的文件.

        参数:
        - old_file: 旧文件名,无后缀.
        - new_file: 新文件名,无后缀.
        - suffix: 后缀名,如'.bbl'.

        行为:
        - 检查新旧辅助文件是否同时存在.
        - 如果存在,则返回True,否则返回False.
        """
        old_file_path = Path(old_file + suffix)  # 转换为Path对象
        new_file_path = Path(new_file + suffix)  # 转换为Path对象
        if old_file_path.exists() and new_file_path.exists():
            self.logger.info(_("新旧辅助文件同时存在: ") + str(old_file_path) + " " + str(new_file_path))
            return suffix


    # --------------------------------------------------------------------------------
    # 定义 LaTeXDiff 编译函数
    # --------------------------------------------------------------------------------
    def compile_LaTeXDiff(self, old_tex_file, new_tex_file, diff_tex_file, suffix):
        options = ["latexdiff", old_tex_file + suffix, new_tex_file + suffix]
        command = f"{' '.join(options)} > {diff_tex_file}{suffix} --encoding=utf8"
        console.print(_("[bold]运行命令: ") + f"[/bold][cyan]{command}\n")
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=False, encoding='utf-8')

        if result.stderr:
            self.logger.error(_("LaTeXDiff 运行出错: ") + str(result.stderr))
            exit_pytexmk()