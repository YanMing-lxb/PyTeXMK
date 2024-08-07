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
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2024-08-07 18:23:11 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language/lang_help.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-

magic_comments_desc_en = {
    '% !TEX program = pdflatex': 'Set program: xelatex, pdflatex, lualatex',
    '% !TEX root = file.tex': 'Set main file, supports root dir only',
    '% !TEX outdir = out_folder': 'Set output dir for results',
    '% !TEX auxdir = aux_folder': 'Set dir for auxiliary files'
}
magic_comments_desc_zh = {
    '% !TEX program = pdflatex': '指定编译类型: xelatex pdflatex lualatex',
    '% !TEX root = file.tex': '指定待编译主文件名，仅支持根目录下的文件',
    '% !TEX outdir = out_folder': '指定编译结果存放位置，仅支持文件夹名称',
    '% !TEX auxdir = aux_folder': '指定辅助文件存放位置，仅支持文件夹名称'
}

description_en = """
    [i]LaTeX Auxiliary Compilation Program -- YanMing[/] 
    """
description_zh = """
    [i]LaTeX 辅助编译程序 -- 焱铭[/] 
    """
epilog_en = f"""
    For information on magic comments and other detailed instructions, please run the -r parameter to read the README file.
    If you find any bugs, please update to the latest version and feel free to submit an Issue in the Github repository: https://github.com/YanMing-lxb/PyTeXMK/issues
    """
epilog_zh = f"""
    如欲了解魔法注释以及其他详细说明信息请运行 -r 参数，阅读 README 文件。
    发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues
    """

help_strings_en = {
    'description': description_en,
    'epilog': epilog_en,
    'help': "show PyTeXMK help information and exit",
    'version': "show PyTeXMK version number and exit",
    'readme': "show the README file",
    'PdfLaTeX': "compile using PdfLaTeX",
    'XeLaTeX': "compile using XeLaTeX",
    'LuaLaTeX': "compile using LuaLaTeX",
    'LaTeXDiff': "compile using LaTeXDiff to generate a difference file",
    'LaTeXDiff_compile': "compile using LaTeXDiff and compile the new file",
    'clean': "clear auxiliary files of the main file",
    'Clean': "clear auxiliary files (including root directory) and output files",
    'clean_any': "clear all files with auxiliary file suffixes",
    'Clean_any': "clear all files with auxiliary file suffixes (including root directory) and main file output files",
    'unquiet': "run in non-quiet mode, displaying log information in the terminal",
    'verbose': "show detailed information during PyTeXMK operation",
    'pdf_repair': "attempt to repair all PDF files outside the root directory. Use this option if you encounter 'invalid X X R object' warnings during LaTeX compilation",
    'pdf_preview': "preview the generated PDF file using a web browser or local PDF reader after compilation. If you need to specify the main file to be compiled in the command line, place the -pv command after the document without specifying parameters (e.g., pytexmk main -pv); if you do not need to specify the main file in the command line, just enter -pv (e.g., pytexmk -pv). If [FILE_NAME] is specified, it opens the specified file without compiling (only supports PDF files in the output directory, e.g., pytexmk -pv main)",
    'document': "main file name to be compiled",
    'mcd_title': "Magic Comments Description Table",
    'mcd_description': 'PyTeXMK supports using magic comments to define the main file to be compiled, the compilation program, the storage location of the compilation results, etc. (only supports searching the first 50 lines of the document)',
}

help_strings_zh = {
    'description': description_zh,
    'epilog': epilog_zh,
    'help': "显示 PyTeXMK 的帮助信息并退出",
    'version': "显示 PyTeXMK 的版本号并退出",
    'readme': "显示README文件",
    'PdfLaTeX': "PdfLaTeX 进行编译",
    'XeLaTeX': "XeLaTeX 进行编译",
    'LuaLaTeX': "LuaLaTeX 进行编译",
    'LaTeXDiff': "使用 LaTeXDiff 进行编译, 生成改动对比文件",
    'LaTeXDiff_compile': "使用 LaTeXDiff 进行编译, 生成改动对比文件并编译新文件",
    'clean': "清除所有主文件的辅助文件",
    'Clean': "清除所有主文件的辅助文件（包含根目录）和输出文件",
    'clean_any': "清除所有带辅助文件后缀的文件",
    'Clean_any': "清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件",
    'unquiet': "非安静模式运行, 此模式下终端显示日志信息",
    'verbose': "显示 PyTeXMK 运行过程中的详细信息",
    'pdf_repair': "尝试修复所有根目录以外的 PDF 文件, 当 LaTeX 编译过程中警告 invalid X X R object 时, 可使用此参数尝试修复所有 pdf 文件",
    'pdf_preview': "尝试编译结束后调用 Web 浏览器或者本地PDF阅读器预览生成的PDF文件 (如需指定在命令行中指定待编译主文件, 则 -pv 命令, 需放置 document 后面并无需指定参数, 示例: pytexmk main -pv; 如无需在命令行中指定待编译主文件, 则直接输入 -pv 即可, 示例: pytexmk -pv), 如有填写 [FILE_NAME] 则不进行编译打开指定文件 (注意仅支持输出目录下的 PDF 文件, 示例: pytexmk -pv main)",
    'document': "待编译主文件名",
    'mcd_title': "魔法注释说明表",
    'mcd_description': 'PyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）',
}