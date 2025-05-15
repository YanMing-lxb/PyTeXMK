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
LastEditTime : 2025-05-15 18:54:18 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import argparse
import datetime
import webbrowser
from pathlib import Path

# rich 库（美化 CLI 输出）
from rich import print
from rich.console import Console
from rich_argparse import RichHelpFormatter

# 版本信息
from pytexmk.version import script_name, __version__

# 日志与语言配置
from pytexmk.logger_config import setup_logger
from pytexmk.language import set_language

# 信息输出模块
from pytexmk.info_print import (time_count, time_print, print_message, magic_comment_desc_table)

# 主要功能模块
from pytexmk.run import RUN, LaTeXDiffRUN
from pytexmk.latexdiff import LaTeXDiff_Aux
from pytexmk.log_parser import LatexLogParser
from pytexmk.additional import (MoveRemoveOperation, MainFileOperation, PdfFileOperation)

# 辅助功能
from pytexmk.config import ConfigParser
from pytexmk.check_version import UpdateChecker
from pytexmk.auxiliary_fun import (get_app_path, exit_pytexmk)

UC = UpdateChecker(1, 6)  # 访问超时, 单位: 秒;缓存时长, 单位: 小时
_ = set_language('__main__')


class CustomArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        if status == 0 and message is None:  # 只有在请求帮助信息时,status 为 0,message 为 None
            # 检查并获取对应语言的帮助信息
            print(_("\nPyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）\n")
                 )
            table = magic_comment_desc_table()
            console = Console()  # 创建控制台对象
            console.print(table)
            UC.check_for_updates()
        super().exit(status, message)


class CustomHelpFormatter(RichHelpFormatter):

    def _format_args(self, action, default_metavar):
        if action.dest == 'LaTeXDiff_compile' or action.dest == 'LaTeXDiff':
            return 'OLD_FILE NEW_FILE'
        return super()._format_args(action, default_metavar)


# --------------------------------------------------------------------------------
# 定义命令行参数
# --------------------------------------------------------------------------------
def parse_args():
    # 创建 ArgumentParser 对象
    parser = CustomArgumentParser(
        prog='pytexmk',
        description=_("[i]LaTeX 辅助编译程序  ---- 焱铭[/]"),
        epilog=_("如欲了解魔法注释以及其他详细说明信息请运行 -r 参数，阅读 README 文件。发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues"),
        formatter_class=CustomHelpFormatter,
        add_help=False)

    meg_clean = parser.add_mutually_exclusive_group()
    meg_engine = parser.add_mutually_exclusive_group()

    # 添加命令行参数
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: version [i]{__version__}', help=_("显示 PyTeXMK 的版本号并退出"))
    parser.add_argument('-h', '--help', action='help', help=_("显示 PyTeXMK 的帮助信息并退出"))
    parser.add_argument('-r', '--readme', action='store_true', help=_("显示README文件"))
    meg_engine.add_argument('-p', '--PdfLaTeX', action='store_true', help=_("PdfLaTeX 进行编译"))
    meg_engine.add_argument('-x', '--XeLaTeX', action='store_true', help=_("XeLaTeX 进行编译"))
    meg_engine.add_argument('-l', '--LuaLaTeX', action='store_true', help=_("LuaLaTeX 进行编译"))
    parser.add_argument('-d', '--LaTeXDiff', nargs='*', metavar=('OLD_FILE', 'NEW_FILE'), help=_("使用 LaTeXDiff 进行编译, 生成改动对比文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE'"))
    parser.add_argument('-dc', '--LaTeXDiff-compile', nargs='*', metavar=('OLD_FILE', 'NEW_FILE'), help=_("使用 LaTeXDiff 进行编译, 生成改动对比文件并编译新文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE'"))
    parser.add_argument('-dr', '--draft', action='store_true', help=_("启用草稿模式进行编译，提高编译速度 (无图显示)"))
    meg_clean.add_argument('-c', '--clean', action='store_true', help=_("清除所有主文件的辅助文件"))
    meg_clean.add_argument('-C', '--Clean', action='store_true', help=_("清除所有主文件的辅助文件（包含根目录）和输出文件"))
    meg_clean.add_argument('-ca', '--clean-any', action='store_true', help=_("清除所有带辅助文件后缀的文件"))
    meg_clean.add_argument('-Ca', '--Clean-any', action='store_true', help=_("清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件"))
    parser.add_argument('-nq', '--non-quiet', action='store_true', help=_("非安静模式运行, 此模式下终端显示日志信息"))
    parser.add_argument('-vb', '--verbose', action='store_true', help=_("显示 PyTeXMK 运行过程中的详细信息"))
    parser.add_argument('-pr', '--pdf-repair', action='store_true', help=_("尝试修复所有根目录以外的 PDF 文件, 当 LaTeX 编译过程中警告 invalid X X R object 时, 可使用此参数尝试修复所有 pdf 文件"))
    parser.add_argument('-pv', '--pdf-preview', nargs='?', const='preview after compile', metavar='FILE_NAME', help=_("尝试编译结束后调用 Web 浏览器或者本地 PDF 阅读器预览生成的PDF文件 (如需指定在命令行中指定待编译主文件, 则 -pv 命令, 需放置 document 后面并无需指定参数, 示例: pytexmk main -pv; 如无需在命令行中指定待编译主文件, 则直接输入 -pv 即可, 示例: pytexmk -pv), 如有填写 [dark_cyan]FILE_NAME[/dark_cyan] 则不进行编译打开指定文件 (注意仅支持输出目录下的 PDF 文件, 示例: pytexmk -pv main)"))
    parser.add_argument('document', nargs='?', help=_("待编译主文件名"))

    # 解析命令行参数
    args = parser.parse_args()

    return args


