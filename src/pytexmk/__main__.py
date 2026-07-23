"""
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
 ···························································"Y88P"·····
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2025-07-23 22:30:00 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : PyTeXMK 命令行入口
 -----------------------------------------------------------------------
"""

# -*- coding: utf-8 -*-
import argparse
import datetime
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Dict, Any

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
from pytexmk.info_print import time_count, time_print, print_message, magic_comment_desc_table

# 主要功能模块
from pytexmk.run import RUN, LaTeXDiffRUN
from pytexmk.additional import MoveRemoveOperation, MainFileOperation, PdfFileOperation
from pytexmk.latexdiff import LaTeXDiffTool
from pytexmk.check_version import UpdateChecker
from pytexmk.config import ConfigParser
from pytexmk.compile import CompileLaTeX
from pytexmk.engine_detect import auto_configure
from pytexmk.watcher import PvcMode
from pytexmk.toolchain import ToolchainManager
from pytexmk.log_analysis import LogAnalysis

# 辅助功能
from pytexmk.auxiliary_fun import (
    get_app_path,
    setup_console_encoding,
    setup_signal_handlers,
)
from pytexmk.exceptions import PyTeXMKError

UC = UpdateChecker(1, 6)
_ = set_language("__main__")


class CustomArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        super().print_help(file)
        print(
            _("\nPyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）\n")
        )
        table = magic_comment_desc_table()
        console = Console()
        console.print(table)
        UC.check_for_updates()


class CustomHelpFormatter(RichHelpFormatter):
    def _format_args(self, action, default_metavar):
        if action.dest == "LaTeXDiff_compile" or action.dest == "LaTeXDiff":
            return "OLD_FILE NEW_FILE"
        return super()._format_args(action, default_metavar)


