"""PyTeXMK CLI 参数解析模块：CustomArgumentParser / CustomHelpFormatter / parse_args.

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
FilePath     : /PyTeXMK/src/pytexmk/cli_args.py
Description  :
 -----------------------------------------------------------------------
"""

import argparse

from rich import print
from rich.console import Console
from rich_argparse import RichHelpFormatter

from ..language import set_language
from ..ui_messages import magic_comment_desc_table
from ..version import __version__, script_name

_ = set_language("__main__")


class CustomArgumentParser(argparse.ArgumentParser):
    """自定义 ArgumentParser：退出时打印魔法注释说明表与版本检查。"""

    def __init__(self, *args, uc=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.uc = uc

    def exit(self, status=0, message=None):
        """自定义 argparse 退出：帮助时打印魔法注释说明与版本检查。"""
        if status == 0 and message is None:
            print(
                _(
                    "\nPyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）\n"
                )
            )
            table = magic_comment_desc_table()
            console = Console()
            console.print(table)
            if self.uc is not None:
                self.uc.check_for_updates()
        super().exit(status, message)


class CustomHelpFormatter(RichHelpFormatter):
    """自定义 RichHelpFormatter：定制 LaTeXDiff 参数元变量显示。"""

    def _format_args(self, action, default_metavar):
        if action.dest == "LaTeXDiff_compile" or action.dest == "LaTeXDiff":
            return "OLD_FILE NEW_FILE"
        return super()._format_args(action, default_metavar)


def parse_args(uc=None):
    """定义并解析 PyTeXMK 命令行参数，返回 argparse.Namespace。"""
    parser = CustomArgumentParser(
        prog="pytexmk",
        description=_("[i]LaTeX 辅助编译程序  ---- 焱铭[/]"),
        epilog=_(
            "如欲了解魔法注释以及其他详细说明信息请运行 -r 参数，阅读 README 文件。发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues"
        ),
        formatter_class=CustomHelpFormatter,
        add_help=False,
        suggest_on_error=True,
        uc=uc,
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
    parser.add_argument(
        "-h", "--help", action="help", help=_("显示 PyTeXMK 的帮助信息并退出")
    )
    parser.add_argument("-r", "--readme", action="store_true", help=_("显示README文件"))
    meg_engine.add_argument(
        "-p", "--PdfLaTeX", action="store_true", help=_("PdfLaTeX 进行编译")
    )
    meg_engine.add_argument(
        "-x", "--XeLaTeX", action="store_true", help=_("XeLaTeX 进行编译")
    )
    meg_engine.add_argument(
        "-l", "--LuaLaTeX", action="store_true", help=_("LuaLaTeX 进行编译")
    )
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
    parser.add_argument(
        "-dr",
        "--draft",
        action="store_true",
        help=_("启用草稿模式进行编译，提高编译速度 (无图显示)"),
    )
    meg_clean.add_argument(
        "-c", "--clean", action="store_true", help=_("清除所有主文件的辅助文件")
    )
    meg_clean.add_argument(
        "-C",
        "--Clean",
        action="store_true",
        help=_("清除所有主文件的辅助文件（包含根目录）和输出文件"),
    )
    meg_clean.add_argument(
        "-ca",
        "--clean-any",
        action="store_true",
        help=_("清除所有带辅助文件后缀的文件"),
    )
    meg_clean.add_argument(
        "-Ca",
        "--Clean-any",
        action="store_true",
        help=_("清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件"),
    )
    parser.add_argument(
        "-nq",
        "--non-quiet",
        action="store_true",
        help=_("非安静模式运行, 此模式下终端显示日志信息"),
    )
    parser.add_argument(
        "-vb",
        "--verbose",
        action="store_true",
        help=_("显示 PyTeXMK 运行过程中的详细信息"),
    )
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
    parser.add_argument("document", nargs="?", help=_("待编译主文件名"))

    args = parser.parse_args()

    return args
