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
import os

from rich import print
from rich.console import Console
from rich_argparse import RichHelpFormatter

from ..language import set_language
from ..ui_messages import magic_comment_desc_table
from ..version import __version__, script_name

_ = set_language("cli_args")


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
            if self.uc is not None and not os.environ.get("PYTEXMK_NO_UPDATE_CHECK"):
                self.uc.check_for_updates()
        super().exit(status, message)


class CustomHelpFormatter(RichHelpFormatter):
    """自定义 RichHelpFormatter：定制 LaTeXDiff 参数元变量显示。"""

    def _format_args(self, action, default_metavar):
        if action.dest == "LaTeXDiff_compile" or action.dest == "LaTeXDiff":
            return "OLD_FILE NEW_FILE"
        return super()._format_args(action, default_metavar)


def build_parser(uc=None):
    """构建 PyTeXMK 参数解析器（供 parse_args 与 shell 补全共用）。"""
    parser = CustomArgumentParser(
        prog="pytexmk",
        description=_("[i]LaTeX 辅助编译程序  ---- 焱铭[/]"),
        epilog=_(
            "退出码：0=成功；1=参数/路径/主文件错误；3=子项目未找到；4=配置文件错误；5=编译失败；6=警告阈值；7=SyncTeX 校验失败；8=投稿包验证失败。\n"
            "如欲了解魔法注释等详细说明请运行 -r 阅读 README；发现 BUG 请更新到最新版本并在 "
            "https://github.com/YanMing-lxb/PyTeXMK/issues 提交 Issue"
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
        version=f"{script_name} {__version__}",
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
        nargs="?",
        const="",
        metavar="OLD_FILE",
        help=_(
            "使用 LaTeXDiff 生成改动对比文件（两个文件名用空格分隔，可写成 -d OLD NEW）；"
            "不带文件名时取配置文件中的 old/new 设置。注意：文件名需紧跟在本参数之后"
        ),
    )
    parser.add_argument(
        "-dc",
        "--LaTeXDiff-compile",
        nargs="?",
        const="",
        metavar="OLD_FILE",
        help=_(
            "使用 LaTeXDiff 生成改动对比文件并编译（两个文件名用空格分隔）；"
            "不带文件名时取配置文件中的 old/new 设置"
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
        "-q",
        "--quiet",
        action="store_true",
        help=_("安静模式运行（覆盖配置文件中的 quiet_mode=false）"),
    )
    parser.add_argument(
        "--native",
        dest="native_build",
        action="store_true",
        default=None,
        help=_("使用 -output-directory 原生目录构建（默认为自动启用，辅助文件不再往返搬运）"),
    )
    parser.add_argument(
        "--no-native",
        dest="native_build",
        action="store_false",
        help=_("关闭原生目录构建，回退到旧的文件搬运方式"),
    )
    parser.add_argument(
        "--shell-escape",
        dest="shell_escape",
        action="store_true",
        default=None,
        help=_("强制开启 -shell-escape（默认 auto：检测到 minted/pythontex/\\write18 才开）"),
    )
    parser.add_argument(
        "--no-shell-escape",
        dest="shell_escape",
        action="store_false",
        help=_("强制关闭 -shell-escape（拒绝执行任意外部命令）"),
    )
    parser.add_argument(
        "--interaction",
        choices=("nonstopmode", "batchmode", "scrollmode", "errorstopmode"),
        default=None,
        help=_("透传 LaTeX 的 -interaction 模式"),
    )
    parser.add_argument(
        "--pass-arg",
        dest="extra_args",
        action="append",
        default=None,
        metavar="ARG",
        help=_("向编译引擎追加一个参数，可重复使用（如 --pass-arg=-8bit）"),
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        metavar="N",
        help=_("额外编译轮次上限（默认 8，即最多 9 次编译）"),
    )
    parser.add_argument(
        "--jobname",
        default=None,
        metavar="NAME",
        help=_("输出文件名（PDF/辅助文件按 NAME 命名；.tex 源文件仍按主文件名）"),
    )
    parser.add_argument(
        "--submission-pack",
        "-sp",
        action="store_true",
        help=_("生成期刊投稿包 zip（按 .fls 收集依赖，并处理 pdflatex 不兼容的 Unicode）"),
    )
    parser.add_argument(
        "--pdflatex-check",
        "-pc",
        action="store_true",
        help=_("只检查论文是否能被仅支持 pdflatex 的期刊系统编译，不实际打包"),
    )
    parser.add_argument(
        "--submit-dir",
        default=None,
        metavar="DIR",
        help=_("投稿包输出目录（默认 ./Submission/）"),
    )
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help=_("跳过编译前静态检查（默认检查缺失 \\end{document}/.bib/图片等）"),
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help=_("体检本机 TeX 工具链（引擎/biber/makeindex/xindy/latexdiff/状态文件）后退出"),
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help=_("监视源文件变化并自动重编译（Ctrl+C 退出；轮询 1s，去抖 400ms）"),
    )
    parser.add_argument(
        "--keep-preamble",
        action="store_true",
        help=_("投稿包里保留原导言区（默认注释 fontspec/unicode-math/ctex 并补 fontenc）"),
    )
    parser.add_argument(
        "--pack-verify",
        action="store_true",
        help=_("生成投稿包后在临时目录用 pdflatex 真编译一次做验证"),
    )
    parser.add_argument(
        "--synctex-check",
        action="store_true",
        help=_("编译后用 synctex 校验正向/反向跳转（编辑器跳转依赖）"),
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=True,
        default=None,
        metavar="PATH",
        help=_("把 PyTeXLogs 诊断报告写成 JSON（默认 Auxiliary/<主文件>.pytexmk-report.json）"),
    )
    parser.add_argument(
        "--fail-on",
        choices=("none", "warning", "error"),
        default="none",
        help=_("警告/错误达到阈值时返回非零退出码（CI 用，默认 none）"),
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help=_("只打印本次编译的有效配置与决策，不编译"),
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help=_("打印合并后的完整配置（默认 < 用户 < 项目）"),
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help=_("校验配置项的键名与类型，发现错误返回非零"),
    )
    parser.add_argument(
        "-A",
        "--all-subprojects",
        action="store_true",
        help=_("依次编译根配置 [subprojects] 中的全部子项目"),
    )
    parser.add_argument(
        "-io",
        "--includeonly",
        metavar="LIST",
        help=_("只编译指定 \\include 章节（逗号分隔，如 01,03）；输出隔离到 partial/ 子目录"),
    )
    parser.add_argument(
        "--include-bib",
        action="store_true",
        help=_("投稿包同时带上 .bib 源文件（默认只带 .bbl）"),
    )
    parser.add_argument(
        "--clean-dry-run",
        action="store_true",
        help=_("配合 -c/-C/-ca/-Ca：只列出将被删除的文件，不真的删除"),
    )
    parser.add_argument(
        "--diff-style",
        choices=("1", "2"),
        default=None,
        help=_("LaTeXDiff 显示风格；缺省且非交互时使用 2（不再阻塞等待输入）"),
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
        "-fr",
        "--force-rebuild",
        action="store_true",
        help=_("强制重新编译, 忽略构建状态中记录的“源文件未改动”判断"),
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
    parser.add_argument(
        "-s",
        "--subproject",
        metavar="NAME",
        help=_(
            "从根配置 \\[subprojects\\] 中选中一个子项目并在其目录编译；可与待编译主文件名共存"
        ),
    )
    parser.add_argument(
        "-ls",
        "--list-subprojects",
        action="store_true",
        help=_(
            "扫描子项目并展示清单；若根 .pytexmkrc 存在则更新 \\[subprojects\\] 段"
            "（仍指向真实路径的手写别名会保留）"
        ),
    )
    parser.add_argument(
        "-i", "--init", action="store_true", help=_("生成根项目 .pytexmkrc 配置文件")
    )
    parser.add_argument(
        "-iu",
        "--init-user",
        action="store_true",
        help=_("生成用户级 ~/.pytexmkrc 配置文件"),
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help=_("配合 -i/-iu 强制覆盖已存在的配置文件")
    )
    parser.add_argument(
        "--completion",
        choices=("bash", "zsh", "fish", "powershell"),
        metavar="SHELL",
        help=_("输出对应 shell 的补全脚本后退出（bash/zsh/fish/powershell）"),
    )
    parser.add_argument("document", nargs="?", help=_("待编译主文件名"))

    return parser


def parse_args(uc=None):
    """解析命令行参数，返回 argparse.Namespace。"""
    args = build_parser(uc).parse_args()

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