# --------------------------------------------------------------------------------
# 定义命令行参数
# --------------------------------------------------------------------------------
def parse_args():
    parser = CustomArgumentParser(
        prog="pytexmk",
        description=_("[i]LaTeX 辅助编译程序  ---- 焱铭[/]"),
        epilog=_(
            "如欲了解魔法注释以及其他详细说明信息请运行 -r 参数，阅读 README 文件。发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues"
        ),
        formatter_class=CustomHelpFormatter,
        add_help=False,
    )

    meg_clean = parser.add_mutually_exclusive_group()
    meg_engine = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{script_name}: version [i]{__version__}",
        help=_("显示 PyTeXMK 的版本号并退出"),
    )
    parser.add_argument("-h", "--help", action="help", help=_("显示 PyTeXMK 的帮助信息并退出"))
    parser.add_argument("-r", "--readme", action="store_true", help=_("显示README文件"))

    meg_engine.add_argument("-p", "--PdfLaTeX", action="store_true", help=_("PdfLaTeX 进行编译"))
    meg_engine.add_argument("-x", "--XeLaTeX", action="store_true", help=_("XeLaTeX 进行编译"))
    meg_engine.add_argument("-l", "--LuaLaTeX", action="store_true", help=_("LuaLaTeX 进行编译"))
    meg_engine.add_argument("--engine", choices=["xelatex", "lualatex", "pdflatex"], help=_("显式指定 TeX 引擎"))

    parser.add_argument(
        "-d",
        "--LaTeXDiff",
        nargs="*",
        metavar=("OLD_FILE", "NEW_FILE"),
        help=_(
            "使用 LaTeXDiff 进行编译, 生成改动对比文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE'"
        ),
    )
    parser.add_argument(
        "-dc",
        "--LaTeXDiff-compile",
        nargs="*",
        metavar=("OLD_FILE", "NEW_FILE"),
        help=_(
            "使用 LaTeXDiff 进行编译, 生成改动对比文件并编译新文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE'"
        ),
    )
    parser.add_argument("-dr", "--draft", action="store_true", help=_("启用草稿模式进行编译，提高编译速度 (无图显示)"))

    meg_clean.add_argument("-c", "--clean", action="store_true", help=_("清除所有主文件的辅助文件"))
    meg_clean.add_argument(
        "-C", "--Clean", action="store_true", help=_("清除所有主文件的辅助文件（包含根目录）和输出文件")
    )
    meg_clean.add_argument("-ca", "--clean-any", action="store_true", help=_("清除所有带辅助文件后缀的文件"))
    meg_clean.add_argument(
        "-Ca", "--Clean-any", action="store_true", help=_("清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件")
    )

    parser.add_argument("-nq", "--non-quiet", action="store_true", help=_("非安静模式运行, 此模式下终端显示日志信息"))
    parser.add_argument("-vb", "--verbose", action="store_true", help=_("显示 PyTeXMK 运行过程中的详细信息"))
    parser.add_argument(
        "-pr",
        "--pdf-repair",
        action="store_true",
        help=_(
            "尝试修复所有根目录以外的 PDF 文件, 当 LaTeX 编译过程中警告 invalid X X R object 时, 可使用此参数尝试修复所有 pdf 文件"
        ),
    )
    parser.add_argument(
        "-pv",
        "--pdf-preview",
        nargs="?",
        const="preview after compile",
        metavar="FILE_NAME",
        help=_(
            "尝试编译结束后调用 Web 浏览器或者本地 PDF 阅读器预览生成的PDF文件 (如需指定在命令行中指定待编译主文件, 则 -pv 命令, 需放置 document 后面并无需指定参数, 示例: pytexmk main -pv; 如无需在命令行中指定待编译主文件, 则直接输入 -pv 即可, 示例: pytexmk -pv), 如有填写 [dark_cyan]FILE_NAME[/dark_cyan] 则不进行编译打开指定文件 (注意仅支持输出目录下的 PDF 文件, 示例: pytexmk -pv main)"
        ),
    )
    parser.add_argument("-O", "--open", action="store_true", dest="open_pdf", help=_("编译成功后自动打开 PDF 文件预览"))
    parser.add_argument("-n", dest="runs_short", type=int, metavar="N", help=_("固定编译次数（默认2），同 --runs"))
    parser.add_argument("-o", dest="outdir_short", metavar="DIR", help=_("输出目录，同 --outdir"))

    parser.add_argument("--bib", choices=["auto", "bibtex", "biber"], help=_("指定参考文献工具"))
    parser.add_argument("--index", choices=["auto", "makeindex", "xindy"], help=_("指定索引工具"))

    auto_group = parser.add_mutually_exclusive_group()
    auto_group.add_argument("--auto", action="store_true", dest="auto_enable", help=_("启用智能引擎自动判定（默认）"))
    auto_group.add_argument("--no-auto", action="store_false", dest="auto_enable", help=_("禁用智能引擎自动判定"))

    parser.add_argument("--timeout", type=int, metavar="SECONDS", help=_("编译超时时间（默认300秒）"))
    parser.add_argument("--runs", type=int, metavar="N", help=_("固定编译次数（默认2，设为3时包含 bib 编译）"))
    parser.add_argument("--outdir", metavar="DIR", help=_("输出目录（命令行覆盖魔法注释和配置）"))
    parser.add_argument("--auxdir", metavar="DIR", help=_("辅助文件目录"))

    synctex_group = parser.add_mutually_exclusive_group()
    synctex_group.add_argument("--synctex", action="store_true", dest="synctex", help=_("启用 SyncTeX（默认）"))
    synctex_group.add_argument("--no-synctex", action="store_false", dest="synctex", help=_("禁用 SyncTeX"))

    shell_escape_group = parser.add_mutually_exclusive_group()
    shell_escape_group.add_argument(
        "--shell-escape", action="store_true", dest="shell_escape", help=_("启用 -shell-escape（默认）")
    )
    shell_escape_group.add_argument(
        "--no-shell-escape", action="store_false", dest="shell_escape", help=_("禁用 -shell-escape")
    )

    parser.add_argument(
        "--pvc",
        "--continuous",
        action="store_true",
        dest="pvc",
        help=_("启用 PVC 模式（实时文件监听+自动编译），类似 latexmk -pvc"),
    )
    parser.add_argument(
        "--pvc-debounce", type=float, metavar="SECONDS", help=_("PVC 模式文件变更防抖时间（默认1.0秒）")
    )
    parser.add_argument("--pvc-preview", action="store_true", help=_("PVC 模式下编译成功自动打开预览"))

    parser.add_argument("--diff-flatten", action="store_true", help=_("LaTeXDiff 时压平子文件（--flatten）"))
    parser.add_argument("--diff-fast", action="store_true", help=_("LaTeXDiff 使用 --fast 模式"))
    parser.add_argument("--diff-output", metavar="FILE", help=_("LaTeXDiff 输出文件名"))
    parser.add_argument(
        "--diff-style",
        type=int,
        choices=[1, 2],
        help=_("LaTeXDiff 显示风格：1-显示参考文献修改，2-不显示（默认2，非交互模式）"),
    )

    parser.add_argument(
        "--non-interactive", action="store_true", help=_("非交互模式（不询问用户，自动处理，适合 CI/CD）")
    )

    parser.add_argument("document", nargs="?", help=_("待编译主文件名"))

    parser.set_defaults(
        auto_enable=None,
        synctex=None,
        shell_escape=None,
    )

    args = parser.parse_args()

    if args.runs is not None:
        args.run_count = args.runs
    elif args.runs_short is not None:
        args.run_count = args.runs_short
    else:
        args.run_count = None

    if args.outdir is not None:
        args.final_outdir = args.outdir
    elif args.outdir_short is not None:
        args.final_outdir = args.outdir_short
    else:
        args.final_outdir = None

    return args


