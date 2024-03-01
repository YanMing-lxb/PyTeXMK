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
LastEditTime : 2024-03-01 15:40:41 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\compile_model.py
Description  : 
 -----------------------------------------------------------------------
'''

import os
import re
import subprocess


# --------------------------------------------------------------------------------
# 定义编译 TeX 文件命令
# --------------------------------------------------------------------------------
def compile_tex(tex_name, file_name, tex_times, quiet):
    print("\n\n" + "=" * 80 + "\n" +
          "X" * 28 + f" 开始 {tex_times} 次 {tex_name} 编译 " + "X" * 28 + "\n" +
          "=" * 80 + "\n\n")
    options = ["-shell-escape", "-file-line-error", "-halt-on-error", "--synctex=1"]

    if tex_name == 'xelatex':
        options.insert(3, "-no-pdf")

    if quiet:
        options.insert(0, "-interaction=batchmode") # 静默编译
    else:
        options.insert(3, "-interaction=nonstopmode") # 非静默编译

    subprocess.run([tex_name] + options + [f"{file_name}.tex"])

# --------------------------------------------------------------------------------
# 定义编译参考文献命令
# --------------------------------------------------------------------------------
def compile_bib(file_name, quiet):
    try:
        with open(f"{file_name}.aux", 'r', encoding='utf-8') as aux_file:
            aux_content = aux_file.read()

        if re.search(r'\\citation|\\abx@aux@cite', aux_content):
            print("\n\n" + "=" * 80 + "\n" +
                "X" * 33 + " 参考文献编译 " + "X" * 33 + "\n" +
                "=" * 80 + "\n\n")
            compile_tex_times = 2 # 参考文献需要额外编译的次数
            if re.search(r'\\abx@aux@refcontext', aux_content):
                options = ['biber', "-quiet" if quiet else "", file_name]
                subprocess.run(options)
                name_target = "biber"
                print_bib = "biber 编译参考文献"
            elif re.search(r'\\bibdata', aux_content):
                options = ['bibtex', file_name]
                subprocess.run(options)
                name_target = "bibtex"
                print_bib = "bibtex 编译参考文献"
        else:
            bib_compile_tex_times = 0
            name_target = None
            print_bib = "没有参考文献或编译工具不属于 bibtex 或 biber "
    except FileNotFoundError:
        compile_tex_times = 0
        name_target = None
        print("找不到辅助文件，存在错误，请用 -nq 模式运行查看报错！")
        
    return compile_tex_times, print_bib, name_target

# --------------------------------------------------------------------------------
# 定义编译目录索引命令
# --------------------------------------------------------------------------------
def compile_index(file_name):
    if any(os.path.exists(f"{file_name}{ext}") for ext in [".glo", ".nlo", ".toc"]):
        print("\n\n" + "=" * 80+"\n"+
            "X" * 33 + " 符号索引编译 " + "X" * 33 + "\n" + 
            "=" * 80 + "\n\n")
        if os.path.exists(f"{file_name}.glo"):
            with open(f"{file_name}.glo", "r", encoding='utf-8') as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                subprocess.run(["makeindex", "-s", f"{file_name}.ist", "-o", f"{file_name}.gls", f"{file_name}.glo"])
                compile_tex_times = 1 # 目录和符号索引需要额外编译的次数
                name_target = "glossaries"
                print_catalogs = "glossaries 宏包生成符号索引"
            else:
                compile_tex_times = 0
                name_target = None
                print_catalogs = "glossaries 宏包没有进行索引"

        elif os.path.exists(f"{file_name}.nlo"):
            with open(f"{file_name}.nlo", "r", encoding='utf-8') as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                subprocess.run(["makeindex", "-s", "nomencl.ist", "-o", f"{file_name}.nls", f"{file_name}.nlo"])
                compile_tex_times = 1
                name_target = "nomencl"
                print_catalogs = "nomencl 宏包生成符号索引"
            else:
                compile_tex_times = 0
                name_target = None
                print_catalogs = "nomencl 宏包没有进行索引"      
        else:
            if os.path.exists(f"{file_name}.toc"):
                compile_tex_times = 1 # 目录需要额外编译 1 次
                name_target = "makeindex"
                print_catalogs = "含有图\表\章节目录"
            else:
                compile_tex_times = 0
                name_target = None
                print_catalogs = "没有插入任何目录"

        print(print_catalogs)
    else: 
        compile_tex_times = 0
        name_target = None
        print_catalogs = "没有插入任何目录"

    return compile_tex_times, print_catalogs, name_target

# --------------------------------------------------------------------------------
# 定义编译 xdv 文件命令
# --------------------------------------------------------------------------------
def compile_xdv(file_name):
    print("\n\n" + "=" * 80 + "\n" +
        "X" * 32 + " xdvipdfmx 编译 " + "X" * 32 + "\n" +
        "=" * 80 + "\n\n")
    subprocess.run(["xdvipdfmx", "-V", "1.6", f"{file_name}"]) # 将 xelatex 生成的 xdv 转换成 pdf