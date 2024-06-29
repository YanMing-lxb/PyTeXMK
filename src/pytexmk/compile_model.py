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
Date         : 2024-02-29 15:43:26 +0800
LastEditTime : 2024-06-29 14:06:47 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\compile_model.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
import subprocess
from .info_print import print_message
from rich import console
console = console.Console()  # 设置宽度为80

class CompileModel(object):
    def __init__(self, compiler_engine, project_name, quiet):
        self.compiler_engine = compiler_engine
        self.project_name = project_name
        self.quiet = quiet 
# --------------------------------------------------------------------------------
# 定义编译 TeX 文件命令
# --------------------------------------------------------------------------------
    def compile_tex(self, compiler_times):
        options = [self.compiler_engine, "-shell-escape", "-file-line-error", "-halt-on-error", "-synctex=1", f'{self.project_name}.tex']
        print_message(f"{compiler_times} 次 {self.compiler_engine} 编译")
        if self.compiler_engine == 'xelatex':
            options.insert(5, "-no-pdf")
        if self.quiet:
            options.insert(4, "-interaction=batchmode") # 静默编译
        else:
            options.insert(4, "-interaction=nonstopmode") # 非静默编译
        console.print(f"[bold]运行命令：[/bold][red][cyan]{' '.join(options)}[/cyan][/red]\n")
        
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
            return True
        except subprocess.CalledProcessError as e:
            print(e.output)
            return False
# --------------------------------------------------------------------------------
# 定义编译参考文献命令
# --------------------------------------------------------------------------------
    def compile_bib(self):
        if os.path.exists(f"{self.project_name}.aux"):
            with open(f"{self.project_name}.aux", 'r', encoding='utf-8') as aux_file:
                aux_content = aux_file.read()

            if re.search(r'\\bibdata|\\abx@aux@cite', aux_content):
                if re.search(r'\\abx@aux@refcontext', aux_content):
                    name_target = "biber 编译"
                    print_message('biber 文献编译')
                    options = ["biber", self.project_name]
                    if self.quiet:
                        options.insert(1, "-self.quiet") # 静默编译
                    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                elif re.search(r'\\bibdata', aux_content):
                    name_target = 'bibtex 编译'
                    print_message('bibtex 文献编译')
                    options = ['bibtex', self.project_name]
                    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                try:
                    subprocess.run(options, check=True, text=True, capture_output=False)
                    compile_compiler_times = 2 # 参考文献需要额外编译的次数
                    print_bib = f"{name_target}参考文献"
                except subprocess.CalledProcessError as e:
                    print(e.output)
                    return compile_compiler_times, print_bib, name_target, False
                
            elif re.search(r'\\bibcite', aux_content):
                compile_compiler_times = 1
                name_target = None
                print_bib = "thebibliography 环境实现排版 "
            else:
                compile_compiler_times = 0
                name_target = None
                print_bib = "没有引用参考文献或编译工具不属于 bibtex 或 biber "
        else:
            compile_compiler_times = 0
            name_target = None
            print_bib = "文档没有参考文献"
        return compile_compiler_times, print_bib, name_target, True

    # --------------------------------------------------------------------------------
    # 定义编译目录索引命令
    # --------------------------------------------------------------------------------
    def compile_makeindex(self):
        if any(os.path.exists(f"{self.project_name}{ext}") for ext in [".glo", ".nlo", ".idx", ".toc"]):
            if os.path.exists(f"{self.project_name}.glo"):
                with open(f"{self.project_name}.glo", "r", encoding='utf-8') as f:
                    content = f.read()
                if content.strip():  # Check if content is not empty
                    compile_compiler_times = 1 # 目录和符号索引需要额外编译的次数
                    name_target = "glossaries 宏包"
                    print_message("glossaries 宏包")
                    print_index = "glossaries 宏包生成符号索引"
                    print(print_index,"\n")
                    options = ["makeindex", "-s", f"{self.project_name}.ist", "-o", f"{self.project_name}.gls", f"{self.project_name}.glo"]
                    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                    try:
                        subprocess.run(options, check=True, text=True, capture_output=False)
                    except subprocess.CalledProcessError as e:
                        print(e.output)
                        return compile_compiler_times, print_index, name_target, False
                else:
                    compile_compiler_times = 0
                    name_target = None
                    print_index = "glossaries 宏包没有进行索引"

            elif os.path.exists(f"{self.project_name}.nlo"):
                with open(f"{self.project_name}.nlo", "r", encoding='utf-8') as f:
                    content = f.read()
                if content.strip():  # Check if content is not empty
                    compile_compiler_times = 1
                    name_target = "nomencl 宏包"
                    print_message("nomencl 宏包")
                    print_index = "nomencl 宏包生成符号索引"
                    print(print_index,"\n")
                    options = ["makeindex", "-s", "nomencl.ist", "-o", f"{self.project_name}.nls", f"{self.project_name}.nlo"]
                    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                    try:
                        subprocess.run(options, check=True, text=True, capture_output=False)
                    except subprocess.CalledProcessError as e:
                        print(e.output)
                        return compile_compiler_times, print_index, name_target, False
                else:
                    compile_compiler_times = 0
                    name_target = None
                    print_index = "nomencl 宏包没有进行索引"
            elif os.path.exists(f"{self.project_name}.idx"):
                with open(f"{self.project_name}.idx", "r", encoding='utf-8') as f:
                    content = f.read()
                if content.strip():  # Check if content is not empty
                    compile_compiler_times = 1
                    name_target = "makeidx 宏包"
                    print_message("makeidx 宏包")
                    print_index = "makeidx 宏包生成索引"
                    print(print_index,"\n")
                    options = ["makeindex", f"{self.project_name}.idx"]
                    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                    try:
                        subprocess.run(options, check=True, text=True, capture_output=False)
                    except subprocess.CalledProcessError as e:
                        print(e.output)
                        return compile_compiler_times, print_index, name_target, False
                else:
                    compile_compiler_times = 0
                    name_target = None
                    print_index = "makeidx 宏包没有进行索引"  

            else:
                name_target = None
                if os.path.exists(f"{self.project_name}.toc"):
                    compile_compiler_times = 1 # 目录需要额外编译 1 次
                    print_index = "含有图/表/章节目录"
                else:
                    compile_compiler_times = 0
                    print_index = "没有图/表/章节目录"

        else: 
            compile_compiler_times = 0
            name_target = None
            print_index = "没有插入任何目录或者使用 makeidx、glossaries、nomencl 等宏包"

        return compile_compiler_times, print_index, name_target, True

    # --------------------------------------------------------------------------------
    # 定义编译 xdv 文件命令
    # --------------------------------------------------------------------------------
    def compile_xdv(self):
        print_message("dvipdfmx 编译")
        options = ["dvipdfmx", "-V", "2.0", f"{self.project_name}"]
        if self.quiet:
            options.insert(1, "-q") # 静默编译
        console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
            return True
        except subprocess.CalledProcessError as e:
            print(e.output)
            return False