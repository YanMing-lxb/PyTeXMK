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
LastEditTime : 2024-08-07 21:34:42 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import argparse
import datetime
import webbrowser
from rich import print
from pathlib import Path
import importlib.resources
from rich.console import Console
from rich_argparse import RichHelpFormatter

from .version import script_name, __version__

from .language import lang_help
from .language_module import check_language, info_desc

from .run_module import RUN
from .logger_config import setup_logger
from .additional_module import MoveRemoveClean, MainFileJudgment, PdfFileOperation, exit_pytexmk
from .get_main_file_module import get_main_file
from .info_print_module import time_count, time_print, print_message, magic_comment_desc_table
from .latexdiff_module import LaTeXDiff_Aux
from .check_version_module import UpdateChecker

MFJ = MainFileJudgment() # 实例化 MainFileJudgment 类
MRC = MoveRemoveClean() # 实例化 MoveRemoveClean 类
PFO = PdfFileOperation() # 实例化 PdfFileOperation 类
UC = UpdateChecker(1, 6) # 访问超时, 单位: 秒；缓存时长, 单位: 小时


lang = check_language()
if lang:
    help_list = lang_help.help_strings_zh
    magic_comment_desc_list = lang_help.magic_comments_desc_zh
else:
    help_list = lang_help.help_strings_en
    magic_comment_desc_list = lang_help.magic_comments_desc_en

class CustomArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if status == 0 and message is None:  # 只有在请求帮助信息时，status 为 0，message 为 None
            # 检查并获取对应语言的帮助信息
            print(f"\n{info_desc(help_list, 'mcd_description')}\n")
            table = magic_comment_desc_table(magic_comment_desc_list, info_desc(help_list, 'mcd_title'))
            console = Console() # 创建控制台对象
            console.print(table)
        super().exit(status, message)




