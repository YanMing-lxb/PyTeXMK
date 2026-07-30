"""终端摘要打印与类别可视化。"""
from __future__ import annotations

import logging
import re as _re
import textwrap
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from .base import LogLevel, ParsedLog

if TYPE_CHECKING:
    from .base import LogEntry

logger = logging.getLogger(__name__)

_RICH_CONSOLE = Console(highlight=False, markup=True, soft_wrap=False)
_ANSI_RE = _re.compile(r"\x1b\[[0-9;]*[mK]")

SUMMARY_TOTAL_LEN = 74

CATEGORY_ORDER = [
    "bibliography",
    "index",
    "glossary",
    "code",
    "graphics",
    "compile",
]

CATEGORY_LABEL: dict[str, str] = {
    "bibliography": "参考文献",
    "index": "索引",
    "glossary": "术语/词汇表",
    "code": "代码执行",
    "graphics": "图形/绘图",
    "compile": "一般编译",
}

IMPORTANCE_LABEL: dict[str, str] = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

_LEVEL_ORDER = ["error", "warning", "info"]

_LEVEL_LOGGER = {
    "error": logger.error,
    "warning": logger.warning,
    "info": logger.info,
}

_LEVEL_TITLE = {
    "error": "错误汇总",
    "warning": "警告汇总",
    "info": "提示汇总",
}

_LEVEL_ANSI = {
    "error": "\033[1;31m",
    "warning": "\033[1;33m",
    "info": "\033[1;34m",
}

_ANSI_RESET = "\033[0m"

_LEVEL_SYMBOL_MARKUP = {
    "error": "[bold red]  [E][/]",
    "warning": "[bold yellow]  [W][/]",
    "info": "[bold blue]  [I][/]",
}

_LEVEL_SEP_STYLE = {
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}


def _wrap_key_block(
    header: str,
    keys: list[str],
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
) -> list[str]:
    """将标题与完整 key 列表按宽度换行输出（兼容旧返回纯字符串）。"""
    if not keys:
        return []
    result: list[str] = [header]
    joined = ", ".join(keys)
    effective_width = width - len(indent)
    wrapped = textwrap.wrap(joined, width=effective_width, break_long_words=False, break_on_hyphens=False)
    for line in wrapped:
        result.append(indent + line)
    return result


def _format_ref_block(
    header: str,
    keys: list[str],
    symbol_style: str,
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
) -> list[str]:
    """返回 rich markup 字符串 list：[+]/[-] header + keys 按宽度换行，keys 用 cyan 样式。"""
    if not keys:
        return []
    symbol = "[+]" if "green" in symbol_style else "[-]"
    header_line = f"[{symbol_style}]{symbol}[/{symbol_style}] [bold]{header}[/]"
    result: list[str] = [header_line]
    sorted_keys = sorted(keys)
    effective_plain_width = width - len(indent)

    wrapped_lines: list[str] = []
    current_plain = ""
    current_rich = ""
    key_idx = 0
    while key_idx < len(sorted_keys):
        k = sorted_keys[key_idx]
        is_last = key_idx == len(sorted_keys) - 1
        sep_plain = ", " if not is_last else ""
        k_rich = f"[cyan]{k}[/]"
        sep_rich = "[dim], [/]" if not is_last else ""

        piece_plain = k + sep_plain
        piece_rich = k_rich + sep_rich

        if len(current_plain) + len(piece_plain) <= effective_plain_width:
            current_plain += piece_plain
            current_rich += piece_rich
            key_idx += 1
        else:
            if current_plain:
                wrapped_lines.append(current_rich)
            if len(k) > effective_plain_width:
                k_trunc = k[: effective_plain_width - 3] + "..."
                wrapped_lines.append(f"[cyan]{k_trunc}[/]")
                key_idx += 1
            current_plain = ""
            current_rich = ""
    if current_plain:
        wrapped_lines.append(current_rich)

    for wl in wrapped_lines:
        result.append(indent + wl)
    return result


def _format_top_cited(key_counts: dict[str, int], top_n: int = 10) -> list[str]:
    """返回 rich markup 字符串 list：TopN 引用排行块，含前后 SUMMARY_TOTAL_LEN 列分隔线。"""
    if not key_counts or top_n <= 0:
        return []
    items = Counter(key_counts).most_common(top_n)
    if not items:
        return []
    sep_line = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
    result: list[str] = [sep_line]
    title_line = f"[bold magenta](*)[/] [bold][参考文献] 引用 Top {top_n}:[/]"
    result.append(title_line)

    max_key_plain = 40
    count_width = 3
    for rank, (key, count) in enumerate(items, 1):
        key_plain = key
        if len(key_plain) > max_key_plain:
            key_plain = key_plain[: max_key_plain - 3] + "..."
        key_padded = key_plain.ljust(max_key_plain)
        rank_str = f"({rank})"
        count_str = str(count).rjust(count_width)
        line = f"    {rank_str} [cyan]{key_padded}[/]  [bold magenta]{count_str}[/] 次引用"
        result.append(line)

    result.append(sep_line)
    return result


