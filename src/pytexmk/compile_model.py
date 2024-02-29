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
LastEditTime : 2024-02-29 18:05:12 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/compile_model.py
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
        options.insert(0, "-interaction=batchmode")
    else:
        options.insert(3, "-interaction=nonstopmode")

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
            bib_compile_tex_times = 2 # 参考文献需要额外编译的次数
            if re.search(r'\\abx@aux@refcontext', aux_content):
                options = ['biber', "-quiet" if quiet else "", file_name]
                subprocess.run(options)
                bib_print = "biber 编译参考文献"
            elif re.search(r'\\bibdata', aux_content):
                options = ['bibtex', file_name]
                subprocess.run(options)
                bib_print = "bibtex 编译参考文献"
        else:
            bib_compile_tex_times = 0
            bib_print = "没有参考文献或编译工具不属于 bibtex 或 biber "
    except FileNotFoundError:
        bib_compile_tex_times = 0
        bib_print("找不到辅助文件，存在错误，请用 -nq 模式运行查看报错！")
        
    return bib_compile_tex_times, bib_print

# --------------------------------------------------------------------------------
# 定义编译目录索引命令
# --------------------------------------------------------------------------------
def compile_index(file_name):
    if any(os.path.exists(f"{file_name}{ext}") for ext in [".glo", ".nlo", ".toc"]):
        print("\n\n" + "=" * 80+"\n"+
            "X" * 33 + " 符号索引编译 " + "X" * 33 + "\n" + 
            "=" * 80 + "\n\n")
        if os.path.exists(f"{file_name}.glo"):
            with open(f"{file_name}.glo", "r") as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                subprocess.run(["makeindex", "-s", f"{file_name}.ist", "-o", f"{file_name}.gls", f"{file_name}.glo"])
                index_compile_tex_times = 1 # 目录和符号索引需要额外编译的次数
                catalogs_print = "glossaries 宏包生成符号索引"
            else:
                index_compile_tex_times = 0
                catalogs_print = "glossaries 宏包没有进行索引"

        elif os.path.exists(f"{file_name}.nlo"):
            with open(f"{file_name}.nlo", "r") as f:
                content = f.read()
            if content.strip():  # Check if content is not empty
                subprocess.run(["makeindex", "-s", "nomencl.ist", "-o", f"{file_name}.nls", f"{file_name}.nlo"])
                index_compile_tex_times = 1
                catalogs_print = "nomencl 宏包生成符号索引"
            else:
                index_compile_tex_times = 0
                catalogs_print = "nomencl 宏包没有进行索引"      
        else:
            if os.path.exists(f"{file_name}.toc"):
                index_compile_tex_times = 1 # 目录需要额外编译 1 次
                catalogs_print = "含有图\表\章节目录"
            else:
                index_compile_tex_times = 0
                catalogs_print = "没有插入任何目录"

        print(catalogs_print)
    else: 
        index_compile_tex_times = 0
        catalogs_print = "没有插入任何目录"

    return index_compile_tex_times, catalogs_print

# --------------------------------------------------------------------------------
# 定义编译 xdv 文件命令
# --------------------------------------------------------------------------------
def compile_xdv(tex_name,file_name):
    if tex_name == "xelatex": 
            print("\n\n" + "=" * 80 + "\n" +
                "X" * 32 + " xdvipdfmx 编译 " + "X" * 32 + "\n" +
                "=" * 80 + "\n\n")
            subprocess.run(["xdvipdfmx", "-V", "1.6", f"{file_name}"]) # 将 xelatex 生成的 xdv 转换成 pdf