# --------------------------------------------------------------------------------
# 标准化名称方法
# --------------------------------------------------------------------------------
def standardize_name(compiled_program):
    standard_names = {"xelatex": "XeLaTeX", "pdflatex": "PdfLaTeX", "lualatex": "LuaLaTeX"}
    return standard_names.get(compiled_program.lower(), compiled_program)


def build_cli_args(args) -> Dict[str, Any]:
    """将 argparse 解析结果转为 auto_configure 所需的字典"""
    cli_args = {
        "XeLaTeX": args.XeLaTeX,
        "PdfLaTeX": args.PdfLaTeX,
        "LuaLaTeX": args.LuaLaTeX,
    }
    if args.engine:
        cli_args["program"] = args.engine
    if args.bib:
        cli_args["bib"] = args.bib
    if args.index:
        cli_args["index"] = args.index
    return cli_args


def is_tty() -> bool:
    """检测是否在交互式终端中运行"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def setup_pdf_preview(compiler, args, project_name, outdir, PFO):
    """PDF 预览处理"""
    if args.open_pdf:
        PFO.pdf_preview(project_name, outdir)
    elif args.pdf_preview == "preview after compile":
        PFO.pdf_preview(project_name, outdir)


def handle_clean(
    args, compiler, MRO, project_name, outdir, auxdir, suffixes_out, suffixes_aux, start_time, runtime_dict
):
    """清洁命令处理"""
    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if args.clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件的指令"))
    elif args.Clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令"))
    elif args.clean:
        runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
        runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
        runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, ".")
        runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
        print(_("[bold green]已完成清除所有主文件的辅助文件的指令"))
    elif args.Clean:
        runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
        runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
        runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, ".")
        runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
        runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_("[bold green]已完成清除所有主文件的辅助文件和输出文件的指令"))

    if runtime_dict:
        time_print(start_time, runtime_dict)


def handle_diff(
    args,
    config,
    magic_comments,
    MFO,
    MRO,
    PFO,
    main_files_in_root,
    start_time,
    runtime_dict,
    suffixes_out,
    suffixes_aux,
    outdir,
    auxdir,
):
    """LaTeXDiff 处理（使用新 LaTeXDiffTool）"""
    old_tex_file = "old_file"
    new_tex_file = "new_file"
    diff_tex_file = "LaTeXDiff"

    if config and config.get("latexdiff"):
        latexdiff_config = config["latexdiff"]
        if latexdiff_config.get("old_tex_file"):
            old_tex_file = latexdiff_config["old_tex_file"]
        if latexdiff_config.get("new_tex_file"):
            new_tex_file = latexdiff_config["new_tex_file"]
        if latexdiff_config.get("diff_tex_file"):
            diff_tex_file = latexdiff_config["diff_tex_file"]

    if config and config.get("diff"):
        diff_config = config["diff"]
        if diff_config.get("output"):
            diff_tex_file = diff_config["output"]

    if args.diff_output:
        diff_tex_file = args.diff_output
        if diff_tex_file.endswith(".tex"):
            diff_tex_file = diff_tex_file[:-4]

    diff_mode = None
    if args.LaTeXDiff is not None or args.LaTeXDiff_compile is not None:
        if args.LaTeXDiff is not None:
            diff_mode = "generate_only"
            diff_args = args.LaTeXDiff
        else:
            diff_mode = "generate_and_compile"
            diff_args = args.LaTeXDiff_compile

        if diff_args and len(diff_args) == 2:
            old_tex_file, new_tex_file = diff_args
        elif diff_args and len(diff_args) == 0:
            pass
        else:
            print(_("[bold red]错误: LaTeXDiff 需要指定 0 或 2 个文件参数[/bold red]"))
            return False

    if not old_tex_file or not new_tex_file:
        print(_("[bold red]错误: 请在命令行或配置文件中指定 LaTeXDiff 的新旧 TeX 文件[/bold red]"))
        return False

    if old_tex_file == new_tex_file:
        print(_("[bold red]错误: 不能对同一个文件进行比较[/bold red]"))
        return False

    old_tex_file = MFO.check_project_name(main_files_in_root, old_tex_file, ".tex")
    new_tex_file = MFO.check_project_name(main_files_in_root, new_tex_file, ".tex")

    print_message(_("LaTeXDiff 预处理"), "additional")

    non_interactive = args.non_interactive or not is_tty()
    flatten = args.diff_flatten or (config.get("diff", {}).get("flatten", False) if config else False)
    fast = args.diff_fast or (config.get("diff", {}).get("fast", False) if config else False)

    if non_interactive:
        latex_diff_style = args.diff_style if args.diff_style is not None else 2
    else:
        if args.diff_style is not None:
            latex_diff_style = args.diff_style
        else:
            try:
                latex_diff_style = int(
                    input(
                        _(
                            "请输入 LaTeXDiff 的显示风格：\n"
                            "  1 - 显示参考文献/符号说明的修改\n"
                            "  2 - 不显示参考文献/符号说明的修改\n"
                            "请选择 (1 或者 2): "
                        )
                    )
                )
            except (EOFError, ValueError):
                latex_diff_style = 2

    diff_tool = LaTeXDiffTool()

    if not diff_tool.detect_available():
        print(_("[bold red]错误: 未检测到 latexdiff 命令，请先安装 LaTeXDiff[/bold red]"))
        return False

    try:
        print_message(_("LaTeXDiff 运行"), "running")

        if flatten:
            old_flat = f"{old_tex_file}-flatten"
            new_flat = f"{new_tex_file}-flatten"
            diff_tool.flatten_tex(f"{old_tex_file}.tex", f"{old_flat}.tex")
            diff_tool.flatten_tex(f"{new_tex_file}.tex", f"{new_flat}.tex")
            diff_tool.generate_diff(
                old_file=f"{old_flat}.tex",
                new_file=f"{new_flat}.tex",
                output_file=f"{diff_tex_file}.tex",
                fast=fast,
            )
            try:
                Path(f"{old_flat}.tex").unlink(missing_ok=True)
                Path(f"{new_flat}.tex").unlink(missing_ok=True)
            except Exception:
                pass
        else:
            diff_tool.generate_diff(
                old_file=f"{old_tex_file}.tex",
                new_file=f"{new_tex_file}.tex",
                output_file=f"{diff_tex_file}.tex",
                fast=fast,
            )

        runtime_dict[_("LaTeXDiff 运行")] = 0

        if diff_mode == "generate_and_compile":
            out_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_out]
            aux_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_aux]

            print_message(_("开始预处理命令"), "additional")
            print(_("检测并移动辅助文件到根目录..."))
            runtime_move_aux_root = time_count(MRO.move_specific_files, aux_files, auxdir, ".")
            runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

            compiled_program = standardize_name(config.get("compiled_program", "xelatex")) if config else "XeLaTeX"
            non_quiet = args.non_quiet

            if latex_diff_style == 1:
                LaTeXDiffRUN(
                    runtime_dict,
                    diff_tex_file,
                    compiled_program,
                    out_files,
                    aux_files,
                    outdir,
                    auxdir,
                    non_quiet,
                    args.draft,
                )
            else:
                RUN(
                    runtime_dict,
                    diff_tex_file,
                    compiled_program,
                    out_files,
                    aux_files,
                    outdir,
                    auxdir,
                    non_quiet,
                    args.draft,
                )

            print_message(_("开始后处理"), "additional")
            print(_("移动结果文件到输出目录..."))
            runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)
            runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
            print(_("移动辅助文件到辅助目录..."))
            runtime_move_aux_auxdir = time_count(MRO.move_specific_files, aux_files, ".", auxdir)
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

            if args.open_pdf or args.pdf_preview == "preview after compile":
                PFO.pdf_preview(diff_tex_file, outdir)

    except Exception as e:
        print(_("[bold red]LaTeXDiff 编译出错: ") + str(e))
        return False

    return True


# --------------------------------------------------------------------------------
# 主程序
# --------------------------------------------------------------------------------
def main():
    start_time = datetime.datetime.now()

    setup_console_encoding()
    setup_signal_handlers()

    MFO = MainFileOperation()
    MRO = MoveRemoveOperation()
    PFO = PdfFileOperation()

    args = parse_args()

    non_interactive = args.non_interactive or not is_tty()
    CP = ConfigParser(interactive=not non_interactive)

    verbose = args.verbose
    logger = setup_logger(verbose)

    print(_("PyTeXMK 版本: %(args)s") % {"args": f"[i bold green]{__version__}[/i bold green]\n"})
    print(_("[bold green]PyTeXMK 开始运行...\n"))

    try:
        _main_internal(args, CP, MFO, MRO, PFO, start_time, logger, non_interactive)
    except PyTeXMKError as e:
        console = Console()
        console.print(f"\n[bold red]错误: {e.message}[/bold red]")
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        print(_("\n[bold yellow]用户中断操作[/bold yellow]"))
        sys.exit(130)
    except Exception as e:
        console = Console()
        console.print(f"\n[bold red]未预期的错误: {e}[/bold red]")
        console.print("[yellow]请将以下信息提交到 GitHub Issue 帮助我们改进：[/yellow]")
        traceback.print_exc()
        sys.exit(1)
    finally:
        UC.check_for_updates()


def _main_internal(args, CP, MFO, MRO, PFO, start_time, logger, non_interactive):
    runtime_dict = {}

    suffixes_out = [".pdf", ".synctex.gz"]
    suffixes_aux = [
        ".log",
        ".blg",
        ".ilg",
        ".aux",
        ".bbl",
        ".xml",
        ".toc",
        ".lof",
        ".lot",
        ".out",
        ".bcf",
        ".idx",
        ".ind",
        ".nlo",
        ".nls",
        ".ist",
        ".glo",
        ".gls",
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
        ".run.xml",
    ]

    magic_comments_keys = ["program", "root", "outdir", "auxdir", "bib", "index"]

    if args.readme:
        try:
            app_path = get_app_path()
            readme_path = app_path / "data" / "README.html"

            if readme_path.exists():
                print(_("[bold green]正在打开 README 文件..."))
                logger.info(_("README 本地路径: %(args)s") % {"args": f"file://{readme_path.resolve().as_posix()}"})
                webbrowser.open(f"file://{readme_path.resolve().as_posix()}")
            else:
                logger.error(_("README.html 文件未找到: ") + str(readme_path))
                import time

                time.sleep(60)
        except Exception as e:
            logger.error(_("打开 README 文件出错: ") + str(e))
        return

    logger.info("-" * 70)
    tex_files_in_root = MFO.get_suffix_files_in_dir(".", ".tex")
    main_files_in_root = MFO.find_tex_commands(tex_files_in_root)
    all_magic_comments = MFO.search_magic_comments(main_files_in_root, magic_comments_keys)

    logger.info("-" * 70)
    config_dict = CP.init_config_file()

    default_file = "main"
    compiled_program_display = "XeLaTeX"
    non_quiet = False
    outdir = "./Build/"
    auxdir = "./Auxiliary/"
    pdf_preview_file = None
    auto_detect = True
    timeout = 300
    run_count = 2
    shell_escape = True
    synctex = True

    if config_dict:
        if config_dict.get("default_file"):
            default_file = config_dict["default_file"]
            logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{default_file}")
        if config_dict.get("compiled_program"):
            compiled_program_display = standardize_name(config_dict["compiled_program"])
            logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{compiled_program_display}")
        if config_dict.get("quiet_mode") is not None:
            non_quiet = not config_dict["quiet_mode"]
        if config_dict.get("non_quiet"):
            non_quiet = config_dict["non_quiet"]
        if config_dict.get("folder"):
            folder_config = config_dict["folder"]
            if folder_config.get("outdir"):
                outdir = folder_config["outdir"]
                logger.info(_("通过配置文件设置输出目录为: ") + f"[bold cyan]{outdir}")
            if folder_config.get("auxdir"):
                auxdir = folder_config["auxdir"]
                logger.info(_("通过配置文件设置辅助目录为: ") + f"[bold cyan]{auxdir}")
        if config_dict.get("output"):
            output_config = config_dict["output"]
            if output_config.get("outdir"):
                outdir = output_config["outdir"]
            if output_config.get("auxdir"):
                auxdir = output_config["auxdir"]
        if config_dict.get("engine"):
            engine_config = config_dict["engine"]
            if engine_config.get("auto_detect") is not None:
                auto_detect = engine_config["auto_detect"]
            if engine_config.get("timeout"):
                timeout = engine_config["timeout"]
        if config_dict.get("compilation"):
            comp_config = config_dict["compilation"]
            if comp_config.get("default_run_count"):
                run_count = comp_config["default_run_count"]
            if comp_config.get("shell_escape") is not None:
                shell_escape = comp_config["shell_escape"]
            if comp_config.get("synctex") is not None:
                synctex = comp_config["synctex"]
            if comp_config.get("quiet") is not None:
                non_quiet = not comp_config["quiet"]

    if args.non_quiet:
        non_quiet = True
    if args.final_outdir:
        outdir = args.final_outdir
    if args.auxdir:
        auxdir = args.auxdir
    if args.timeout is not None:
        timeout = args.timeout
    if args.run_count is not None:
        run_count = args.run_count
    if args.shell_escape is not None:
        shell_escape = args.shell_escape
    if args.synctex is not None:
        synctex = args.synctex
    if args.auto_enable is not None:
        auto_detect = args.auto_enable

    if non_quiet:
        logger.info(_("非安静模式运行"))

    if args.pdf_preview and args.pdf_preview != "preview after compile" and not args.document:
        pdf_files_in_outdir = MFO.get_suffix_files_in_dir(outdir, ".pdf")
        pdf_preview_file = MFO.check_project_name(pdf_files_in_outdir, args.pdf_preview, ".pdf")
        PFO.pdf_preview(pdf_preview_file, outdir)
        return

    project_name = ""
    magic_comments = {}
    is_diff_mode = (args.LaTeXDiff is not None) or (args.LaTeXDiff_compile is not None)

    if is_diff_mode:
        pass
    elif not args.readme:
        project_name = MFO.get_main_file(default_file, args.document, main_files_in_root, all_magic_comments)

    if all_magic_comments and project_name:
        for key, values in all_magic_comments.items():
            if key == "root":
                continue
            if project_name in values:
                magic_comments[key] = values[project_name]
                logger.info(_("提取魔法注释: ") + f"{project_name}.tex ==> % !TEX {key} = {values[project_name]}")

    if magic_comments.get("outdir"):
        outdir = magic_comments["outdir"]
        print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get("auxdir"):
        auxdir = magic_comments["auxdir"]
        print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{auxdir}[/bold cyan]")

    if is_diff_mode:
        handle_diff(
            args,
            config_dict,
            magic_comments,
            MFO,
            MRO,
            PFO,
            main_files_in_root,
            start_time,
            runtime_dict,
            suffixes_out,
            suffixes_aux,
            outdir,
            auxdir,
        )
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    if not project_name:
        return

    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]

    if args.clean or args.Clean or args.clean_any or args.Clean_any:
        handle_clean(
            args, None, MRO, project_name, outdir, auxdir, suffixes_out, suffixes_aux, start_time, runtime_dict
        )
        return

    if args.pdf_repair:
        runtime_pdf_repair = time_count(PFO.pdf_repair, project_name, ".", outdir)
        runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    toolchain = ToolchainManager()
    toolchain.detect_all()

    cli_args_for_auto = build_cli_args(args)

    if auto_detect:
        auto_config = auto_configure(
            project_name=project_name,
            cli_args=cli_args_for_auto,
            config=config_dict,
            toolchain_manager=toolchain,
            magic_comments=magic_comments if magic_comments else None,
        )
        selected_engine = auto_config["engine"]
        selected_bib = auto_config["bib_tool"]
        selected_index = auto_config["index_tool"]
        if auto_config["outdir"] and not args.final_outdir and not magic_comments.get("outdir"):
            outdir = auto_config["outdir"]
        if auto_config["auxdir"] and not args.auxdir and not magic_comments.get("auxdir"):
            auxdir = auto_config["auxdir"]
    else:
        if args.XeLaTeX:
            selected_engine = "xelatex"
        elif args.PdfLaTeX:
            selected_engine = "pdflatex"
        elif args.LuaLaTeX:
            selected_engine = "lualatex"
        elif args.engine:
            selected_engine = args.engine
        elif magic_comments.get("program"):
            selected_engine = magic_comments["program"].lower()
        elif config_dict.get("compiled_program"):
            selected_engine = config_dict["compiled_program"].lower()
        else:
            selected_engine = "xelatex"

        if args.bib and args.bib != "auto":
            selected_bib = args.bib
        elif magic_comments.get("bib"):
            selected_bib = magic_comments["bib"]
        else:
            selected_bib = None

        if args.index and args.index != "auto":
            selected_index = args.index
        elif magic_comments.get("index"):
            selected_index = magic_comments["index"]
        else:
            selected_index = "makeindex"

    if args.pvc:
        pvc_preview = args.pvc_preview or args.open_pdf or (args.pdf_preview == "preview after compile")

        compiler_kwargs = {
            "program": selected_engine,
            "bibtex_tool": selected_bib,
            "index_tool": selected_index,
            "outdir": outdir,
            "auxdir": auxdir,
            "run_count": run_count,
            "draft": args.draft,
            "quiet": not non_quiet,
            "shell_escape": shell_escape,
            "synctex": synctex,
            "timeout": timeout,
            "auto_detect": auto_detect,
        }

        pvc = PvcMode(
            project_dir=".",
            project_name=project_name,
            compiler_kwargs=compiler_kwargs,
            auto_open_preview=pvc_preview,
        )
        pvc.start()

        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    print_message(_("开始预处理"), "additional")
    print(_("检测并移动辅助文件到根目录..."))
    runtime_move_aux_root = time_count(MRO.move_specific_files, aux_files, auxdir, ".")
    runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

    compiler = CompileLaTeX(
        project_name=project_name,
        program=selected_engine,
        bibtex_tool=selected_bib,
        index_tool=selected_index,
        outdir=outdir,
        auxdir=auxdir,
        run_count=run_count,
        draft=args.draft,
        quiet=not non_quiet,
        shell_escape=shell_escape,
        synctex=synctex,
        timeout=timeout,
        auto_detect=auto_detect,
    )

    compiler.compile_tex()

    print_message(_("日志分析器"), "additional")
    try:
        log_analysis = LogAnalysis(project_name)
        log_analysis.parse_all()
        log_analysis.view_log()
    except Exception as e:
        logger.warning(_("日志分析失败: ") + str(e))

    print_message(_("开始后处理"), "additional")
    print(_("移动结果文件到输出目录..."))
    runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)
    runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
    print(_("移动辅助文件到辅助目录..."))
    runtime_move_aux_auxdir = time_count(MRO.move_specific_files, aux_files, ".", auxdir)
    runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

    setup_pdf_preview(compiler, args, project_name, outdir, PFO)

    if runtime_dict:
        time_print(start_time, runtime_dict)


if __name__ == "__main__":
    main()