def _group_by(
    parsed_logs: list[ParsedLog],
) -> dict[str, dict[str, list[LogEntry]]]:
    result: dict[str, dict[str, list[LogEntry]]] = {}
    for lv in _LEVEL_ORDER:
        result[lv] = {}
        for cat in CATEGORY_ORDER:
            result[lv][cat] = []

    level_map = {
        "error": LogLevel.ERROR,
        "warning": LogLevel.WARNING,
        "info": LogLevel.INFO,
    }

    for plog in parsed_logs:
        category = plog.category if plog.category in CATEGORY_ORDER else "compile"
        for entry in plog.entries:
            for lv_name, lv_enum in level_map.items():
                if entry.level == lv_enum:
                    result[lv_name][category].append(entry)
                    break
    return result


def _format_separator(title: str, style: str, text_len_fn: Callable[[str], int] | None = None) -> str:
    """返回单行居中的 rich markup 字符串，总宽 SUMMARY_TOTAL_LEN，左右 === 填充，标题加粗+style 颜色。"""
    _len = text_len_fn or len
    total_width = SUMMARY_TOTAL_LEN
    title_plain = title
    padding_size = total_width - _len(title_plain) - 2
    left_len = padding_size // 2
    right_len = padding_size - left_len
    left_sep = "=" * left_len
    right_sep = "=" * right_len
    return f"[{style}]{left_sep} {title_plain} {right_sep}[/{style}]"


def _format_entry(entry: LogEntry) -> str:
    """返回纯字符串（不含 ANSI/rich）：file:line --> text。"""
    file_part = entry.file or ""
    if file_part:
        p = Path(file_part)
        try:
            file_part = str(p.relative_to(Path.cwd())).replace("\\", "/")
        except ValueError:
            file_part = p.name
    return f"{file_part}:{entry.line} --> {entry.text}"


def _strip_rich_markup(s: str) -> str:
    """临时去掉 rich markup 标签，用于计算纯文本宽度。"""
    pat = _re.compile(r"\[/?[^\]]+\]")
    return pat.sub("", s)


def print_summary(
    parsed_logs: list[ParsedLog],
    ref_change_report: str | None = None,
    non_quiet: bool = True,
    use_logger: bool = True,
    show_info: bool = False,
    ref_added_keys: list[str] | None = None,
    ref_removed_keys: list[str] | None = None,
    ref_total: int | None = None,
    ref_unchanged: int | None = None,
    ref_key_counts: dict[str, int] | None = None,
    text_len_fn: Callable[[str], int] | None = None,
) -> str:
    """按类别/等级分组打印日志摘要并返回拼接字符串（去 rich 版用于兼容旧调用方）。"""
    _len = text_len_fn or len
    grouped = _group_by(parsed_logs)
    output_lines: list[str] = []

    levels_to_show: list[str] = []
    if non_quiet:
        levels_to_show = ["error", "warning"]
        if show_info:
            levels_to_show.append("info")
    else:
        levels_to_show = ["error"]

    for level in levels_to_show:
        categories_data = grouped[level]
        has_entries = any(categories_data[cat] for cat in CATEGORY_ORDER)
        if not has_entries:
            continue

        sep_markup = _format_separator(_LEVEL_TITLE[level], _LEVEL_SEP_STYLE[level], text_len_fn)
        sep_plain = _strip_rich_markup(sep_markup)
        output_lines.append(sep_plain)
        if use_logger:
            sep_line_old = _format_separator_old(_LEVEL_TITLE[level], _LEVEL_ANSI[level])
            _LEVEL_LOGGER[level](sep_line_old)
        else:
            _RICH_CONSOLE.print(sep_markup)

        for cat in CATEGORY_ORDER:
            entries = categories_data[cat]
            if not entries:
                continue

            label = f"[{CATEGORY_LABEL.get(cat, cat)}]"
            prefix = "[bold #d79921]+--[/] [bold]"
            suffix_part = "[/bold] [bold #d79921]"
            plain_prefix_text = f"+-- {label} "
            plain_prefix_len = _len(plain_prefix_text)
            dashes_count = max(0, SUMMARY_TOTAL_LEN - plain_prefix_len)
            dashes = "-" * dashes_count
            cat_markup = f"{prefix}{label}{suffix_part}{dashes}[/]"
            cat_plain = f"{plain_prefix_text}{dashes}"
            output_lines.append(cat_plain)
            if use_logger:
                _LEVEL_LOGGER[level](cat_plain)
            else:
                _RICH_CONSOLE.print(cat_markup)

            for entry in entries:
                formatted_plain = _format_entry(entry)
                symbol_markup = _LEVEL_SYMBOL_MARKUP[level]
                entry_markup = f"{symbol_markup} {formatted_plain}"
                file_line, _, text_part = formatted_plain.partition(" --> ")
                if text_part:
                    entry_markup = (
                        f"{symbol_markup} {file_line} [bold cyan]-->[/] {text_part}"
                    )
                entry_plain_for_logger = f"  {formatted_plain}"
                output_lines.append(entry_plain_for_logger)
                if use_logger:
                    _LEVEL_LOGGER[level](entry_plain_for_logger)
                else:
                    _RICH_CONSOLE.print(entry_markup)

            cat_bottom_sep_markup = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
            cat_bottom_sep_plain = "-" * SUMMARY_TOTAL_LEN
            output_lines.append(cat_bottom_sep_plain)
            if use_logger:
                _LEVEL_LOGGER[level](cat_bottom_sep_plain)
            else:
                _RICH_CONSOLE.print(cat_bottom_sep_markup)

    if ref_change_report:
        output_lines.append(ref_change_report)
        if use_logger:
            logger.info(ref_change_report)
        else:
            _RICH_CONSOLE.print(ref_change_report)

    if ref_added_keys:
        added_header = f"[参考文献] 新增 {len(ref_added_keys)}:"
        added_block_markup = _format_ref_block(
            added_header,
            sorted(ref_added_keys),
            symbol_style="bold green",
            width=SUMMARY_TOTAL_LEN,
            indent="  ",
        )
        added_block_plain = _wrap_key_block(
            f"[参考文献] 新增 {len(ref_added_keys)}:",
            sorted(ref_added_keys),
            width=SUMMARY_TOTAL_LEN,
            indent="  ",
        )
        for i, line in enumerate(added_block_markup):
            if use_logger:
                logger.info(added_block_plain[i])
            else:
                _RICH_CONSOLE.print(line)
        output_lines.extend(added_block_plain)

    if ref_removed_keys:
        removed_header = f"[参考文献] 移除 {len(ref_removed_keys)}:"
        removed_block_markup = _format_ref_block(
            removed_header,
            sorted(ref_removed_keys),
            symbol_style="bold red",
            width=SUMMARY_TOTAL_LEN,
            indent="  ",
        )
        removed_block_plain = _wrap_key_block(
            f"[参考文献] 移除 {len(ref_removed_keys)}:",
            sorted(ref_removed_keys),
            width=SUMMARY_TOTAL_LEN,
            indent="  ",
        )
        for i, line in enumerate(removed_block_markup):
            if use_logger:
                logger.info(removed_block_plain[i])
            else:
                _RICH_CONSOLE.print(line)
        output_lines.extend(removed_block_plain)

    if ref_total and ref_total > 0:
        total_plain = f"  [参考文献] 共 {ref_total} 篇，未变动 {ref_unchanged or 0} 篇"
        total_markup = f"[bold]  [参考文献] [/]共 {ref_total} 篇，未变动 {ref_unchanged or 0} 篇"
        output_lines.append(total_plain)
        if use_logger:
            logger.info(total_plain)
        else:
            _RICH_CONSOLE.print(total_markup)

    if ref_key_counts and len(ref_key_counts) > 0:
        top_block_markup = _format_top_cited(ref_key_counts, top_n=5)
        for line in top_block_markup:
            plain = _strip_rich_markup(line)
            output_lines.append(plain)
            if use_logger:
                logger.info(plain)
            else:
                _RICH_CONSOLE.print(line)

    return "\n".join(output_lines)


