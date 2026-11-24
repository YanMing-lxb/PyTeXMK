"""PyTeXMK 诊断报告导出：把 PyTeXLogs 生成的 JSON 报告转成 Markdown。

设计约束：

* Markdown 报告**只以 JSON 报告为输入**，不在内存里另起一套解析；
* 不写 Rich 标记，保证 ``.md`` 可直接在编辑器 / GitHub / issue 中阅读；
* 写失败不抛未捕获异常：保留已成功的 JSON，返回结构化失败，由 CLI 打印
  警告并决定退出码 ``9``。
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.file_ops import atomic_write_text
from pytexmk.language import get_locale_lang

#: 报告里等级从重到轻的展示顺序；未知等级排在最后。
_LEVEL_ORDER = ("error", "warning", "typesetting", "info", "font", "graphic", "page")

_LEVEL_LABEL = {
    "error": "错误",
    "warning": "警告",
    "typesetting": "排版提示",
    "info": "信息",
    "font": "字体",
    "graphic": "图形",
    "page": "版面",
}


@dataclass(slots=True)
class ReportExportResult:
    """一次 Markdown 报告导出的可核对结果。"""

    json_path: Path | None = None
    md_path: Path | None = None
    #: 导出过程中缺失的必需文件（JSON 不存在时记录）
    missing: list[str] = field(default_factory=list)
    #: 失败原因；成功时为 ``None``
    error: str | None = None

    @property
    def ok(self) -> bool:
        """JSON 与 Markdown 都已落盘。"""
        return self.error is None and self.md_path is not None and self.json_path is not None


def _hint_language() -> str:
    """跟随终端 locale：中文环境给中文建议，其他环境给英文建议。"""
    return "zh" if get_locale_lang().startswith("zh") else "en"


def _iter_json_entries(data: dict) -> list[dict]:
    """从 JSON 报告里取出全部条目（附加所属工具名）。"""
    rows: list[dict] = []
    for tool in data.get("tool_results") or []:
        tool_name = str(tool.get("tool_name") or "")
        for entry in tool.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item["_tool"] = tool_name
            rows.append(item)
    return rows


def _level_key(level: str) -> int:
    try:
        return _LEVEL_ORDER.index(level)
    except ValueError:
        return len(_LEVEL_ORDER)


def _md_code(value: object) -> str:
    """行内代码；内容自带反引号时用双反引号包裹。"""
    text = " ".join(str(value or "").split()) or "-"
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def _md_cell(value: object) -> str:
    """表格单元格：转义竖线，压缩换行。"""
    text = " ".join(str(value or "").split()) or "-"
    return text.replace("|", "\\|")


def _md_text(value: object) -> str:
    """条目正文：压缩空白，转义会破坏 Markdown 结构的尖括号与 HTML 实体。"""
    text = " ".join(str(value or "").split())
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _hint_for(entry: dict, *, jobname: str, root_file: str) -> object | None:
    try:
        from pytexlogs import LogEntry, hint_for_entry, level_from_value

        return hint_for_entry(
            LogEntry(
                level=level_from_value(str(entry.get("level") or "info")),
                file=str(entry.get("file") or ""),
                line=int(entry.get("line") or 0),
                text=" ".join(str(entry.get("text") or "").split()),
            ),
            jobname=jobname,
            root_file=root_file or None,
            language=_hint_language(),
            tool_name=entry.get("_tool") or None,
        )
    except Exception:
        return None


def _entry_block(entry: dict, *, jobname: str, root_file: str) -> list[str]:
    """一条条目 → Markdown 小节（位置、正文、可选建议与命令）。"""
    file_name = str(entry.get("file") or root_file or jobname)
    line = int(entry.get("line") or 0)
    location = f"{file_name}:{line}" if line else file_name
    text = _md_text(entry.get("text") or "")
    lines = [f"**{_md_code(location)}** — {text}", ""]

    hint = _hint_for(entry, jobname=jobname, root_file=root_file)
    if hint is not None and getattr(hint, "text", None):
        lines.append(f"> **建议**：{_md_text(hint.text)}")
        commands = list(getattr(hint, "commands", ()) or ())
        if commands:
            lines.extend([">", "> ```bash"])
            lines.extend(f"> {command}" for command in commands)
            lines.append("> ```")
        lines.append("")
    return lines


def write_markdown_report_from_json(json_path: str | Path, md_path: str | Path) -> Path:
    """读取 PyTeXLogs 的 JSON 报告，生成 Markdown 报告并返回路径。

    JSON 缺失 / 解析失败 / 写盘失败都会抛出异常，由 :func:`export_report`
    统一转成结构化失败。
    """
    json_file = Path(json_path)
    md_file = Path(md_path)
    with json_file.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"报告顶层必须是 JSON object，实际是 {type(data).__name__}")

    jobname = str(data.get("jobname") or json_file.stem)
    root_file = str(data.get("root_file") or f"{jobname}.tex")
    generated_at = str(data.get("generated_at") or "-")
    auxdir = str(data.get("auxdir") or "-")
    pytexmk_version = str(data.get("pytexmk_version") or "unknown")
    schema_version = data.get("schema_version")

    entries = _iter_json_entries(data)
    grouped: dict[str, list[dict]] = {}
    for entry in entries:
        level = str(entry.get("level") or "info")
        grouped.setdefault(level, []).append(entry)

    total = len(entries)
    lines = [
        f"# PyTeXMK 诊断报告：{_md_cell(jobname)}",
        "",
        "> 由 `pytexmk -r` 读取最近一次编译日志生成；原始数据保留在 "
        f"[同名 `.json` 文件](<{json_file.name}>)。",
        "",
        "| 项目 | 内容 |",
        "| --- | --- |",
        f"| 主文件 | {_md_code(root_file)} |",
        f"| jobname | {_md_code(jobname)} |",
        f"| 辅助目录 | {_md_code(auxdir)} |",
        f"| 生成时间 | {_md_code(generated_at)} |",
        f"| PyTeXMK 版本 | {_md_code(pytexmk_version)} |",
        f"| 报告 schema | {_md_code('-' if schema_version is None else schema_version)} |",
        f"| 条目总数 | {total} |",
        "",
        "## 概览",
        "",
        "| 等级 | 条目数 |",
        "| --- | ---: |",
    ]
    for level in sorted(grouped, key=_level_key):
        lines.append(f"| {_LEVEL_LABEL.get(level, level)} | {len(grouped[level])} |")
    lines.extend([f"| **合计** | **{total}** |", ""])

    if not grouped:
        lines.append("日志里没有解析出任何条目。")
        lines.append("")
    for level in sorted(grouped, key=_level_key):
        label = _LEVEL_LABEL.get(level, level)
        lines.extend([f"## {label}（{len(grouped[level])}）", ""])
        for entry in sorted(
            grouped[level],
            key=lambda item: (
                str(item.get("file") or ""),
                int(item.get("line") or 0),
            ),
        ):
            lines.extend(_entry_block(entry, jobname=jobname, root_file=root_file))

    atomic_write_text(md_file, "\n".join(lines).rstrip() + "\n")
    return md_file


def export_report(json_path: str | Path, md_path: str | Path) -> ReportExportResult:
    """把 JSON 报告导出为 Markdown 报告，返回结构化结果；不吞掉失败原因。"""
    json_file = Path(json_path)
    md_file = Path(md_path)
    result = ReportExportResult(json_path=json_file)

    if not json_file.is_file():
        result.missing.append(str(json_file))
        result.error = f"缺少 JSON 报告: {json_file}"
        return result

    try:
        result.md_path = write_markdown_report_from_json(json_file, md_file)
    except Exception as exc:  # Markdown 失败不能吞掉已经生成的 JSON
        result.error = f"{type(exc).__name__}: {exc}"
        result.missing.append(str(md_file))
        return result

    return result


def print_report_error(result: ReportExportResult) -> None:
    """把导出失败写到 stderr：给人看清路径与原因。"""
    print(f"pytexmk: 报告导出失败: {result.error}", file=sys.stderr)
    for path in result.missing:
        print(f"pytexmk: 缺少/未写入: {path}", file=sys.stderr)
