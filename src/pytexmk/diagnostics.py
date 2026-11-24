"""编译失败/成功后的可执行诊断（PyTeXMK 侧展示层）。

它把 PyTeXLogs 的「日志条目 + 可执行建议（hint）」翻译成终端上真正有用的两段：

* 失败时：按 ``[E]`` + ``+-- [分类]`` 分组列出最多 5 条错误，每条后跟
  ``↳ 建议`` 与安装/排查命令，末尾给出日志文件指针，告诉用户“完整日志在哪”。
* 成功时：同一套 ``==== 警告汇总 ====`` + ``+-- [分类]`` 分组版式（PyTeXLogs
  的 ``print_summary``），每个分组最多 3 条，避免几十条 overfull 淹没结论；
  被折叠的条目由库统一给出“还有 N 条”。

为什么单独一个模块：``compile.py`` 里只该有“跑哪个程序”，不该夹杂
终端排版；这里只负责展示，日志解析与建议规则全部由 PyTeXLogs 提供。

``--json`` 模式复用同一次解析结果：``LogSummary.issues`` 带上 ``file``/``line``/
``text``，供编辑器插件或 CI 直接跳到出错行，不必再解析人类可读输出。

PyTeXMK 依赖 ``pytexlogs>=0.6.4``；0.6.4 新增 ``hint_style`` / ``format_footer``，
这里用运行时探测兼容仍装着 0.6.3 的环境（只影响展示，不影响解析）。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pytexmk.language import get_locale_lang, set_language
from pytexmk.timing import get_text_len, total_len
from pytexmk.ui_theme import console

_ = set_language("diagnostics")

logger = logging.getLogger(__name__)

MAX_FAILURE_ERRORS = 5
#: 成功摘要里**每个「等级 × 类别」分组**最多展示的警告条数，交给 PyTeXLogs 的
#: ``print_summary(max_entries=)`` 执行；``None`` 是全量口径，不要改成传 ``None``。
MAX_SUCCESS_WARNINGS = 3
#: ``--json`` 载荷里最多带多少条问题条目；全量请配合 ``--report`` 导出。
MAX_JSON_ISSUES = 20


def _run_pipeline(
    *,
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    write_report: bool = False,
    report_path: str | None = None,
):
    """调用 PyTeXLogs（>=0.6.3）的 ``run_pipeline``；终端打印关闭，摘要由本模块排版。"""
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
    except Exception:
        return "unknown"


def _level_name(entry) -> str:
    """条目等级统一成字符串（``LogLevel`` 与报告里的 ``level`` 字符串通用）。"""
    level = getattr(entry, "level", "info")
    return str(getattr(level, "value", level))


def _severity(entry) -> int:
    """按 PyTeXLogs 的 ``LogLevel.severity`` 取排序键（0 最严重）。

    等级顺序由库统一维护（``ERROR < WARNING < INFO < TYPESET < FONT <
    GRAPHIC < PAGE``），本模块不再自建 level→序号表：0.5 时代的
    ``{"typesetting": 2, "info": 3}`` 与 0.6.1 起的口径正好相反。
    """
    from pytexlogs import level_from_value

    return level_from_value(_level_name(entry)).severity


def _iter_entries(report):
    """遍历报告中的全部条目（按 ``LogLevel.severity``、文件行号排序）。"""
    rows = []
    for tool in getattr(report, "tool_results", []) or []:
        for entry in getattr(tool, "entries", []) or []:
            rows.append((_severity(entry), entry, tool))
    rows.sort(
        key=lambda row: (
            row[0],
            str(getattr(row[1], "file", "")),
            int(getattr(row[1], "line", 0) or 0),
        )
    )
    return rows


def _tool_name(tool) -> str | None:
    """取条目所属工具名，用于把 hint 限定在该工具的提示表内。"""
    return getattr(tool, "tool_name", None) or None


def _hint_language() -> str:
    """跟随终端 locale：中文环境给中文建议，其他环境给英文建议。"""
    return "zh" if get_locale_lang().startswith("zh") else "en"


def _entry_hint(entry, *, jobname: str, root_file: str | None, tool_name: str | None = None):
    """按条目取 PyTeXLogs 建议，并把 jobname/主文件上下文填进命令。

    ``tool_name`` 传给 0.6.2 的作用域参数：同一条文本在不同工具下含义不同
    （Biber 的 ``WARN -`` 不该命中 LaTeX 警告规则），不传会退化成全库匹配。
    """
    from pytexlogs import hint_for_entry

    return hint_for_entry(
        entry,
        jobname=jobname,
        root_file=root_file,
        language=_hint_language(),
        tool_name=tool_name,
    )


def _parsed_logs(entries) -> list:
    """把条目按工具分组，转成 PyTeXLogs 摘要渲染器要的 ``ParsedLog``。

    ``_iter_entries`` 返回的是 ``ToolResultReport`` 里的字符串等级条目；摘要
    渲染按 ``LogLevel`` 枚举归组，所以这里统一过一次 ``level_from_value``。
    成功摘要与失败摘要共用这一份转换：两条路径的差别只在挑哪些条目、折叠多少。
    """
    from pytexlogs import LogEntry, ParsedLog, level_from_value

    logs: list = []
    by_tool: dict[int, Any] = {}
    for _rank, entry, tool in entries:
        key = id(tool)
        parsed = by_tool.get(key)
        if parsed is None:
            parsed = ParsedLog(
                tool_name=_tool_name(tool) or "",
                category=getattr(tool, "category", "") or "compile",
                importance=getattr(tool, "importance", "low") or "low",
                source_path=str(getattr(tool, "source_path", "") or ""),
            )
            by_tool[key] = parsed
            logs.append(parsed)
        parsed.entries.append(
            LogEntry(
                level=level_from_value(_level_name(entry)),
                file=str(getattr(entry, "file", "") or ""),
                line=int(getattr(entry, "line", 0) or 0),
                text=str(getattr(entry, "text", "") or ""),
                error_pos_text=str(getattr(entry, "error_pos_text", "") or ""),
            )
        )
    return logs


def _print_groups(
    entries,
    *,
    jobname: str,
    root_file: str | None,
    max_entries: int | None = None,
) -> None:
    """用 PyTeXLogs 的 ``==== 汇总 ====`` + ``+-- [分类]`` 版式打印条目。

    宽度显式传 ``total_len``（PyTeXMK 自己的横幅宽度）：0.6.3 起摘要版式支持
    ``width=``，不传就退回库默认的 74 列，会和本程序 78 列的分隔线错位。
    ``max_entries`` 是**每个「等级 × 类别」分组**的上限（库的口径），``None``
    表示全量；折叠行与“还有 N 条”都由库自己排版，调用方不要再手写一份。
    """
    from pytexlogs import print_summary

    # 0.6.4 起 hint 默认 brief（一行说明，不带命令）；旧版没有该参数，
    # 仍按原文案输出，避免为了一个展示细节把依赖锁死。
    summary_kwargs: dict[str, Any] = {}
    has_footer = _has_pytexlogs_footer()
    if has_footer:
        summary_kwargs["hint_style"] = "brief"
        # 页脚由本模块统一打印：库返回的是中文 msgid，需经 PyTeXMK 的
        # 翻译目录才能在 ``--lang en`` 下正确显示，因此关掉库内打印。
        summary_kwargs["show_footer"] = False
    print_summary(
        _parsed_logs(entries),
        use_logger=False,
        non_quiet=True,
        show_hints=True,
        jobname=jobname,
        root_file=root_file,
        text_len_fn=get_text_len,
        language=_hint_language(),
        width=total_len,
        max_entries=max_entries,
        **summary_kwargs,
    )


def _has_pytexlogs_footer() -> bool:
    """0.6.4 才导出 ``format_footer``；旧版返回 False，调用方退回原行为。"""
    try:
        from pytexlogs import format_footer  # noqa: F401
    except ImportError:
        return False
    return True


def _print_footer(*, has_errors: bool) -> None:
    """打印 pytexlogs 的统一页脚（文案由库提供，翻译由本程序负责）。"""
    from pytexlogs import format_footer

    text = format_footer(has_errors=has_errors)
    if not str(get_locale_lang() or "").lower().startswith("zh"):
        # diagnostics 没有独立翻译目录，这里只对页脚做最小英文回退，
        # 避免中文摘要里混进一行英文或英文摘要里混进一行中文。
        text = (
            "Next: fix the ERRORs above (jump by file:line), then rerun; if only "
            "typesetting/font warnings remain and the PDF is fine, you can continue."
            if has_errors
            else "Next: check the warnings above by file:line; if only typesetting/font "
            "warnings remain and the PDF is fine, you can continue."
        )
    console.print("[dim]" + text + "[/dim]")


def _print_failure_groups(entries, *, jobname: str, root_file: str | None) -> None:
    """失败摘要：调用方已截到 ``MAX_FAILURE_ERRORS``，这里不再二次折叠。"""
    _print_groups(entries, jobname=jobname, root_file=root_file)


def _pytexlogs_command(subcmd: str, log_path: Path | str, *options: str) -> str:
    """拼一条**真的能执行**的 PyTeXLogs 命令。

    PyTeXLogs（>=0.6.3）接受裸路径（等价于隐式 ``check``），但 ``--format`` /
    ``--max-entries`` 只挂在 ``export`` / ``summary`` 子命令上；为了让用户复制后
    直接可跑，这里始终显式写出子命令。日志路径含空格时加引号，保证可粘贴。
    """
    path = str(log_path)
    if any(ch in path for ch in " \t"):
        path = f'"{path}"'
    return " ".join(["pytexlogs", subcmd, path, *options])


def _entry_issue(
    entry,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    tool_name: str | None = None,
) -> dict[str, Any]:
    """把一条日志条目压成 ``--json`` 里的最小定位信息。

    ``text`` 压成单行：JSON 消费方（编辑器插件/CI 注释）按一行渲染，
    多行原样塞进去只会让 ``file:line: text`` 被拆散。
    ``rule_id`` 是 PyTeXLogs 0.6.2 给机器消费方的稳定规则标识（文案会变、id 不变），
    没命中任何规则时不写该键，保持旧载荷形态。
    """
    text = " ".join(str(getattr(entry, "text", "") or "").split())
    issue = {
        "level": _level_name(entry),
        "file": str(getattr(entry, "file", "") or ""),
        "line": int(getattr(entry, "line", 0) or 0),
        "text": text,
    }
    if jobname:
        hint = _entry_hint(
            entry,
            jobname=jobname,
            root_file=root_file,
            tool_name=tool_name,
        )
        rule_id = getattr(hint, "rule_id", "") if hint is not None else ""
        if rule_id:
            issue["rule_id"] = rule_id
    return issue


def report_failure(
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    *,
    write_report: bool = False,
    report_path: str | None = None,
) -> LogSummary:
    """编译失败时打印「错误 + 建议 + 日志指针」，同时返回可供 ``--json`` 用的计数与条目。"""
    available = log_readable(jobname, auxdir)
    try:
        report = _run_pipeline(
            jobname=jobname,
            auxdir=auxdir,
            root_file=root_file,
            translate_fn=translate_fn,
            write_report=write_report,
            report_path=report_path,
        )
    except Exception:
        logger.debug("失败诊断生成失败", exc_info=True)
        console.print("[red]" + _("无法生成失败诊断，请直接查看日志: ") + f"{auxdir}/{jobname}.log[/red]")
        return LogSummary(available=False, source="unavailable")

    entries = [row for row in _iter_entries(report) if _level_name(row[1]) == "error"]
    summary = LogSummary(
        errors=len(entries),
        issues=[
            _entry_issue(
                entry,
                jobname=jobname,
                root_file=root_file,
                tool_name=_tool_name(tool),
            )
            for _rank, entry, tool in entries[:MAX_JSON_ISSUES]
        ],
    )
    summary.available = available
    summary.source = "log" if available else "unavailable"
    _apply_report_status(summary, report)
    log_path = Path(auxdir) / f"{jobname}.log"
    if entries:
        console.print("[bold red]" + _("编译失败，发现 %(n)s 个错误") % {"n": len(entries)} + "[/bold red]")
        _print_failure_groups(entries[:MAX_FAILURE_ERRORS], jobname=jobname, root_file=root_file)
        if len(entries) > MAX_FAILURE_ERRORS:
            console.print(
                "  [dim]"
                + _("… 还有 %(n)s 个错误（用 %(cmd)s 查看全部）")
                % {
                    "n": len(entries) - MAX_FAILURE_ERRORS,
                    "cmd": _pytexlogs_command("export", log_path, "--format", "json"),
                }
                + "[/dim]"
            )
    else:
        console.print("[bold red]" + _("编译失败，但日志里没有解析出 error 条目") + "[/bold red]")
        if _log_looks_truncated(log_path):
            # 日志停在半页、既没 error 也没 "Output written"，多半是引擎在写出
            # PDF 之前被结束了（临时目录不可写、PDF 被阅读器占用、进程被终止）。
            console.print(
                "[yellow]"
                + _("日志在写出 PDF 前就结束了，编译进程可能被中断（临时目录不可写、PDF 被占用或进程被结束）")
                + "[/yellow]"
            )

    console.print("[dim]" + _("完整日志: ") + str(log_path) + "[/dim]")
    console.print(
        "[dim]"
        + _("排查入口: ")
        + _pytexlogs_command("check", log_path, "--open")
        + "[/dim]"
    )
    if entries and _has_pytexlogs_footer():
        _print_footer(has_errors=True)
    return summary


def _log_looks_truncated(log_path: Path, *, tail_bytes: int = 8192) -> bool:
    """判断日志是否停在"已经排出第一页、但没有收尾"的中间状态。

    正常结束的日志一定有 ``Output written on ...``；只有 ``[1`` 却没有这一行，
    说明引擎是在写出 PDF 时被结束的，这是"日志里没有 error"的真正原因。
    """
    try:
        with log_path.open("rb") as fh:
            total = log_path.stat().st_size
            fh.seek(max(0, total - tail_bytes))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    return "[1" in tail and "Output written on" not in tail


@dataclass
class LogSummary:
    """一次成功摘要的计数结果（``--fail-on`` 需要按级别区分）。"""

    errors: int = 0
    warnings: int = 0
    typesetting: int = 0
    #: ``--json`` 用的条目级定位（最多 ``MAX_JSON_ISSUES`` 条，error 在前）
    issues: list[dict[str, Any]] = field(default_factory=list)
    #: PyTeXLogs 实际写出的报告路径；写入失败时为 ``None``（0.6.2 的
    #: ``write_report`` 失败不再抛异常，而是回传 ``None`` + ``_report_write_error``）。
    report_path: str | None = None
    #: 报告写盘失败原因（``TypeError: ...`` 之类），成功时为 ``None``。
    report_error: str | None = None
    #: 本次诊断是否真的读到了可用日志。日志缺失/为空/解析异常时为 ``False``，
    #: 此时所有计数都是 0，但**不代表构建无警告**——门禁与缓存必须据此拒绝放行。
    available: bool = True
    #: 诊断来源：``log`` = 现场解析；``unavailable`` = 日志不可用；``none`` = 未请求。
    source: str = "log"

    @property
    def warn_total(self) -> int:
        """警告 + 排版提示，仅用于判断"要不要打印摘要"。

        ``--fail-on`` 的判定请分别看 ``warnings`` / ``typesetting``：0.6.0 起
        TYPESET 明确是"提示"，不再计入 ``--fail-on warning``。
        """
        return self.warnings + self.typesetting


def log_readable(jobname: str, auxdir: str | Path) -> bool:
    """``<auxdir>/<jobname>.log`` 是否存在且可读（非空）。

    缓存复用与日志分析的前置条件：日志缺失时 PyTeXLogs 只会返回全零摘要，
    若把它当成“无警告”就会漏报真实的警告 / 错误。
    """
    path = Path(auxdir) / f"{jobname}.log"
    try:
        if not path.is_file() or path.stat().st_size <= 0:
            return False
        with path.open("rb") as handle:
            handle.read(1)
    except OSError:
        return False
    return True


class ReportWriteError(OSError):
    """无法持久化诊断 JSON。"""


def generate_report_from_latest_log(
    auxdir: str | Path,
    jobname: str,
    root_file: str | None = None,
) -> tuple[Path | None, str | None]:
    """从最近一次编译日志生成 PyTeXLogs 默认 JSON 报告（不触发编译）。

    返回 ``(JSON 路径, 失败原因)``。日志不存在或解析失败时返回原因，
    写盘失败时抛出 ``ReportWriteError``。
    """
    log_path = Path(auxdir) / f"{jobname}.log"
    if not log_readable(jobname, auxdir):
        return None, f"未找到可读的编译日志: {log_path}"
    try:
        report = _run_pipeline(
            jobname=jobname,
            auxdir=str(auxdir),
            root_file=root_file,
            translate_fn=set_language("diagnostics"),
            write_report=True,
        )
    except OSError as exc:
        raise ReportWriteError(f"{type(exc).__name__}: {exc}") from exc
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

    custom = getattr(report, "custom_fields", {}) or {}
    path = custom.get("_report_path") or None
    if not path:
        if error := custom.get("_report_write_error"):
            raise ReportWriteError(error)
        return None, "报告未生成"
    return Path(path), None


def _apply_report_status(summary: LogSummary, report) -> LogSummary:
    """把 ``run_pipeline`` 报告里的写盘结果抄到 ``LogSummary``。

    0.6.2 起写盘失败不抛异常：成功路径塞 ``custom_fields["_report_path"]``，
    失败路径塞 ``_report_write_error``。调用方必须据此决定是否向用户
    宣称"报告已生成"，不能再凭自己算出的默认路径。
    """
    custom = getattr(report, "custom_fields", {}) or {}
    summary.report_path = custom.get("_report_path") or None
    summary.report_error = custom.get("_report_write_error") or None
    return summary


def report_summary(
    jobname: str,
    auxdir: str,
    root_file: str | None,
    translate_fn=None,
    *,
    write_report: bool = False,
    report_path: str | None = None,
) -> LogSummary:
    """编译成功后用 PyTeXLogs 的分组版式报警告；返回按级别统计的条目数量。

    版式与失败摘要一致（``==== 警告汇总 ====`` + ``+-- [分类]`` + ``↳ 建议``），
    只是每个分组最多 ``MAX_SUCCESS_WARNINGS`` 条，避免几十条 overfull 淹没结论。
    排版提示仍只给一行计数，不展开成组（它们不是需要用户动手的问题）。
    """
    available = log_readable(jobname, auxdir)
    try:
        report = _run_pipeline(
            jobname=jobname,
            auxdir=auxdir,
            root_file=root_file,
            translate_fn=translate_fn,
            write_report=write_report,
            report_path=report_path,
        )
    except Exception:
        logger.debug("成功摘要生成失败", exc_info=True)
        return LogSummary(available=False, source="unavailable")

    rows = _iter_entries(report)
    errors = [row for row in rows if _level_name(row[1]) == "error"]
    warnings = [row for row in rows if _level_name(row[1]) == "warning"]
    typesetting = [row for row in rows if _level_name(row[1]) == "typesetting"]
    counts = LogSummary(errors=len(errors), warnings=len(warnings), typesetting=len(typesetting))
    # 没有日志时计数必然全零：此时必须让调用方看到 available=False，
    # 否则 --fail-on / --report 会把“读不到诊断”当成“没有警告”。
    counts.available = available
    counts.source = "log" if available else "unavailable"
    counts.issues = [
        _entry_issue(
            entry,
            jobname=jobname,
            root_file=root_file,
            tool_name=_tool_name(tool),
        )
        for _rank, entry, tool in (errors + warnings)[:MAX_JSON_ISSUES]
    ]
    _apply_report_status(counts, report)
    if not counts.warn_total:
        return counts
    log_path = Path(auxdir) / f"{jobname}.log"
    if warnings:
        _print_groups(
            warnings,
            jobname=jobname,
            root_file=root_file,
            max_entries=MAX_SUCCESS_WARNINGS,
        )
        if len(warnings) > MAX_SUCCESS_WARNINGS:
            # 折叠行由库按分组给出“还有 N 条”，这里只补一条可直接复制执行的命令：
            # 库的提示是 ``--max-entries 0``，不带上 ``pytexlogs summary <log>``
            # 用户并不知道该对哪份日志执行。
            console.print(
                "  [dim]"
                + _("完整摘要: %(cmd)s")
                % {"cmd": _pytexlogs_command("summary", log_path, "--max-entries", "0")}
                + "[/dim]"
            )
    if typesetting:
        console.print(
            "  [dim]"
            + _("另有 %(n)s 条排版提示（多为 Overfull/Underfull box）") % {"n": len(typesetting)}
            + "[/dim]"
        )
    if _has_pytexlogs_footer():
        # 页脚必须排在所有分组/折叠命令之后，作为整段摘要的最后一句。
        _print_footer(has_errors=False)
    return counts