# --------------------------------------------------------------------------------
# 标准化名称方法
# --------------------------------------------------------------------------------
def standardize_name(compiled_program):
    standard_names = {"xelatex": "XeLaTeX", "pdflatex": "PdfLaTeX", "lualatex": "LuaLaTeX"}
    return standard_names.get(compiled_program.lower(), compiled_program)


# --------------------------------------------------------------------------------
# 主程序
# --------------------------------------------------------------------------------
def main():
    start_time = datetime.datetime.now()  # 计算开始时间

    MFO = MainFileOperation()  # 实例化 MainFileOperation 类
    MRO = MoveRemoveOperation()  # 实例化 MoveRemoveOperation 类
    PFO = PdfFileOperation()  # 实例化 PdfFileOperation 类
    CP = ConfigParser()  # 实例化 ConfigParser 类

    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! 设置默认 ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !
    verbose = False

    default_file = "main"
    compiled_program = "XeLaTeX"
    non_quiet = False
    local_config_auto_init = True  # 是否自动创建本地配置文件

    pdf_preview_status = "preview after compile"
    pdf_viewer = "default"  # PDF查看器: default为默认PDF查看器

    outdir = "./Build/"
    auxdir = "./Auxiliary/"

    old_tex_file = "old_file"  # 旧TeX文件
    new_tex_file = "new_file"  # 新TeX文件
    diff_tex_file = "LaTeXDiff"  # 差异TeX文件

    suffixes_out = [".pdf", ".synctex.gz"]
    suffixes_aux = [
        ".log",
        ".blg",
        ".ilg",  # 日志文件
        ".aux",
        ".bbl",
        ".xml",  # 参考文献辅助文件
        ".toc",
        ".lof",
        ".lot",  # 目录辅助文件
        ".out",
        ".bcf",
        ".idx",
        ".ind",
        ".nlo",
        ".nls",
        ".ist",
        ".glo",
        ".gls",  # 索引辅助文件
        ".bak",
        ".spl",
        ".ent-x",
        ".tmp",
        ".ltx",
        ".los",
        ".lol",
        ".loc",
        ".listing",
        ".gz",
        ".userbak",
        ".nav",
        ".snm",
        ".vrb",
        ".fls",
        ".xdv",
        ".fdb_latexmk",
        ".run.xml"
    ]

    magic_comments_keys = ["program", "root", "outdir", "auxdir"]
    project_name = ""
    runtime_dict = {}
    magic_comments = {}  # 存储魔法注释

    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !

    # 解析命令行参数
    args = parse_args()


    print(_("PyTeXMK 版本: %(args)s") % {"args": f"[i bold green]{__version__}[/i bold green]\n"})
    print(_("[bold green]PyTeXMK 开始运行...\n"))

    # --------------------------------------------------------------------------------
    # 详细模式及实例化日志
    # --------------------------------------------------------------------------------
    if args.verbose:
        verbose = args.verbose  # 存储详细模式参数
    logger = setup_logger(verbose)

    # --------------------------------------------------------------------------------
    # README 文件打开函数
    # --------------------------------------------------------------------------------
    if args.readme:  # 如果存在 readme 参数
        try:
            app_path = get_app_path() # 获取应用程序路径

            # 使用 pathlib 拼接 README.html 文件路径
            readme_path = app_path / "data" / "README.html"

            if readme_path.exists():
                print(_("[bold green]正在打开 README 文件..."))
                # 使用 pathlib 获取 README.html 文件的绝对路径
                logger.info(_("README 本地路径: %(args)s") % {"args": f"file://{readme_path.resolve().as_posix()}"})
                # 使用 webbrowser 打开 README.html 文件
                webbrowser.open(f'file://{readme_path.resolve().as_posix()}')
            else:
                logger.error(_("README.html 文件未找到: ") + str(readme_path))
                import time
                time.sleep(60)

        except Exception as e:
            # 记录打开 README 文件时的错误信息
            logger.error(_("打开 README 文件出错: ") + str(e))
        finally:
            # 打印退出信息并退出程序
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # TeX 文件获取判断,魔法注释获取
    # --------------------------------------------------------------------------------
    logger.info("-" * 70)
    tex_files_in_root = MFO.get_suffix_files_in_dir('.', '.tex')  # 获取当前根目录下所有 tex 文件, 并去掉文件后缀
    main_files_in_root = MFO.find_tex_commands(tex_files_in_root)  # 判断获取当前根目录下的主文件列表
    all_magic_comments = MFO.search_magic_comments(main_files_in_root, magic_comments_keys)  # 搜索 main_files_in_root 中每个文件的魔法注释

    # --------------------------------------------------------------------------------
    # 配置文件相关
    # --------------------------------------------------------------------------------
    logger.info("-" * 70)
    config_dict = CP.init_config_file()  # 初始化配置文件,获取配置文件中的参数

    # 读取配置文件中的参数
    if config_dict["default_file"]:  # 如果存在配置文件中的默认文件名
        default_file = config_dict["default_file"]
        logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{default_file}")
    if config_dict["compiled_program"]:  # 如果存在配置文件中的编译器
        compiled_program = standardize_name(config_dict["compiled_program"])
        logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{compiled_program}")
    if config_dict['quiet_mode']:  # 如果配置文件中的安静模式参数为 True
        non_quiet = False
        logger.info(_("通过配置文件设置安静模式为: ") + f"[bold cyan]{config_dict['quiet_mode']}")

    if config_dict["folder"]:  # 如果存在配置文件中的文件夹参数
        if config_dict["folder"]["outdir"]:  # 如果存在配置文件中的输出目录
            outdir = config_dict["folder"]["outdir"]
            logger.info(_("通过配置文件设置输出目录为: ") + f"[bold cyan]{outdir}")
        if config_dict["folder"]["auxdir"]:  # 如果存在配置文件中的辅助目录
            auxdir = config_dict["folder"]["auxdir"]
            logger.info(_("通过配置文件设置辅助目录为: ") + f"[bold cyan]{auxdir}")

    if config_dict["pdf"]:  # 如果存在配置文件中的 pdf 参数
        if config_dict["pdf"]["pdf_preview_status"]:  # 如果存在配置文件中的 pdf_preview 参数
            pdf_preview_status = config_dict["pdf"]["pdf_preview_status"]  # 表示编译结束预览 PDF
            logger.info(_("通过配置文件设置 PDF 预览为: ") + f"[bold cyan]{pdf_preview_status}")
        if config_dict["pdf"]["pdf_viewer"]:  # 如果存在配置文件中的 viewer 参数
            pdf_viewer = config_dict["pdf"]["pdf_viewer"]
            PFO.set_viewer(pdf_viewer)
            logger.info(_("通过配置文件设置 PDF 预览器为: ") + f"[bold cyan]{pdf_viewer}")

    if config_dict["index"]:  # 如果存在配置文件中的 index 参数
        # TODO 与之对应的 index_judgment 函数关于配置部分接口需要完善
        if config_dict["index"]["index_style_file"]:  # 如果存在配置文件中的 index_style_file 参数
            index_style_file = config_dict["index"]["index_style_file"]
            logger.info(_("通过配置文件设置索引文件名为: ") + f"[bold cyan]{index_style_file}")
        if config_dict["index"]["input_suffix"]:  # 如果存在配置文件中的 input_suffix 参数
            input_suffix = config_dict["index"]["input_suffix"]
            logger.info(_("通过配置文件设置索引输入文件后缀为: ") + f"[bold cyan]{input_suffix}")
        if config_dict["index"]["output_suffix"]:  # 如果存在配置文件中的 output_suffix 参数
            output_suffix = config_dict["index"]["output_suffix"]
            logger.info(_("通过配置文件设置索引输出文件后缀为: ") + f"[bold cyan]{output_suffix}")

    if config_dict["latexdiff"]:  # 如果存在配置文件中的 latexdiff 参数
        if config_dict["latexdiff"]["old_tex_file"]:  # 如果存在配置文件中的 old_tex_file 参数
            old_tex_file = config_dict["latexdiff"]["old_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 旧文件为: ") + f"[bold cyan]{old_tex_file}")
        if config_dict["latexdiff"]["new_tex_file"]:  # 如果存在配置文件中的 new_tex_file 参数
            new_tex_file = config_dict["latexdiff"]["new_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 新文件为: ") + f"[bold cyan]{new_tex_file}")
        if config_dict["latexdiff"]["diff_tex_file"]:  # 如果存在配置文件中的 diff_tex_file 参数
            diff_tex_file = config_dict["latexdiff"]["diff_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 对比文件为: ") + f"[bold cyan]{diff_tex_file}")

    # TODO 添加suffixes_aux 与 suffixes_out 相关的配置参数和功能

    # --------------------------------------------------------------------------------
    # 命令行安静模式判断
    # --------------------------------------------------------------------------------
    logger.info("-" * 70)
    if args.non_quiet:  # 如果存在 non_quiet 参数
        non_quiet = args.non_quiet
    if non_quiet == True:  # 如果存在 anon_quiet 参数
        logger.info(_("非安静模式运行"))

    # --------------------------------------------------------------------------------
    # 非编译预览 PDF 操作
    # --------------------------------------------------------------------------------
    pdf_preview_status = args.pdf_preview  # 存储是否需要预览 PDF 状态
    if pdf_preview_status and pdf_preview_status != 'preview after compile' and not args.document:  # 当 -pv 指定参数时, 进行 PDF 预览操作
        pdf_files_in_outdir = MFO.get_suffix_files_in_dir(outdir, '.pdf')
        pdf_preview_status = MFO.check_project_name(pdf_files_in_outdir, pdf_preview_status, '.pdf')
        PFO.pdf_preview(pdf_preview_status, outdir)  # 调用 pdf_preview 函数进行 PDF 预览操作

    # --------------------------------------------------------------------------------
    # 主文件逻辑预处理判断
    # --------------------------------------------------------------------------------
    if args.LaTeXDiff or args.LaTeXDiff_compile or args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
        # 当 -d -dc 参数存在但未在命令行指定两个 TeX 文件时, 尝试从配置文件中读取
        if args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
            print(_("命令行未指定 LaTeXDiff 相关参数"))
            if new_tex_file and old_tex_file:
                print(_("根据配置文件设置 LaTeXDiff 新 TeX 文件为: ") + f"[bold cyan]{new_tex_file}")
                print(_("根据配置文件设置 LaTeXDiff 旧 TeX 文件为: ") + f"[bold cyan]{old_tex_file}")
            else:
                logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
                exit_pytexmk()

        if args.LaTeXDiff and len(args.LaTeXDiff) != 2 or args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) != 2:
            logger.error(_("请同时指定 LaTeXDiff 所需的新旧 TeX 文件"))
            exit_pytexmk()
        if args.LaTeXDiff and len(args.LaTeXDiff) == 2:
            old_tex_file, new_tex_file = args.LaTeXDiff
        if args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) == 2:
            old_tex_file, new_tex_file = args.LaTeXDiff_compile

        old_tex_file = MFO.check_project_name(main_files_in_root, old_tex_file, '.tex')  # 检查 old_tex_file 是否正确
        new_tex_file = MFO.check_project_name(main_files_in_root, new_tex_file, '.tex')  # 检查 new_tex_file 是否正确
    elif not args.readme:  # 如果不存在 readme 参数，也就是普通的编译模式
        project_name = MFO.get_main_file(default_file, args.document, main_files_in_root, all_magic_comments)  # 通过进行一系列判断获取主文件名

    # --------------------------------------------------------------------------------
    # 主文件魔法注释提取
    # --------------------------------------------------------------------------------
    if all_magic_comments:  # 如果存在魔法注释
        for key, values in all_magic_comments.items():  # 遍历所有提取的魔法注释
            if key == "root":  # 如果是 root 关键字,跳过
                continue

            if project_name in values:  # 如果魔法注释中存在 project_name
                magic_comments[key] = values[project_name]  # 存储魔法注释
                logger.info(_("提取魔法注释: ") + f"{project_name}.tex ==> % !TEX {key} = {values[project_name]}")

    # --------------------------------------------------------------------------------
    # 编译类型判断
    # --------------------------------------------------------------------------------
    if args.XeLaTeX:
        compiled_program = "XeLaTeX"
    elif args.PdfLaTeX:
        compiled_program = "PdfLaTeX"
    elif args.LuaLaTeX:
        compiled_program = "LuaLaTeX"
    elif magic_comments.get('program'):  # 如果存在 magic comments 且 program 存在
        compiled_program = standardize_name(magic_comments['program'])  # 使用 magic comments 中的 program 作为编译器
        print(_("通过魔法注释设置程序为: ") + f"[bold cyan]{compiled_program}")

    # --------------------------------------------------------------------------------
    # 输出文件路径判断
    # --------------------------------------------------------------------------------
    if magic_comments.get('outdir'):  # 如果存在 magic comments 且 outdir 存在
        outdir = magic_comments['outdir']  # 使用 magic comments 中的 outdir 作为输出目录
        print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get('auxdir'):  # 如果存在 magic comments 且 auxdir 存在
        auxdir = magic_comments['auxdir']  # 使用 magic comments 中的 auxdir 作为辅助文件目录
        print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{auxdir}[/bold cyan]")

    # --------------------------------------------------------------------------------
    # 匹配文件清除命令
    # --------------------------------------------------------------------------------
    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if args.clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, '.')
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        print(_('[bold green]已完成清除所有带辅助文件后缀的文件的指令'))
        if runtime_dict:  # 如果存在运行时统计信息
            time_print(start_time, runtime_dict)  # 打印编译时长统计
        return
    elif args.Clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, '.')
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_('[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令'))
        if runtime_dict:  # 如果存在运行时统计信息
            time_print(start_time, runtime_dict)  # 打印编译时长统计
        return

    # --------------------------------------------------------------------------------
    # LaTeXDiff 相关
    # --------------------------------------------------------------------------------
    if args.LaTeXDiff or args.LaTeXDiff_compile or args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
        if not old_tex_file or not new_tex_file:
            logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
            exit_pytexmk()

        if old_tex_file == new_tex_file:  # 如果 old_tex_file 和 new_tex_file 相同
            logger.error(_("不能对同一个文件进行比较, 请检查文件名是否正确"))
            exit_pytexmk()

        print_message(_("LaTeXDiff 预处理"), "additional")

        # 检查辅助文件是否存在 TODO 要求辅助文件不存在时要自动进行编译
        LDA = LaTeXDiff_Aux(outdir, suffixes_out, suffixes_aux, auxdir)
        if LDA.check_aux_files(old_tex_file):
            logger.info(_("%(args)s 的辅助文件存在") % {"args": old_tex_file})
        else:  # 如果辅助文件不存在
            logger.error(_("%(args)s 的辅助文件不存在, 请检查编译") % {"args": old_tex_file})
            exit_pytexmk()
        if LDA.check_aux_files(new_tex_file):
            logger.info(_("%(args)s 的辅助文件存在") % {"args": new_tex_file})
        else:
            logger.error(_("%(args)s 的辅助文件不存在, 请检查编译") % {"args": new_tex_file})
            exit_pytexmk()

        old_tex_file_flatten = LDA.flatten_Latex(old_tex_file)
        new_tex_file_flatten = LDA.flatten_Latex(new_tex_file)
        runtime_move_matched_files = time_count(MRO.move_matched_files, aux_regex_files, auxdir, '.')  # 将所有辅助文件移动到根目录
        runtime_dict[_("全辅助文件->根目录")] = runtime_move_matched_files
        latex_diff_style = input(_(
            "请输入 LaTeXDiff 的显示风格：\n"
            "  1 - 显示参考文献/符号说明的修改\n"
            "  2 - 不显示参考文献/符号说明的修改\n"
            "请选择 (1 或者 2): "
        ))

        try:
            print_message(_("LaTeXDiff 运行"), "running")
            aux_suffixes_exit = []
            if latex_diff_style == '1':
                for aux_suffix in ['.bbl', '.nls', '.gls', '.idx']:
                    aux_file_exit = LDA.aux_files_both_exist(old_tex_file, new_tex_file, aux_suffix)
                    aux_suffixes_exit.append(aux_file_exit) if aux_file_exit else None
                for aux_suffix in aux_suffixes_exit:
                    runtime_compile_LaTeXDiff = time_count(LDA.compile_LaTeXDiff, old_tex_file, new_tex_file, diff_tex_file, aux_suffix)

            runtime_compile_LaTeXDiff = time_count(LDA.compile_LaTeXDiff, old_tex_file_flatten, new_tex_file_flatten, diff_tex_file, ".tex")
            runtime_dict[_("LaTeXDiff 运行")] = runtime_compile_LaTeXDiff

            print_message(_("LaTeXDiff 后处理"), "additional")
            print(_('删除 Flatten 后的文件...'))
            runtime_remove_flatten_root = time_count(MRO.remove_specific_files, [f"{old_tex_file_flatten}.tex", f"{new_tex_file_flatten}.tex"], '.')
            runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_flatten_root

            if args.LaTeXDiff_compile or args.LaTeXDiff_compile == []:
                out_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_out]
                print_message(_("开始预处理命令"), "additional")
                if latex_diff_style == '1':
                    LaTeXDiffRUN(runtime_dict, diff_tex_file, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet, args.draft)
                elif latex_diff_style == '2':
                    RUN(runtime_dict, diff_tex_file, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet, args.draft)
                else:
                    logger.error(_(
                        "请输入正确的选项 (1 或者 2)\n"
                        "  1 - 显示参考文献/符号说明的修改\n"
                        "  2 - 不显示参考文献/符号说明的修改"
                    ))
                print_message(_("开始后处理"), "additional")

                print(_('移动结果文件到输出目录...'))
                runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)  # 将输出文件移动到指定目录
                runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
        except Exception as e:
            logger.error(_("LaTeXDiff 编译出错: ") + str(e))
            exit_pytexmk()
        finally:
            runtime_move_matched_files = time_count(MRO.move_matched_files, aux_regex_files, '.', auxdir)  # 将所有辅助文件移动到根目录
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_matched_files

    # --------------------------------------------------------------------------------
    # LaTeX 运行相关
    # --------------------------------------------------------------------------------
    elif project_name:  # 如果存在 project_name
        if args.clean:
            runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
            runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
            runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, '.')
            runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
            print(_('[bold green]已完成清除所有主文件的辅助文的件指令'))
        elif args.Clean:
            runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
            runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
            runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, '.')
            runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
            runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
            runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
            print(_('[bold green]已完成清除所有主文件的辅助文件和输出文件的指令'))
        elif args.pdf_repair:
            runtime_pdf_repair = time_count(PFO.pdf_repair, project_name, '.', outdir)
            runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
        else:
            print_message(_("开始预处理"), "additional")
            print(_('检测并移动辅助文件到根目录...'))
            runtime_move_aux_root = time_count(MRO.move_specific_files, aux_files, auxdir, ".")  # 将辅助文件移动到根目录
            runtime_dict[_('辅助文件->根目录')] = runtime_move_aux_root

            RUN(runtime_dict, project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet, args.draft)

            print_message(_("开始后处理"), "additional")

            print(_('移动结果文件到输出目录...'))
            runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)  # 将输出文件移动到指定目录
            runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir

            print(_('移动辅助文件到辅助目录...'))
            runtime_move_aux_auxdir = time_count(MRO.move_specific_files, aux_files, ".", auxdir)  # 将辅助文件移动到指定目录
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir



            # 初始化日志解析器
            log_parser = LatexLogParser()

            # 解析日志
            log_parser.logparser_cli(auxdir, project_name)



    # --------------------------------------------------------------------------------
    # 编译结束后 PDF 预览
    # --------------------------------------------------------------------------------
    if pdf_preview_status == "preview after compile":  # 当终端有 -pv 未指定参数时, 进行 PDF 预览操作
        PFO.pdf_preview(project_name, outdir)

    # --------------------------------------------------------------------------------
    # 打印 PyTeXMK 运行时长统计信息
    # --------------------------------------------------------------------------------
    if runtime_dict:  # 如果存在运行时统计信息
        time_print(start_time, runtime_dict)  # 打印编译时长统计

    # --------------------------------------------------------------------------------
    # 检查更新
    # --------------------------------------------------------------------------------
    
    UC.check_for_updates()


if __name__ == "__main__":
    main()

# TODO 添加预编译功能
