"""耗时统计与运行时长表格。

``runtime_dict`` 的键一律使用**稳定 ASCII slug**（``latex_1`` / ``detect_aux`` …），
显示名在 ``time_print`` 里翻译：这样 ``--json`` 的 ``timings`` 不随界面语言漂移，
而控制台表格仍然跟着 ``LANG`` 走。新增步骤时只加 slug 与显示名，不要直接把
中文/英文句子当作字典键。
"""

import datetime
import itertools
import logging
import math
import re
import time
import unicodedata
from typing import NamedTuple

from rich import box
from rich.table import Table
from rich.text import Text

from pytexmk.language import set_language
from pytexmk.ui_theme import console

logger = logging.getLogger(__name__)

_ = set_language("timing")

total_len = 78


class Timed(NamedTuple):
    """time_count 的返回值：耗时（秒）、被调函数的返回值、异常（成功为 None）。

    ``seconds`` 始终是真实耗时：异常时不再返回半成品三元组，而是记录日志后
    向外抛出——否则调用方会把 ``None`` 当秒数参与 ``sum()``/格式化，最终以
    TypeError 掩盖真正的失败原因。
    """

    seconds: float
    value: object
    error: Exception | None


def time_count(fun, *args, **kwargs) -> Timed:
    """计时执行 ``fun``；异常照常上抛，只记一条错误日志。"""
    time_start = time.perf_counter()
    try:
        fun_return = fun(*args, **kwargs)
    except Exception as e:
        logger.error(_("执行函数 %(args)s 时出错: ") % {"args": {fun.__name__}} + str(e))
        raise
    return Timed(round(time.perf_counter() - time_start, 4), fun_return, None)


