"""
PyTeXMK 命令行参数解析模块
"""

# -*- coding: utf-8 -*-
import argparse
import sys
from typing import Any

from rich import print
from rich_argparse import RichHelpFormatter

from pytexmk.check_version import UpdateChecker
from pytexmk.console import get_console
from pytexmk.info_print import magic_comment_desc_table
from pytexmk.language import set_language
from pytexmk.version import __version__, script_name

UC = UpdateChecker(1, 6)
_ = set_language("__main__")


class CustomArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        super().print_help(file)
        print(
            _("\nPyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）\n")
        )
        table = magic_comment_desc_table()
        console = get_console()
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


def build_cli_args(args) -> dict[str, Any]:
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