def _format_separator_old(title: str, ansi_color: str) -> str:
    """旧版分隔符，仅用于 use_logger 分支。"""
    sep_len = max(40, len(title) + 8)
    line = "=" * sep_len
    return f"{line}\n{ansi_color}{title}{_ANSI_RESET}\n{line}"


def format_editor_jumps(entries: list[LogEntry]) -> list[str]:
    result: list[str] = []
    for e in entries:
        pathname = Path(str(e.file or '')).name if e.file else ''
        result.append(f"{pathname}:{e.line}: {e.text}")
    return result


def log_editor_jumps(entries: list[LogEntry], logger: logging.Logger | None = None, level: int = logging.INFO) -> None:
    logger = logger or logging.getLogger('pytexmk.pytexlogs')
    sorted_entries = sorted(entries, key=lambda e: (e.level.value, e.file, e.line))
    for e in sorted_entries:
        pathname = Path(str(e.file or '')).name if e.file else ''
        msg = f"{pathname}:{e.line}: {e.text}"
        logger.log(level, msg)


def show_log_entries(entries_or_parsed_logs, use_logger: bool = True, show_info: bool = False, non_quiet: bool = True, text_len_fn: Callable[[str], int] | None = None) -> None:
    parsed_logs: list[ParsedLog]
    if isinstance(entries_or_parsed_logs, list):
        if entries_or_parsed_logs and isinstance(entries_or_parsed_logs[0], ParsedLog):
            parsed_logs = entries_or_parsed_logs
        else:
            parsed_logs = [ParsedLog(entries=entries_or_parsed_logs)]
    elif isinstance(entries_or_parsed_logs, ParsedLog):
        parsed_logs = [entries_or_parsed_logs]
    else:
        parsed_logs = [ParsedLog(entries=[entries_or_parsed_logs])]
    print_summary(
        parsed_logs=parsed_logs,
        use_logger=use_logger,
        non_quiet=non_quiet,
        show_info=show_info,
        ref_change_report=None,
        ref_added_keys=None,
        ref_removed_keys=None,
        ref_total=None,
        ref_unchanged=None,
        ref_key_counts=None,
        text_len_fn=text_len_fn,
    )