def get_text_len(text: str) -> int:
    """按终端显示宽度计算字符串长度（东亚宽字符算 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1 for ch in text)


#: 固定步骤的 slug → msgid（msgid 在运行时才翻译）
_FIXED_LABELS: dict[str, str] = {
    "detect_aux": "检测辅助文件",
    "detect_state": "编译状态检测",
    "dvipdfmx": "DVIPDFMX 编译",
    "pythontex": "pythontex",
    "bib2gls": "bib2gls 编译",
    "latexdiff": "LaTeXDiff 运行",
    "clear_all_aux_auxdir": "清除所有的辅助文件",
    "clear_aux_auxdir": "清除文件夹内辅助文件",
    "clear_aux_root": "清除根目录内辅助文件",
    "clear_out_outdir": "清除文件夹内输出文件",
    "clear_any_out_outdir": "清除文件夹内输出文件",
    "repair_pdf": "修复 PDF 文件",
    "move_aux_root": "辅助文件->根目录",
    "move_aux_auxdir": "辅助文件->辅助目录",
    "move_out_outdir": "结果文件->输出目录",
    "move_all_root": "全辅助文件->根目录",
}

#: 前缀类 slug：``bib_<engine>`` / ``index_<tool>`` 走 "%(args)s 编译"
_PREFIX_LABELS = ("bib_", "index_")

#: 计入 "LaTeX 编译时长" 的 slug 前缀（外部排版/文献/索引工具，不含 pythontex）
_LATEX_SLUG_PREFIXES = ("latex_", "dvipdfmx", "bib_", "bib2gls", "index_", "latexdiff")

#: 重复工具的单次明细键：``bib_bibtex_1`` / ``index_makeindex_2``。
#: 这些键只用于统计调用次数，不进入合计行，也不参与 LaTeX 时长求和。
_TOOL_DETAIL_PATTERN = re.compile(r"^(bib_|index_)(?P<tool>.+)_(?P<round>\d+)$")


def ordinal(n: int) -> str:
    """1 → 1st / 2 → 2nd / 11 → 11th（编译轮次序数）。"""
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def display_name(slug: str, program: str = "") -> str:
    """把稳定 slug 翻译成当前语言的显示名（未知 slug 原样返回）。"""
    msgid = _FIXED_LABELS.get(slug)
    if msgid is not None:
        return _(msgid)
    if slug == "latex_after_pythontex":
        return _("%(args)s (pythontex 后)") % {"args": program}
    if slug.startswith("latex_") and slug.removeprefix("latex_").isdigit():
        return f"{program} {ordinal(int(slug.removeprefix('latex_')))}".strip()
    for prefix in _PREFIX_LABELS:
        if slug.startswith(prefix):
            return _("%(args)s 编译") % {"args": slug.removeprefix(prefix)}
    return slug


def _is_latex_slug(slug: str) -> bool:
    return slug.startswith(_LATEX_SLUG_PREFIXES) and not _TOOL_DETAIL_PATTERN.match(slug)


def _tool_call_counts(runtime_dict: dict[str, float], program: str) -> dict[str, int]:
    """按工具名统计真实调用次数（重复的 bib/index 由明细键提供）。"""
    counts: dict[str, int] = {}

    def add(name: str) -> None:
        counts[name] = counts.get(name, 0) + 1

    for slug in runtime_dict:
        detail = _TOOL_DETAIL_PATTERN.match(slug)
        if detail:
            add(detail.group("tool"))
        elif slug.startswith("latex_"):
            add(program or "LaTeX")
        elif slug in {"bib2gls", "dvipdfmx", "latexdiff"}:
            add(slug)
    return counts


def time_print(
    start_time,
    runtime_dict: dict[str, float],
    *,
    program: str = "",
    start_perf: float | None = None,
) -> None:
    """打印运行时长统计表（**不修改** 传入的 runtime_dict）。

    ``runtime_dict`` 只保存原始秒数（``--json`` 直接读它），派生项与格式化后的
    文本都存在本地副本里，避免调用方拿到被原地改写成字符串的字典。

    ``start_perf`` 给出时用单调时钟计算总时长；墙钟只用于“跨进程/跨机器”
    的兜底，NTP 校时或夏令时跳变不会污染统计。
    """
    run_time = datetime.datetime.now(tz=datetime.UTC) - start_time
    if start_perf is not None:
        total_seconds = time.perf_counter() - start_perf
    else:
        total_seconds = run_time.total_seconds()
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(total_seconds % 1 * 1000)

    latex_steps = [k for k in runtime_dict if _is_latex_slug(k)]
    latex_seconds = sum(runtime_dict[k] for k in latex_steps)
    python_seconds = max(total_seconds - latex_seconds, 0.0)

    # 显示用的副本：原始步骤 + 三个派生汇总（键为已翻译的显示名）
    rows: dict[str, float] = {
        display_name(k, program): v
        for k, v in runtime_dict.items()
        if not _TOOL_DETAIL_PATTERN.match(k)
    }
    if latex_steps:
        rows[_("LaTeX 编译时长")] = latex_seconds
    rows[_("Python 侧（未细分）")] = python_seconds
    rows[_("PyTeXMK 运行时长")] = total_seconds

    max_whole_digits = max(len(str(int(value or 0))) for value in rows.values())
    formatted = {
        name: f"{float(value or 0):0{max_whole_digits + 5}.4f} s" for name, value in rows.items()
    }

    console.print("\n" + "=" * total_len + "\n")

    table = Table(
        show_header=True,
        header_style="bold dark_orange",
        box=box.ASCII_DOUBLE_HEAD,
        title=_("PyTeXMK 运行时长统计表"),
    )
    for _unused in range(2):
        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(Text(_("运行项目"), justify="center"), style="cyan", justify="left", no_wrap=True)
        table.add_column(_("运行时长"), style="green", justify="center", no_wrap=True)

    names = list(formatted)
    row_num = math.ceil(len(names) / 2)
    # 原表是"左列 1..row_num、右列 row_num+1..end"的列优先排布
    left = names[:row_num]
    right = names[row_num:] + [None] * (row_num - len(names[row_num:]))
    for index, (left_name, right_name) in enumerate(
        itertools.zip_longest(left, right, fillvalue=None), start=1
    ):
        row = [f"{index:02d}", left_name or "", formatted.get(left_name, "")]
        if right_name is None:
            row.extend(["", "", ""])
        else:
            row.extend([f"{index + row_num:02d}", right_name, formatted.get(right_name, "")])
        table.add_row(*row)

    console.print(table)
    console.print(
        _("PyTeXMK 运行时长: ")
        + f"{hours} h {minutes} min {seconds} s {milliseconds} ms ({total_seconds:.3f} s total)"
    )
    counts = _tool_call_counts(runtime_dict, program)
    total_calls = sum(counts.values())
    detail = "、".join(f"{name}×{n}" for name, n in counts.items())
    console.print(
        _("外部工具调用 %(total)s 次（%(detail)s）") % {"total": total_calls, "detail": detail}
    )
