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
LastEditTime : 2024-08-07 10:28:47 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import sys
import argparse
import datetime
import webbrowser
from rich import print
from pathlib import Path
import importlib.resources
from rich_argparse import RichHelpFormatter

from .version import script_name, __version__

from .language import lang_help
from .language_model import check_language, info_desrption

from .run_model import RUN
from .logger_config import setup_logger
from .additional_operation_model import MoveRemoveClean, MainFileJudgment, PdfFileOperation
from .info_print_model import time_count, time_print, print_message
from .latexdiff_model import LaTeXDiff_Aux
from .check_version_model import UpdateChecker

MFJ = MainFileJudgment() # 实例化 MainFileJudgment 类
MRC = MoveRemoveClean() # 实例化 MoveRemoveClean 类
PFO = PdfFileOperation() # 实例化 PdfFileOperation 类
UC = UpdateChecker(1, 6) # 访问超时, 单位：秒；缓存时长, 单位：小时

def parse_args():
    # 不能再在这个程序上花时间了, 该看论文学技术了, 要不然博士怎么毕业啊, 吐了。---- 焱铭,2024-07-28 21:02:30
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    # TODO 完善对魔法注释的说明

    # 检查并获取对应语言的帮助信息
    help_list = check_language(lang_help.help_strings_zh, lang_help.help_strings_en)

    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(
        prog = 'pytexmk',
        description=info_desrption(help_list, 'description'), 
        epilog=info_desrption(help_list, 'epilog'), 
        formatter_class=RichHelpFormatter, 
        add_help=False)

    meg_clean = parser.add_mutually_exclusive_group()
    meg_engine = parser.add_mutually_exclusive_group()
    meg_diff = parser.add_mutually_exclusive_group()

    # 添加命令行参数
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: version [i]{__version__}', help=info_desrption(help_list,'version'))
    parser.add_argument('-h', '--help', action='help', help=info_desrption(help_list, 'help'))
    parser.add_argument('-r', '--readme', action='store_true', help=info_desrption(help_list, 'readme'))

    meg_engine.add_argument('-p', '--PdfLaTeX', action='store_true', help=info_desrption(help_list, 'PdfLaTeX'))
    meg_engine.add_argument('-x', '--XeLaTeX', action='store_true', help=info_desrption(help_list, 'XeLaTeX'))
    meg_engine.add_argument('-l', '--LuaLaTeX', action='store_true', help=info_desrption(help_list, 'LuaLaTeX'))

    meg_diff.add_argument('-d', '--LaTeXDiff', nargs=2, metavar=('OLD_FILE', 'NEW_FILE'), help=info_desrption(help_list, 'LaTeXDiff')) # 吐了, 又在这个功能上花费了一上午的时间。---- 焱铭,2024-08-02 12:48:23
    meg_diff.add_argument('-dc', '--LaTexDiff-compile', nargs=2, metavar=('OLD_FILE', 'NEW_FILE'), help=info_desrption(help_list, 'LaTeXDiff_compile'))

    meg_clean.add_argument('-c', '--clean', action='store_true', help=info_desrption(help_list, 'clean'))
    meg_clean.add_argument('-C', '--Clean', action='store_true', help=info_desrption(help_list, 'Clean'))
    meg_clean.add_argument('-ca', '--clean-any', action='store_true', help=info_desrption(help_list, 'clean_any'))
    meg_clean.add_argument('-Ca', '--Clean-any', action='store_true', help=info_desrption(help_list, 'Clean_any'))

    parser.add_argument('-pr', '--pdf-repair', action='store_true', help=info_desrption(help_list, 'pdf_repair'))
    parser.add_argument('-pv', '--pdf-preview', nargs='?', default='Do not start', metavar='FILE_NAME', help=info_desrption(help_list, 'pdf_preview'))

    parser.add_argument('-uq', '--unquiet', action='store_true', help=info_desrption(help_list, 'unquiet'))
    parser.add_argument('-vb', '--verbose', action='store_true', help=info_desrption(help_list,'verbose'))

    parser.add_argument('document', nargs='?', help=info_desrption(help_list, 'document'))
    
    # 解析命令行参数
    args = parser.parse_args()

    return args

