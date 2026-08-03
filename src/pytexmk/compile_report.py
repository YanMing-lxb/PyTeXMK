import logging

from pytexmk.language import set_language
from pytexmk.timing import total_len
from pytexmk.ui_theme import console

logger = logging.getLogger(__name__)

_ = set_language("compile_report")

DIVIDER_CHAR = "-"
DIVIDER_STYLE = "cyan bold"


def standardize_name(compiled_program):
    standard_names = {
        "xelatex": "XeLaTeX",
        "pdflatex": "PdfLaTeX",
        "lualatex": "LuaLaTeX",
    }
    return standard_names.get(compiled_program.lower(), compiled_program)


def print_compile_separator(divider_char: str = DIVIDER_CHAR, style: str = DIVIDER_STYLE) -> None:
    try:
        print()
        console.print(divider_char * total_len, style=style)
    except Exception as e:  # noqa: BLE001
        logger.error(_("打印分隔线时出错: ") + str(e))


ORDER: list[tuple[str, str, tuple[str, str]]] = [
    (_("文献检测"), "bib", (_("参考文献引用计数无变化，参考文献解析稳定"), _("需要额外执行编译以解析生成参考文献"))),
    (_("索引检测"), "idx", (_("索引词汇表内容未变动，索引生成稳定"), _("索引文件存在变动，需要重新编译索引"))),
    (_("目录变化"), "toc", (_("目录条目未发生变更，目录生成稳定"), _("目录内容发生变动，需要重新生成目录"))),
    (_("交叉引用"), "aux", (_("交叉引用锚点未发生变更，引用解析稳定"), _("辅助文件已发生变更，需再次编译解析引用关系"))),
    (_("书签文件"), "out", (_("PDF 书签条目未发生变更，书签生成稳定"), _("PDF 书签信息发生变动，需要重新生成书签"))),
    (_("日志信号"), "log", (_("未检测到需要重编译的 LaTeX 警告信号，本次迭代稳定"), _("日志检测到重编译警告，要求多次迭代编译"))),
]

NAME_WIDTH = 8


def print_compile_report(
    round_index: int,
    next_extra_compilations: int,
    total_compilations: int,
    dims: dict[str, int],
    compiled_program: str = "",
    *,
    prog: str = "",
    reached_limit: bool = False,
    max_extra: int = 10,
) -> None:
    try:
        raw_program = compiled_program if compiled_program else prog
        actual_program = standardize_name(raw_program)

        console.print(
            f"[bold magenta][" + _("检测报告") + "][/bold magenta] "
            f"[yellow](" + _("第") + " " + str(round_index) + " " + _("轮") + ")[/yellow] "
        )

        for name, tag, (stable_msg, unstable_msg) in ORDER:
            val = dims.get(tag, 0)
            if val == 0:
                mark = "[bold green][√][/bold green]"
                detail = f"[green]{stable_msg}[/green]"
            else:
                mark = r"[bold yellow]\[x][/bold yellow]"
                detail = f"[yellow]{unstable_msg}[/yellow]"
            console.print(
                f" [bold cyan]{name:<{NAME_WIDTH}s}[/bold cyan]"
                f"[bold]({tag})[/bold] : {mark} --> {detail}"
            )

        console.print()

        all_zero = all(dims.get(tag, 0) == 0 for _, tag, _ in ORDER)

        if all_zero:
            console.print(
                f"[bold magenta]" + _("结论：") + "[/bold magenta] "
                f"[green]" + _("无需额外执行 %(prog)s 编译。") % {"prog": actual_program} + "[/green]"
            )
            console.print(
                f"[cyan]" + _("本次累计编译总次数：%(total)s 次") % {"total": total_compilations} + "[/cyan]"
            )
        else:
            actual_next = next_extra_compilations
            console.print(
                f"[bold magenta]" + _("结论：") + "[/bold magenta] "
                f"[yellow]" + _("需额外进行 %(next)s 次 %(prog)s 编译。") % {"next": actual_next, "prog": actual_program} + "[/yellow]"
            )

        if reached_limit:
            console.print(
                f"[bold red]" + _("已达 %(max_extra)s 次额外编译安全上限，停止调度。") % {"max_extra": max_extra} + "[/bold red]"
            )
    except Exception as e:  # noqa: BLE001
        logger.error(_("打印编译检测报告时出错: ") + str(e))