def parse_args():
    # 不能再在这个程序上花时间了, 该看论文学技术了, 要不然博士怎么毕业啊, 吐了。---- 焱铭,2024-07-28 21:02:30
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    # 创建 ArgumentParser 对象
    parser = CustomArgumentParser(
        prog = 'pytexmk',
        description=info_desc(help_list, 'description'), 
        epilog=info_desc(help_list, 'epilog'), 
        formatter_class=RichHelpFormatter, 
        add_help=False)

    meg_clean = parser.add_mutually_exclusive_group()
    meg_engine = parser.add_mutually_exclusive_group()

    # 添加命令行参数
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: version [i]{__version__}', help=info_desc(help_list,'version'))
    parser.add_argument('-h', '--help', action='help', help=info_desc(help_list, 'help'))
    parser.add_argument('-r', '--readme', action='store_true', help=info_desc(help_list, 'readme'))
    meg_engine.add_argument('-p', '--PdfLaTeX', action='store_true', help=info_desc(help_list, 'PdfLaTeX'))
    meg_engine.add_argument('-x', '--XeLaTeX', action='store_true', help=info_desc(help_list, 'XeLaTeX'))
    meg_engine.add_argument('-l', '--LuaLaTeX', action='store_true', help=info_desc(help_list, 'LuaLaTeX'))
    parser.add_argument('-d', '--LaTeXDiff', nargs=2, metavar=('OLD_FILE', 'NEW_FILE'), help=info_desc(help_list, 'LaTeXDiff')) # 吐了, 又在这个功能上花费了一上午的时间。---- 焱铭,2024-08-02 12:48:23
    parser.add_argument('-dc', '--LaTexDiff-compile', nargs=2, metavar=('OLD_FILE', 'NEW_FILE'), help=info_desc(help_list, 'LaTeXDiff_compile'))
    meg_clean.add_argument('-c', '--clean', action='store_true', help=info_desc(help_list, 'clean'))
    meg_clean.add_argument('-C', '--Clean', action='store_true', help=info_desc(help_list, 'Clean'))
    meg_clean.add_argument('-ca', '--clean-any', action='store_true', help=info_desc(help_list, 'clean_any'))
    meg_clean.add_argument('-Ca', '--Clean-any', action='store_true', help=info_desc(help_list, 'Clean_any'))
    parser.add_argument('-uq', '--unquiet', action='store_true', help=info_desc(help_list, 'unquiet'))
    parser.add_argument('-vb', '--verbose', action='store_true', help=info_desc(help_list,'verbose'))
    parser.add_argument('-pr', '--pdf-repair', action='store_true', help=info_desc(help_list, 'pdf_repair'))
    parser.add_argument('-pv', '--pdf-preview', nargs='?', default='Do not start', metavar='FILE_NAME', help=info_desc(help_list, 'pdf_preview'))
    parser.add_argument('document', nargs='?', help=info_desc(help_list, 'document'))

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
    magic_comments = {} # 存储魔法注释
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

    print(f"PyTeXMK 版本: [bold green]{__version__}[/bold green]\n")
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
            logger.info('README 的本地路径是: file://' + readme_path.resolve().as_posix())
            # 使用 webbrowser 打开 README.html 文件
            webbrowser.open('file://' + readme_path.resolve().as_posix())
        except Exception as e:
            # 记录打开 README 文件时的错误信息
            logger.error(f"打开 README 文件时出错: {e}")
        finally:
            # 打印退出信息并退出程序
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 非编译预览 PDF 操作
    # --------------------------------------------------------------------------------
    pdf_preview_status = args.pdf_preview # 存储是否需要预览 PDF 状态
    if pdf_preview_status != 'Do not start' and pdf_preview_status != None: # 当 -pv 参数存在时, 有值且不等于默认值 'Do not start' 时, 进行 PDF 预览操作
        pdf_files_in_outdir = MFJ.get_suffixes_files_in_dir(outdir, '.pdf')
        pdf_preview_status = MFJ.check_project_name(pdf_files_in_outdir, pdf_preview_status, '.pdf')
        PFO.pdf_preview(pdf_preview_status, outdir) # 调用 pdf_preview 函数进行 PDF 预览操作

    # --------------------------------------------------------------------------------
    # 主文件逻辑预处理判断
    # --------------------------------------------------------------------------------
    tex_files_in_root = MFJ.get_suffixes_files_in_dir('.', '.tex') # 获取当前根目录下所有 tex 文件, 并去掉文件后缀
    main_file_in_root = MFJ.find_tex_commands(tex_files_in_root) # 判断获取当前根目录下的主文件列表
    all_magic_comments = MFJ.search_magic_comments(main_file_in_root, magic_comments_keys) # 搜索 main_file_in_root 中每个文件的魔法注释

    if args.LaTeXDiff or args.LaTexDiff_compile:
        if args.LaTeXDiff:
            old_tex_file, new_tex_file = args.LaTeXDiff # 获取 -d 参数指定的两个文件
        elif args.LaTexDiff_compile:
            old_tex_file, new_tex_file = args.LaTexDiff_compile # 获取 -dc 参数指定的两个文件
        old_tex_file = MFJ.check_project_name(main_file_in_root, old_tex_file, '.tex') # 检查 old_tex_file 是否正确
        new_tex_file = MFJ.check_project_name(main_file_in_root, new_tex_file, '.tex') # 检查 new_tex_file 是否正确
    else:
        project_name = get_main_file(args.document, main_file_in_root, all_magic_comments) # 通过进行一系列判断获取主文件名

    # --------------------------------------------------------------------------------
    # 主文件魔法注释提取
    # --------------------------------------------------------------------------------
    if all_magic_comments: # 如果存在魔法注释
        for key, values in all_magic_comments.items():  # 遍历所有提取的魔法注释
            for value in values:  # 遍历魔法注释中所有值
                if value[0] == project_name:  # 如果是project_name对应的文件
                    magic_comments[key] = value[1]  # 存储魔法注释
                    logger.info(f"提取魔法注释: {value[0]}.tex --> % !TEX {key} = {value[1]}")

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
            exit_pytexmk()
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
                        exit_pytexmk()
                    finally:
                        runtime_move_matched_files, _ = time_count(MRC.move_matched_files, aux_regex_files, '.', auxdir) # 将所有辅助文件移动到根目录
                        runtime_dict["辅助文件->辅助目录"] = runtime_move_matched_files
                else:
                    logger.error(f"{new_tex_file} 的辅助文件不存在, 请检查编译")
                    exit_pytexmk()

            else: # 如果辅助文件不存在
                logger.error(f"{old_tex_file} 的辅助文件不存在, 请检查编译")
                exit_pytexmk()
            
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

# 吐了啊，又搞了两天，我该好好学学 CAN 通信了，该死的强迫症，啊啊啊啊啊啊！ ---- 焱铭,2024-08-07 21:40:29