def main():
    start_time = datetime.datetime.now() # 计算开始时间

    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! 设置默认 ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !
    compiler_engine = "XeLaTeX"
    outdir = "./Build/"
    auxdir = "./Auxiliary/"
    magic_comments_keys = ["program", "root", "outdir", "auxdir"]
    runtime_dict = {}
    suffixes_out = [".pdf", ".synctex.gz"]
    suffixes_aux = [".log", ".blg", ".ilg",  # 日志文件
                    ".aux", ".bbl", ".xml",  # 参考文献辅助文件
                    ".toc", ".lof", ".lot",  # 目录辅助文件
                    ".out", ".bcf",
                    ".idx", ".ind", ".nlo", ".nls", ".ist", ".glo", ".gls",  # 索引辅助文件
                    ".bak", ".spl",
                    ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc", ".listing", ".gz",
                    ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv", ".fdb_latexmk", ".run.xml"]

    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !

    # 解析命令行参数
    args = parse_args()

    # 实例化 logger 类
    logger = setup_logger(args.verbose)

    print(f"PyTeXMK 版本：[bold green]{__version__}[/bold green]\n")
    print('[bold green]PyTeXMK 开始运行...\n')


    # --------------------------------------------------------------------------------
    # README 文件打开函数
    # --------------------------------------------------------------------------------
    if args.readme: # 如果存在 readme 参数
        try:
            # 使用 pathlib 获取包数据路径
            data_path = Path(importlib.resources.files('pytexmk')) / 'data'
            # 使用 pathlib 拼接 README.html 文件路径
            readme_path = data_path / "README.html"
            print(f"[bold green]正在打开 README 文件...")
            # 使用 pathlib 获取 README.html 文件的绝对路径
            logger.info('README 的本地路径是：file://' + readme_path.resolve().as_posix())
            # 使用 webbrowser 打开 README.html 文件
            webbrowser.open('file://' + readme_path.resolve().as_posix())
        except Exception as e:
            # 记录打开 README 文件时的错误信息
            logger.error(f"打开 README 文件时出错: {e}")
        finally:
            # 打印退出信息并退出程序
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit()

    # --------------------------------------------------------------------------------
    # 主文件逻辑判断
    # --------------------------------------------------------------------------------
    # TODO 添加块注释, 或者整合到additional_operation.py中
    project_name = '' # 待编译主文件名
    tex_files_in_root = MFJ.get_suffixes_files_in_dir('.', '.tex') # 运行 get_tex_file_in_root 函数判断获取当前根目录下所有 tex 文件, 并去掉文件后缀
    main_file_in_root = MFJ.find_tex_commands(tex_files_in_root) # 运行 find_tex_commands 函数判断获取当前根目录下的主文件列表
    all_magic_comments = MFJ.search_magic_comments(main_file_in_root, magic_comments_keys) # 运行 search_magic_comments 函数搜索 main_file_in_root 每个文件的魔法注释
    magic_comments = {} # 存储魔法注释
    pdf_preview_status = args.pdf_preview # 存储是否需要预览 PDF 状态

    if pdf_preview_status != 'Do not start' and pdf_preview_status != None: # 当 -pv 参数存在时, 有值且不等于默认值 'Do not start' 时, 进行 PDF 预览操作
        pdf_files_in_outdir = MFJ.get_suffixes_files_in_dir(outdir, '.pdf')
        pdf_preview_status = MFJ.check_project_name(pdf_files_in_outdir, pdf_preview_status, '.pdf')
        PFO.pdf_preview(pdf_preview_status, outdir)

    if args.LaTeXDiff or args.LaTexDiff_compile:
        if args.LaTeXDiff:
            old_tex_file, new_tex_file = args.LaTeXDiff # 获取 -d 参数指定的两个文件
        elif args.LaTexDiff_compile:
            old_tex_file, new_tex_file = args.LaTexDiff_compile # 获取 -dc 参数指定的两个文件
        old_tex_file = MFJ.check_project_name(main_file_in_root, old_tex_file, '.tex') # 检查 old_tex_file 是否正确
        new_tex_file = MFJ.check_project_name(main_file_in_root, new_tex_file, '.tex') # 检查 new_tex_file 是否正确
    else:
        current_path = Path.cwd()  # 使用pathlib库获取当前工作目录的路径
        if args.document: # 当前目录下存在 tex 文件, 且命令行参数中指定了主文件
            project_name = args.document # 使用命令行参数指定主文件
            print(f"通过命令行命令指定待编译主文件为：[bold cyan]{project_name}[/bold cyan]")
        elif len(main_file_in_root) == 1: # 如果当前根目录下存在且只有一个主文件
            project_name = main_file_in_root[0] # 使用该文件作为待编译主文件
            print(f"通过根目录下唯一主文件指定待编译主文件为：[bold cyan]{project_name}.tex[/bold cyan]")

        elif 'root' in all_magic_comments: # 当前目录下存在多个主文件, 且存在 % TEX root 魔法注释
            logger.info("魔法注释 % !TEX root 在当前根目录下主文件中有被定义")
            if len(all_magic_comments['root']) == 1: # 当前目录下存在多个主文件, 且只有一个存在 % TEX root 魔法注释
                logger.info(f"魔法注释 % !TEX root 只存在于 {all_magic_comments['root'][0][0]}.tex 中")
                check_file = MFJ.check_project_name(main_file_in_root, all_magic_comments['root'][0][1], '.tex') # 检查 magic comments 中指定的 root 文件名是否正确
                if f"{all_magic_comments['root'][0][0]}" == f"{check_file}": # 如果 magic comments 中指定的 root 文件名与当前文件名相同
                    project_name = check_file # 使用魔法注释 % !TEX root 指定的文件作为主文件
                    print(f"通过魔法注释 % !TEX root 指定待编译主文件为 [bold cyan]{project_name}.tex[/bold cyan]")
                else: # 如果 magic comments 中指定的 root 文件名与当前文件名不同
                    logger.warning(f"魔法注释 % !TEX root 指定的文件名 [bold cyan]{check_file}.tex[/bold cyan] 与当前文件名 [bold cyan]{all_magic_comments['root'][0][0]}.tex[/bold cyan] 不同, 无法确定主文件")
            if len(all_magic_comments['root']) > 1: # 当前目录下存在多个主文件, 且多个 tex 文件中同时存在 % TEX root 魔法注释
                logger.warning("魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义, 无法根据魔法注释确定待编译主文件") 

        elif not project_name: # 如果当前根目录下存在多个主文件, 且不存在 % TEX root 魔法注释, 并且待编译主文件还没有找到
            logger.info("无法根据魔法注释判断出待编译主文件, 尝试根据默认主文件名指定待编译主文件")
            for file in main_file_in_root:
                if file == "main": # 如果存在 main.tex 文件
                    project_name = file # 使用 main.tex 文件作为待编译主文件名
                    print(f"通过默认文件名 \"main.tex\" 指定待编译主文件为：[bold cyan]{project_name}.tex[/bold cyan]")
            if not project_name: # 如果不存在 main.tex 文件
                logger.info("当前根目录下不存在名为 \"main.tex\" 的文件")

        if not project_name: # 如果当前根目录下不存在主文件且 -d 参数未指定
            logger.error("无法进行编译, 当前根目录下存在多个主文件：" + ", ".join(main_file_in_root))
            logger.warning("请修改待编译主文件名为默认文件名 \"main.tex\" 或在文件中加入魔法注释 \"% !TEX root = <待编译主文件名>\" 或在终端输入 \"pytexmk <待编译主文件名>\" 进行编译, 或删除当前根目录下多余的 tex 文件")
            logger.warning(f"当前根目录是：{current_path}")
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit(1)
        
        project_name = MFJ.check_project_name(main_file_in_root, project_name, '.tex') # 检查 project_name 是否正确 
        

    if all_magic_comments: # 如果存在魔法注释
        for key, values in all_magic_comments.items():  # 遍历所有提取的魔法注释
            for value in values:  # 遍历魔法注释中所有值
                if value[0] == project_name:  # 如果是project_name对应的文件
                    magic_comments[key] = value[1]  # 存储魔法注释
                    logger.info(f"已从 {value[0]}.tex 中提取魔法注释 % !TEX {key} = {value[1]}")

    # --------------------------------------------------------------------------------
    # 编译类型判断
    # -------------------------------------------------------------------------------- 
    if args.XeLaTeX:
        compiler_engine = "XeLaTeX"
    elif args.PdfLaTeX:
        compiler_engine = "PdfLaTeX"
    elif args.LuaLaTeX:
        compiler_engine = "LuaLaTeX"
    elif magic_comments.get('program'): # 如果存在 magic comments 且 program 存在
        compiler_engine = magic_comments['program'] # 使用 magic comments 中的 program 作为编译器
        print(f"通过魔法注释设置编译器为 [bold cyan]{compiler_engine}[/bold cyan]")

    # --------------------------------------------------------------------------------
    # 输出文件路径判断
    # --------------------------------------------------------------------------------
    if magic_comments.get('outdir'): # 如果存在 magic comments 且 outdir 存在
        outdir = magic_comments['outdir'] # 使用 magic comments 中的 outdir 作为输出目录
        print(f"通过魔法注释找到输出目录为 [bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get('auxdir'): # 如果存在 magic comments 且 auxdir 存在
        auxdir = magic_comments['auxdir'] # 使用 magic comments 中的 auxdir 作为辅助文件目录
        print(f"通过魔法注释找到辅助文件目录为 [bold cyan]{auxdir}[/bold cyan]")

    # --------------------------------------------------------------------------------
    # 匹配文件清除命令
    # --------------------------------------------------------------------------------
    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if args.clean_any:
        runtime_remove_aux_matched_auxdir, _ = time_count(MRC.remove_matched_files, aux_regex_files, '.')
        runtime_dict["清除所有的辅助文件"] = runtime_remove_aux_matched_auxdir
        print('[bold green]已完成清除所有带辅助文件后缀的文件的指令')
    elif args.Clean_any:
        runtime_remove_aux_matched_auxdir, _ = time_count(MRC.remove_matched_files, aux_regex_files, '.')
        runtime_dict["清除所有的辅助文件"] = runtime_remove_aux_matched_auxdir
        runtime_remove_out_outdir, _ = time_count(MRC.remove_specific_files, out_files, outdir)
        runtime_dict["清除文件夹内输出文件"] = runtime_remove_out_outdir
        print('[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令')

    # --------------------------------------------------------------------------------
    # LaTeXDiff 相关
    # --------------------------------------------------------------------------------
    if args.LaTeXDiff or args.LaTexDiff_compile:
        LDA = LaTeXDiff_Aux(suffixes_aux, auxdir)
        if old_tex_file == new_tex_file: # 如果 old_tex_file 和 new_tex_file 相同
            logger.error(f"不能对同一个文件进行比较, 请检查文件名是否正确")
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit(1) # 退出程序
        else:
            print_message("LaTeXDiff 预处理", "additional")
            if LDA.check_aux_files(old_tex_file): # 检查辅助文件是否存在
                logger.info(f"{old_tex_file} 的辅助文件存在")
                if LDA.check_aux_files(new_tex_file):
                    logger.info(f"{new_tex_file} 的辅助文件存在")
                    old_tex_file = LDA.flatten_Latex(f"{old_tex_file}")
                    new_tex_file = LDA.flatten_Latex(f"{new_tex_file}")
                    runtime_move_matched_files, _ = time_count(MRC.move_matched_files, aux_regex_files, auxdir, '.') # 将所有辅助文件移动到根目录
                    runtime_dict["全辅助文件->根目录"] = runtime_move_matched_files
                    try:
                        print_message("LaTeXDiff 运行", "running")
                        runtime_compile_LaTeXDiff, _ = time_count(LDA.compile_LaTeXDiff, old_tex_file, new_tex_file)
                        runtime_dict["LaTeXDiff 运行"] = runtime_compile_LaTeXDiff
                        
                        print_message("LaTeXDiff 后处理", "additional")
                        print('删除 Flatten 后的文件...')
                        runtime_remove_flatten_root, _ = time_count(MRC.remove_specific_files, [old_tex_file, new_tex_file], '.')
                        runtime_dict["清除文件夹内输出文件"] = runtime_remove_flatten_root
                        if args.LaTexDiff_compile:
                            out_files = [f"LaTeXDiff{suffix}" for suffix in suffixes_out]
                            print_message("开始预处理命令", "additional")
                            
                            RUN(runtime_dict, "LaTeXDiff", compiler_engine, out_files, aux_files, outdir, auxdir, args.unquiet)

                            print_message("开始后处理命令", "additional")

                            print('移动结果文件到输出目录...')
                            runtime_move_out_outdir, _ = time_count(MRC.move_specific_files, out_files, ".", outdir) # 将输出文件移动到指定目录
                            runtime_dict["结果文件->输出目录"] = runtime_move_out_outdir
                    except Exception as e:
                        logger.error(f"LaTeXDiff 编译出错: {e}")
                        print('[bold red]正在退出 PyTeXMK ...[/bold red]')
                        sys.exit(1) # 退出程序
                    finally:
                        runtime_move_matched_files, _ = time_count(MRC.move_matched_files, aux_regex_files, '.', auxdir) # 将所有辅助文件移动到根目录
                        runtime_dict["辅助文件->辅助目录"] = runtime_move_matched_files
                else:
                    logger.error(f"{new_tex_file} 的辅助文件不存在, 请检查编译")
                    print('[bold red]正在退出 PyTeXMK ...[/bold red]')
                    sys.exit(1) # 退出程序

            else: # 如果辅助文件不存在
                logger.error(f"{old_tex_file} 的辅助文件不存在, 请检查编译")
                print('[bold red]正在退出 PyTeXMK ...[/bold red]')
                sys.exit(1) # 退出程序
            
    # --------------------------------------------------------------------------------
    # LaTeX 运行相关
    # --------------------------------------------------------------------------------        
    elif project_name: # 如果存在 project_name 
        if args.clean:
            runtime_remove_aux_auxdir, _ = time_count(MRC.remove_specific_files, aux_files, auxdir)
            runtime_dict["清除文件夹内辅助文件"] = runtime_remove_aux_auxdir
            runtime_remove_aux_root, _ = time_count(MRC.remove_specific_files, aux_files, '.')
            runtime_dict["清除根目录内辅助文件"] = runtime_remove_aux_root
            print('[bold green]已完成清除所有主文件的辅助文的件指令')
        elif args.Clean:
            runtime_remove_aux_auxdir, _ = time_count(MRC.remove_specific_files, aux_files, auxdir)
            runtime_dict["清除文件夹内辅助文件"] = runtime_remove_aux_auxdir
            runtime_remove_aux_root, _ = time_count(MRC.remove_specific_files, aux_files, '.')
            runtime_dict["清除根目录内辅助文件"] = runtime_remove_aux_root
            runtime_remove_out_outdir, _ = time_count(MRC.remove_specific_files, out_files, outdir)
            runtime_dict["清除文件夹内输出文件"] = runtime_remove_out_outdir
            print('[bold green]已完成清除所有主文件的辅助文件和输出文件的指令')
        elif args.pdf_repair:
            runtime_pdf_repair, _ = time_count(PFO.pdf_repair, project_name, '.', outdir)
            runtime_dict["修复 PDF 文件"] = runtime_pdf_repair
        else:
            print_message("开始预处理命令", "additional")
            print('检测并移动辅助文件到根目录...')
            runtime_move_aux_root, _  = time_count(MRC.move_specific_files, aux_files, auxdir, ".") # 将辅助文件移动到根目录
            runtime_dict['辅助文件->根目录'] = runtime_move_aux_root
            
            RUN(runtime_dict, project_name, compiler_engine, out_files, aux_files, outdir, auxdir, args.unquiet)

            print_message("开始后处理命令", "additional")

            print('移动结果文件到输出目录...')
            runtime_move_out_outdir, _ = time_count(MRC.move_specific_files, out_files, ".", outdir) # 将输出文件移动到指定目录
            runtime_dict["结果文件->输出目录"] = runtime_move_out_outdir

            print('移动辅助文件到辅助目录...')
            runtime_move_aux_auxdir, _ = time_count(MRC.move_specific_files, aux_files, ".", auxdir) # 将辅助文件移动到指定目录
            runtime_dict["辅助文件->辅助目录"] = runtime_move_aux_auxdir
    
    # --------------------------------------------------------------------------------
    # 编译结束后 PDF 预览
    # --------------------------------------------------------------------------------       
    if pdf_preview_status == None: # 当终端有 -pv 参数时，但没设置值时，默认开启预览功能
        PFO.pdf_preview(project_name, outdir)

    # --------------------------------------------------------------------------------
    # 打印 PyTeXMK 运行时长统计信息
    # --------------------------------------------------------------------------------       
    if runtime_dict: # 如果存在运行时统计信息
        time_print(start_time, runtime_dict) # 打印编译时长统计

    # --------------------------------------------------------------------------------
    # 检查更新
    # --------------------------------------------------------------------------------
    UC.check_for_updates()

if __name__ == "__main__":
    main()