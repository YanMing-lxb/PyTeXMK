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
LastEditTime : 2024-03-03 19:41:02 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/compile_model.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
import subprocess
from info_print import print_message
from rich import console
console = console.Console(width=80)  # 设置宽度为80

# --------------------------------------------------------------------------------
# 定义编译 TeX 文件命令
# --------------------------------------------------------------------------------
def compile_tex(tex_name, file_name, tex_times, quiet):
    options = ["-shell-escape", "-file-line-error", "-halt-on-error", "--synctex=1"]
    print_message(f"{tex_times} 次 {tex_name} 编译")
    if tex_name == 'xelatex':
        options.insert(3, "-no-pdf")
    if quiet:
        options.insert(0, "-interaction=batchmode") # 静默编译
    else:
        options.insert(3, "-interaction=nonstopmode") # 非静默编译
    console.print(f"[bold]运行命令：[/bold][red][cyan]{' '.join(options)}[/cyan][/red]\n")
    subprocess.run([tex_name] + options + [f"{file_name}.tex"])

# --------------------------------------------------------------------------------
# 定义编译参考文献命令
# --------------------------------------------------------------------------------
def compile_bib(file_name, quiet):
    if os.path.exists(f"{file_name}.aux"):
        with open(f"{file_name}.aux", 'r', encoding='utf-8') as aux_file:
            aux_content = aux_file.read()

        if re.search(r'\\bibdata|\\abx@aux@cite', aux_content):
            if re.search(r'\\abx@aux@refcontext', aux_content):
                name_target = "biber"
                print_message(f'{name_target} 文献编译')
                options = [name_target, "-quiet" if quiet else "", file_name]
                console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                subprocess.run(options)
            elif re.search(r'\\bibdata', aux_content):
                name_target = 'bibtex'
                print_message(f'{name_target} 文献编译')
                options = [name_target, file_name]
                console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                subprocess.run(options)
            compile_tex_times = 2 # 参考文献需要额外编译的次数
            print_bib = f"{name_target} 编译参考文献"
        elif re.search(r'\\bibcite', aux_content):
            compile_tex_times = 1
            name_target = None
            print_bib = "thebibliography 环境实现排版 "
        else:
            compile_tex_times = 0
            name_target = None
            print_bib = "没有引用参考文献或编译工具不属于 bibtex 或 biber "
    else:
        compile_tex_times = 0
        name_target = None
        print_bib = "文档没有参考文献"
    return compile_tex_times, print_bib, name_target

# --------------------------------------------------------------------------------
# 定义编译目录索引命令
# --------------------------------------------------------------------------------
def compile_index(file_name):
    if any(os.path.exists(f"{file_name}{ext}") for ext in [".glo", ".nlo", ".idx", ".toc"]):
        if os.path.exists(f"{file_name}.glo"):
            with open(f"{file_name}.glo", "r", encoding='utf-8') as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                compile_tex_times = 1 # 目录和符号索引需要额外编译的次数
                name_target = "glossaries"
                print_message(f"{name_target} 宏包编译")
                print_index = "glossaries 宏包生成符号索引"
                print(print_index,"\n")
                options = ["makeindex", "-s", f"{file_name}.ist", "-o", f"{file_name}.gls", f"{file_name}.glo"]
                console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                subprocess.run(options)
            else:
                compile_tex_times = 0
                name_target = None
                print_index = "glossaries 宏包没有进行索引"

        elif os.path.exists(f"{file_name}.nlo"):
            with open(f"{file_name}.nlo", "r", encoding='utf-8') as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                compile_tex_times = 1
                name_target = "nomencl"
                print_message(f"{name_target} 宏包编译")
                print_index = "nomencl 宏包生成符号索引"
                print(print_index,"\n")
                options = ["makeindex", "-s", "nomencl.ist", "-o", f"{file_name}.nls", f"{file_name}.nlo"]
                console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                subprocess.run(options)
            else:
                compile_tex_times = 0
                name_target = None
                print_index = "nomencl 宏包没有进行索引"
        elif os.path.exists(f"{file_name}.idx"):
            with open(f"{file_name}.idx", "r", encoding='utf-8') as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                compile_tex_times = 1
                name_target = "makeidx"
                print_message(f"{name_target} 宏包编译")
                print_index = "makeidx 宏包生成索引"
                print(print_index,"\n")
                options = ["makeindex", f"{file_name}.idx"]
                console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
                subprocess.run(options)
            else:
                compile_tex_times = 0
                name_target = None
                print_index = "makeidx 宏包没有进行索引"  

        else:
            name_target = None
            if os.path.exists(f"{file_name}.toc"):
                compile_tex_times = 1 # 目录需要额外编译 1 次
                print_index = "含有图/表/章节目录"
            else:
                compile_tex_times = 0
                print_index = "没有图/表/章节目录"

    else: 
        compile_tex_times = 0
        name_target = None
        print_index = "没有插入任何目录或者使用 makeidx、glossaries、nomencl 等宏包"

    return compile_tex_times, print_index, name_target

# --------------------------------------------------------------------------------
# 定义编译 xdv 文件命令
# --------------------------------------------------------------------------------
def compile_xdv(file_name, quiet):
    print_message("xdvipdfmx PDF 编译")
    options = ["xdvipdfmx", "-q" if quiet else "", "-V", "1.6", f"{file_name}"]
    console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
    subprocess.run(options) # 将 xelatex 生成的 xdv 转换成 pdf