"""编译失败/成功后的可执行诊断（PyTeXMK 侧展示层）。

它把 PyTeXLogs 的「日志条目 + 可执行建议（hint）」翻译成终端上真正有用的两段：

* 失败时：最多 5 条错误，每条 ``file:line`` 后跟一行 ``↳ 建议`` 与安装/排查命令，
  末尾给出日志文件指针，告诉用户“完整日志在哪”。
* 成功时：最多 3 条警告（避免几十条 overfull 淹没结论），并说明还有多少条。

为什么单独一个模块：``compile.py`` 里只该有“跑哪个程序”，不该夹杂
终端排版；这里只负责展示，日志解析与建议规则全部由 PyTeXLogs 提供。

PyTeXMK 依赖 ``pytexlogs>=0.5.0``，因此这里直接使用 0.5 的
``write_report_file`` / ``report_path`` 参数和 ``hint_for_entry`` 上下文 API，
不再做 0.4 的签名探测或参数降级。
"""

import logging
from pathlib import Path

from pytexmk.language import get_locale_lang, set_language

_ = set_language("diagnostics")

logger = logging.getLogger(__name__)

MAX_FAILURE_ERRORS = 5
MAX_SUCCESS_WARNINGS = 3


def _run_pipeline(
    *,
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    write_report: bool = False,
    report_path: str | None = None,
):
    """调用 PyTeXLogs 0.5 的 ``run_pipeline``。"""
    from pytexlogs import run_pipeline

    return run_pipeline(
        jobname=jobname,
        auxdir=auxdir,
        root_file=root_file,
        pytexmk_version=_version_string(),
        ref_tracker_translate_fn=translate_fn,
        print_terminal=False,  # 摘要由本模块排版，避免重复打印
        write_report_file=write_report,
        report_path=report_path,
    )


def _version_string() -> str:
    try:
        from pytexmk.version import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "unknown"


def _iter_entries(report):
    """遍历报告中的全部条目（按 error → warning 优先、文件行号排序）。"""
    rank = {"error": 0, "warning": 1, "typesetting": 2, "info": 3}
    rows = []
    for tool in getattr(report, "tool_results", []) or []:
        for entry in getattr(tool, "entries", []) or []:
            level = getattr(entry, "level", "info")
            level = getattr(level, "value", level)
            rows.append((rank.get(str(level), 3), entry, tool))
    rows.sort(
        key=lambda row: (
            row[0],
            str(getattr(row[1], "file", "")),
            int(getattr(row[1], "line", 0) or 0),
        )
    )
    return rows


def _hint_language() -> str:
    """跟随终端 locale：中文环境给中文建议，其他环境给英文建议。"""
    return "zh" if get_locale_lang().startswith("zh") else "en"


def _entry_hint(entry, *, jobname: str, root_file: str | None):
    """按条目取 PyTeXLogs 建议，并把 jobname/主文件上下文填进命令。"""
    from pytexlogs import hint_for_entry

    return hint_for_entry(
        entry,
        jobname=jobname,
        root_file=root_file,
        language=_hint_language(),
    )


def _entry_line(entry) -> str:
    file = getattr(entry, "file", "") or "(未知文件)"
    line = getattr(entry, "line", 0) or 0
    text = (getattr(entry, "text", "") or "").strip().replace("\n", " ")
    return f"{file}:{line}  {text}"


def _console():
    from pytexmk.ui_theme import console

    return console


def _print_entry(
    entry,
    *,
    jobname: str,
    root_file: str | None,
    marker: str = "✗",
    style: str = "bold red",
) -> None:
    console = _console()
    console.print(f"  [{style}]{marker}[/] {_entry_line(entry)}")
    hint = _entry_hint(entry, jobname=jobname, root_file=root_file)
    if hint is not None and getattr(hint, "text", ""):
        console.print(f"    [dim]↳ {hint.text}[/]")
        for command in getattr(hint, "commands", ()) or ():
            console.print(f"    [dim cyan]$ {command}[/]")


def report_failure(
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    *,
    write_report: bool = False,
    report_path: str | None = None,
) -> None:
    """编译失败时打印「错误 + 建议 + 日志指针」，不返回退出码。"""
    console = _console()
    try:
        report = _run_pipeline(
            jobname=jobname,
            auxdir=auxdir,
            root_file=root_file,
            translate_fn=translate_fn,
            write_report=write_report,
            report_path=report_path,
        )
    except Exception:  # noqa: BLE001  诊断失败不能掩盖真正的编译失败
        logger.debug("失败诊断生成失败", exc_info=True)
        console.print("[red]" + _("无法生成失败诊断，请直接查看日志: ") + f"{auxdir}/{jobname}.log[/red]")
        return

    entries = [row for row in _iter_entries(report) if row[0] == 0]
    if entries:
        console.print("[bold red]" + _("编译失败，发现 %(n)s 个错误") % {"n": len(entries)} + "[/bold red]")
        for _rank, entry, _tool in entries[:MAX_FAILURE_ERRORS]:
            _print_entry(entry, jobname=jobname, root_file=root_file)
        if len(entries) > MAX_FAILURE_ERRORS:
            console.print(
                "  [dim]"
                + _("… 还有 %(n)s 个错误（用 pytexlogs <log> --format json 查看全部）") % {"n": len(entries) - MAX_FAILURE_ERRORS}
                + "[/dim]"
            )
    else:
        console.print("[bold red]" + _("编译失败，但日志里没有解析出 error 条目") + "[/bold red]")

    log_path = Path(auxdir) / f"{jobname}.log"
    console.print("[dim]" + _("完整日志: ") + str(log_path) + "[/dim]")
    console.print(
        "[dim]" + _("排查入口: ") + f"pytexlogs {log_path} --open" + "[/dim]"
    )


def report_success(
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    *,
    write_report: bool = False,
    report_path: str | None = None,
) -> int:
    """编译成功后只报 top-N 警告；返回警告总数（供 --fail-on warning 使用）。"""
    console = _console()
    try:
        report = _run_pipeline(
            jobname=jobname,
            auxdir=auxdir,
            root_file=root_file,
            translate_fn=translate_fn,
            write_report=write_report,
            report_path=report_path,
        )
    except Exception:  # noqa: BLE001
        logger.debug("成功摘要生成失败", exc_info=True)
        return 0

    rows = _iter_entries(report)
    warnings = [row for row in rows if row[0] == 1]
    typesetting = [row for row in rows if row[0] == 2]
    total = len(warnings) + len(typesetting)
    if not total:
        return 0
    if warnings:
        console.print("[yellow]" + _("提示：%(n)s 个警告") % {"n": len(warnings)} + "[/yellow]")
        for _rank, entry, _tool in warnings[:MAX_SUCCESS_WARNINGS]:
            _print_entry(
                entry,
                jobname=jobname,
                root_file=root_file,
                marker="!",
                style="yellow",
            )
        if len(warnings) > MAX_SUCCESS_WARNINGS:
            console.print(
                "  [dim]"
                + _("… 还有 %(n)s 条（pytexmk -nq 或 pytexlogs 可查看全部）") % {"n": len(warnings) - MAX_SUCCESS_WARNINGS}
                + "[/dim]"
            )
    if typesetting:
        console.print(
            "  [dim]"
            + _("另有 %(n)s 条排版提示（多为 Overfull/Underfull box）") % {"n": len(typesetting)}
            + "[/dim]"
        )
    return total
