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
import sys

from rich_argparse import RichHelpFormatter

from ..language import set_language
from ..ui_messages import magic_comment_desc_table
from ..ui_theme import console
from ..version import __version__, script_name

_ = set_language("cli_args")


class CustomArgumentParser(argparse.ArgumentParser):
    """自定义 ArgumentParser：帮助页退出时打印魔法注释说明表。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._help_requested = False

    def print_help(self, file=None):
        # 标记"这次 exit 是 -h 触发的"：-v/--version 也走 exit(0)，
        # 但打印魔法注释表只应在帮助页出现（否则 `pytexmk --version`
        # 会先刷一屏表，既慢又答非所问）。
        self._help_requested = True
        super().print_help(file)

    def exit(self, status=0, message=None):
        """自定义 argparse 退出：帮助时打印魔法注释说明。"""
        if status == 0 and message is None and self._help_requested:
            console.print(
                _(
                    "\n魔法注释：只扫描每个主文件的前 50 行，可指定编译引擎、"
                    "根文件、输出目录和辅助目录。\n"
                )
            )
            table = magic_comment_desc_table()
            console.print(table)
        super().exit(status, message)


class CustomHelpFormatter(RichHelpFormatter):
    """自定义 RichHelpFormatter：固定帮助页宽度，避免跟随超宽终端拉伸。"""

    def __init__(
        self,
        prog,
        indent_increment=2,
        max_help_position=28,
        width=96,
        **kwargs,
    ):
        super().__init__(
            prog,
            indent_increment=indent_increment,
            max_help_position=max_help_position,
            width=width,
            **kwargs,
        )

    def _format_args(self, action, default_metavar):
        if action.dest == "LaTeXDiff_compile" or action.dest == "LaTeXDiff":
            return "OLD_FILE NEW_FILE"
        return super()._format_args(action, default_metavar)


def build_parser():
    """构建 PyTeXMK 参数解析器（供 parse_args 与 shell 补全共用）。"""
    parser = CustomArgumentParser(
        prog="pytexmk",
        description=_("[i]LaTeX 辅助编译程序  ---- 焱铭[/]"),
        epilog=_(
            "提示：运行出错时会直接说明原因与下一步；"
            "问题反馈：https://github.com/YanMing-lxb/PyTeXMK/issues"
        ),
        formatter_class=CustomHelpFormatter,
        add_help=False,
        suggest_on_error=True,
    )

    meg_clean = parser.add_mutually_exclusive_group()
    meg_engine = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{script_name} {__version__}",
        help=_("显示版本并退出"),
    )
    parser.add_argument(
        "-h", "--help", action="help", help=_("显示本帮助并退出")
    )
    parser.add_argument(
        "-r",
        dest="report",
        action="store_true",
        help=_("从最近一次编译日志生成报告（不触发编译）"),
    )
    meg_engine.add_argument(
        "-p", "--PdfLaTeX", action="store_true", help=_("用 PdfLaTeX 编译")
    )
    meg_engine.add_argument(
        "-x", "--XeLaTeX", action="store_true", help=_("用 XeLaTeX 编译")
    )
    meg_engine.add_argument(
        "-l", "--LuaLaTeX", action="store_true", help=_("用 LuaLaTeX 编译")
    )
    parser.add_argument(
        "-d",
        "--LaTeXDiff",
        nargs="?",
        const="",
        metavar="OLD_FILE",
        help=_(
            "生成 LaTeXDiff 对比稿：写 -d OLD NEW；省略文件名时用配置中的 old/new。"
            "两个文件名须紧跟 -d"
        ),
    )
    parser.add_argument(
        "-dc",
        "--LaTeXDiff-compile",
        nargs="?",
        const="",
        metavar="OLD_FILE",
        help=_(
            "生成 LaTeXDiff 对比稿并编译；文件名写法同 -d，省略时用配置中的 old/new"
        ),
    )
    parser.add_argument(
        "-dr",
        "--draft",
        action="store_true",
        help=_("草稿模式：跳过图片加载，编译更快"),
    )
    meg_clean.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help=_("清除当前主文件的辅助文件（仅辅助目录）"),
    )
    meg_clean.add_argument(
        "-C",
        "--Clean",
        action="store_true",
        help=_("清除当前主文件的辅助文件与输出文件（辅助目录 + 根目录）"),
    )
    meg_clean.add_argument(
        "-ca",
        "--clean-any",
        action="store_true",
        help=_("递归清理全项目的辅助文件（不要求唯一主文件）"),
    )
    meg_clean.add_argument(
        "-Ca",
        "--Clean-any",
        action="store_true",
        help=_("递归清理全项目的辅助文件与主文件输出"),
    )
    parser.add_argument(
        "-nq",
        "--non-quiet",
        action="store_true",
        help=_(
            "实时显示 TeX/biber/makeindex 的输出"
        ),
    )
    parser.add_argument(
        "--interaction",
        choices=("nonstopmode", "batchmode", "scrollmode", "errorstopmode"),
        default=None,
        help=_("传给引擎的 -interaction 模式"),
    )
    parser.add_argument(
        "--pass-arg",
        dest="extra_args",
        action="append",
        default=None,
        metavar="ARG",
        help=_("向引擎追加一个参数，可重复（如 --pass-arg=-8bit）"),
    )
    parser.add_argument(
        "--submission-pack",
        "-sp",
        action="store_true",
        help=_("生成期刊投稿包 zip（按 .fls 收集依赖，附全部 .bib，默认不含 .bbl）"),
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help=_("监视源文件并自动重编（Ctrl+C 退出）"),
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help=_("只显示本次编译配置，不编译"),
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help=_("显示合并后的配置（默认 < 用户 < 项目）"),
    )
    parser.add_argument(
        "-A",
        "--all-subprojects",
        action="store_true",
        help=_("编译根配置 \\[subprojects] 中的全部子项目"),
    )
    parser.add_argument(
        "--diff-style",
        choices=("1", "2"),
        default=None,
        help=_("LaTeXDiff 显示风格；非交互默认 2"),
    )
    parser.add_argument(
        "-vb",
        "--verbose",
        action="store_true",
        help=_("显示详细运行信息"),
    )
    parser.add_argument(
        "-pr",
        "--pdf-repair",
        nargs="*",
        default=None,
        metavar="PDF",
        help=_(
            "修复被项目真实引用的 PDF（按 .fls 判定范围）。"
            "不带文件名时只修复被引用的文件；可指定一个或多个 PDF"
        ),
    )
    parser.add_argument(
        "-fr",
        "--force-rebuild",
        action="store_true",
        help=_("忽略构建缓存，强制重新编译"),
    )
    parser.add_argument(
        "-pv",
        "--pdf-preview",
        nargs="?",
        const="preview after compile",
        metavar="FILE_NAME",
        help=_(
            "编译后打开 PDF 预览。指定 FILE_NAME 时只打开该文件（限输出目录），不再编译；"
            "主文件名可写在 document 位置，如 pytexmk main -pv"
        ),
    )
    parser.add_argument(
        "-s",
        "--subproject",
        metavar="NAME",
        help=_("编译根配置 \\[subprojects] 中指定的子项目"),
    )
    parser.add_argument(
        "-ls",
        "--list-subprojects",
        action="store_true",
        help=_("列出并写回根配置的 \\[subprojects] 清单"),
    )
    parser.add_argument(
        "-i", "--init", action="store_true", help=_("生成项目配置 .pytexmkrc（覆盖已有文件）")
    )
    parser.add_argument(
        "-iu",
        "--init-user",
        action="store_true",
        help=_("生成用户配置 ~/.pytexmkrc（覆盖已有文件）"),
    )
    parser.add_argument("document", nargs="?", help=_("待编译主文件名"))

    return parser


def parse_args(argv=None):
    """解析命令行参数，返回 argparse.Namespace。"""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    # `-d OLD NEW`：argparse 只能吃一个（nargs="?"），第二个会被当成 document。
    # 这里补回二元组，避免历史上 `nargs="*"` 把待编译主文件一起吞掉的坑（U1）。
    for attr in ("LaTeXDiff", "LaTeXDiff_compile"):
        value = getattr(args, attr)
        if value is None:
            continue
        if value == "":
            setattr(args, attr, [])
            continue
        if args.document and value:
            setattr(args, attr, [value, args.document])
            args.document = None
        elif value:
            setattr(args, attr, [value])

    return args
