# -*- coding: utf-8 -*-
"""
log_analysis.py - LaTeX 编译日志分析模块

功能：
1. 解析 LaTeX 编译输出中的错误、警告和排版信息。
2. 支持 BibTeX、Biber、Makeindex、Xindy、Glossaries、Nomencl 日志解析。
3. 提供结构化数据供编译调度器自动判断是否需要重编译。
4. 使用 rich 表格展示错误信息。
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Union

from rich.console import Console
from rich.table import Table
from rich import box

from pytexmk.language import set_language

logger = logging.getLogger(__name__)
_ = set_language("log_analysis")
console = Console()


# ========================
# 日志类型枚举（用于旧 LatexLogParser）
# ========================


class LogType:
    ERROR = "error"
    WARNING = "warning"
    TYPESET = "typesetting"
    INFO = "info"
    FONT = "font"
    GRAPHIC = "graphic"
    PAGE = "page"

    _order = {"error": 0, "warning": 1, "typesetting": 2, "font": 3, "graphic": 4, "page": 5, "info": 6}

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self._order.get(self.value, 7) < self._order.get(getattr(other, "value", other), 7)


# ========================
# 正则表达式定义
# ========================

# 引擎检测
ENGINE_PDFTEX_RE = re.compile(r"This is pdfTeX", re.IGNORECASE)
ENGINE_XETEX_RE = re.compile(r"This is XeTeX", re.IGNORECASE)
ENGINE_LUATEX_RE = re.compile(r"This is LuaTeX", re.IGNORECASE)

# 编译成功检测
OUTPUT_WRITTEN_RE = re.compile(r"Output written on (.+?) \((\d+) page", re.IGNORECASE)
TRANSCRIPT_WRITTEN_RE = re.compile(r"Transcript written on", re.IGNORECASE)

# LaTeX 错误模式
ERROR_BANG_RE = re.compile(r"^!")
ERROR_PDFTEX_RE = re.compile(r"^!pdfTeX error:", re.IGNORECASE)
ERROR_XETEX_RE = re.compile(r"^!XeTeX error:", re.IGNORECASE)
ERROR_LUATEX_RE = re.compile(r"^!Lua(?:La)?TeX error:", re.IGNORECASE)
ERROR_EMERGENCY_STOP_RE = re.compile(r"Emergency stop\.", re.IGNORECASE)
ERROR_FATAL_RE = re.compile(r"Fatal error occurred", re.IGNORECASE)
ERROR_FATAL_ARROW_RE = re.compile(r"==>\s*Fatal error occurred", re.IGNORECASE)
ERROR_CANT_USE_RE = re.compile(r"^You can\'t use", re.IGNORECASE)

# 行号提取
LINE_L_DOT_RE = re.compile(r"l\.(\d+)")
LINE_AT_LINE_RE = re.compile(r"(?:at\s+)?line\s+(\d+)", re.IGNORECASE)
LINE_FILE_COLON_RE = re.compile(r"([^:]+\.tex):(\d+):", re.IGNORECASE)

# 警告检测
WARN_PACKAGE_RE = re.compile(r"^Package\s+(.+?)\s+Warning:", re.IGNORECASE)
WARN_CLASS_RE = re.compile(r"^Class\s+(.+?)\s+Warning:", re.IGNORECASE)
WARN_LATEX_RE = re.compile(r"^LaTeX(?:\s+\S*)?\s+Warning:", re.IGNORECASE)
WARN_PDFTEX_RE = re.compile(r"^pdfTeX warning:", re.IGNORECASE)
WARN_XETEX_RE = re.compile(r"^XeTeX warning:", re.IGNORECASE)
WARN_LUATEX_RE = re.compile(r"^LuaTeX warning:", re.IGNORECASE)

# 未定义引用/引用
UNDEFINED_CITATION_RE = re.compile(r"LaTeX Warning: Citation [`\']([^\'\']+)[\'`]", re.IGNORECASE)
UNDEFINED_REFERENCE_RE = re.compile(r"LaTeX Warning: Reference [`\']([^\'\']+)[\'`]", re.IGNORECASE)
RERUN_TO_GET_RE = re.compile(r"Rerun to get", re.IGNORECASE)

# 缺少文件
NO_FILE_RE = re.compile(r"^No file (.+?)\.$", re.IGNORECASE)

# Overfull/Underfull boxes
OVERFULL_RE = re.compile(r"Overfull", re.IGNORECASE)
UNDERFULL_RE = re.compile(r"Underfull", re.IGNORECASE)

# 加载文件列表
FILE_ENTRY_RE = re.compile(r"\(([^()\s]+\.(?:tex|sty|cls|cfg|def|clo|fd|bbx|cbx|lbx|ldf))", re.IGNORECASE)

# BibTeX 日志模式
BIBTEX_ERROR_RE = re.compile(r"^I found no|^I was expecting|^Too many|^Warning--|^There (?:was|were)", re.IGNORECASE)
BIBTEX_FATAL_RE = re.compile(r"^Fatal error|^Aborted", re.IGNORECASE)

# Biber 日志模式
BIBER_ERROR_RE = re.compile(r"^ERROR", re.IGNORECASE)
BIBER_WARN_RE = re.compile(r"^WARN", re.IGNORECASE)
BIBER_FATAL_RE = re.compile(r"^FATAL", re.IGNORECASE)

# Makeindex 日志模式
MAKEINDEX_BANG_RE = re.compile(r"^!!")
MAKEINDEX_NOTFOUND_RE = re.compile(r"Input index file .* not found", re.IGNORECASE)
MAKEINDEX_ERROR_RE = re.compile(r"\*\*\s*Error", re.IGNORECASE)
MAKEINDEX_WARN_RE = re.compile(r"## Warning", re.IGNORECASE)

# Xindy 日志模式
XINDY_ERROR_RE = re.compile(r"^ERROR:", re.IGNORECASE)
XINDY_WARN_RE = re.compile(r"^WARNING:", re.IGNORECASE)
XINDY_OPEN_RE = re.compile(r"Cannot open|No such file", re.IGNORECASE)
XINDY_FATAL_RE = re.compile(r"FATAL|xindy:.*error", re.IGNORECASE)

# Glossaries 日志 (.glg)
GLG_ERROR_RE = re.compile(r"^!!|^Error|^No file|.*not found", re.IGNORECASE)

# Nomencl 日志 (.nlg)
NLG_ERROR_RE = re.compile(r"^!!|^Error|^No file|.*not found", re.IGNORECASE)

# 旧 LatexLogParser 使用的正则
latex_error_re1 = re.compile(r"^(?:(.*):(\d+):|!)(?: (.+) Error:)? (.+?)$")
latex_error_re2 = re.compile(r"^!(?: (.+) Error:)? (.+?)$")
overfull_box_re = re.compile(r"^(Overfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$")
overfull_box_alt_re = re.compile(r"^(Overfull \\[vh]box \([^)]+\)) detected at line (\d+)$")
underfull_box_re = re.compile(r"^(Underfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$")
underfull_box_alt_re = re.compile(r"^(Underfull \\[vh]box \([^)]+\)) detected at line (\d+)$")
latex_warn_re = re.compile(
    r"^((?:(?:Class|Package|Module) \S+)|LaTeX(?: \S*)?|LaTeX3) (Warning|Info):\s+(.*?)(?: on(?: input)? line (\d+))?(\.|\?)?$"
)
undefined_reference_re = re.compile(
    r"^LaTeX Warning: (Reference|Citation) `(.*?)\' on page \d+ undefined on input line (\d+)\.$"
)
message_line_re = re.compile(r"^l\.(\d+)\s*(.*)$")
file_stack_open_re = re.compile(r"\(([^()\s]+)")
file_stack_close_re = re.compile(r"\)")
missing_char_re = re.compile(r"^\s*(Missing character:.+?!)$")
bib_empty_re = re.compile(r"^Empty `thebibliography\' environment$")


class LogAnalysis:
    """
    LaTeX 日志分析器（新版，基于文件名）

    基于文件名解析各类日志文件（.log, .blg, .ilg, .xlg, .glg, .nlg），
    提供结构化的错误、警告、未定义引用等信息，供编译调度器使用。
    """

    def __init__(self, file_name: str):
        """
        初始化日志分析器

        :param file_name: 基础文件名（不含后缀），如 "main"
        """
        self.base_name = file_name
        base_path = Path(file_name)
        self.log = base_path.with_suffix(".log")
        self.blg = base_path.with_suffix(".blg")
        self.ilg = base_path.with_suffix(".ilg")
        self.xlg = base_path.with_suffix(".xlg")
        self.glg = base_path.with_suffix(".glg")
        self.nlg = base_path.with_suffix(".nlg")
        self.aux = base_path.with_suffix(".aux")
        self.bbl = base_path.with_suffix(".bbl")
        self.ind = base_path.with_suffix(".ind")

        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.undefined_citations: Set[str] = set()
        self.undefined_references: Set[str] = set()
        self.missing_files: Set[str] = set()
        self.overfull_boxes: int = 0
        self.underfull_boxes: int = 0
        self.loaded_files: List[str] = []
        self.compilation_success: bool = False
        self.output_file: Optional[str] = None
        self.pages: int = 0
        self.engine_type: Optional[str] = None

        self._tex_error_count: int = 0
        self._bib_error_count: int = 0
        self._index_error_count: int = 0
        self._warning_count: int = 0
        self._needs_rerun: bool = False
        self._parsed: bool = False

    def parse_all(self) -> "LogAnalysis":
        """
        解析所有日志文件，方便链式调用

        :return: self
        """
        self.errors.clear()
        self.warnings.clear()
        self.undefined_citations.clear()
        self.undefined_references.clear()
        self.missing_files.clear()
        self.loaded_files.clear()
        self.overfull_boxes = 0
        self.underfull_boxes = 0
        self.compilation_success = False
        self.output_file = None
        self.pages = 0
        self.engine_type = None
        self._tex_error_count = 0
        self._bib_error_count = 0
        self._index_error_count = 0
        self._warning_count = 0
        self._needs_rerun = False

        self._parse_logfile()
        self._parse_blgfile()
        self._parse_ilgfile()
        self._parse_xlgfile()
        self._parse_glgfile()
        self._parse_nlgfile()
        self._parsed = True
        return self

    def _read_file_safe(self, path: Path) -> List[str]:
        """安全读取文件，返回行列表"""
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.readlines()
        except Exception as e:
            logger.debug(f"读取 {path} 失败: {e}")
        return []

    def _add_error(
        self, message: str, file: str = "", line: int = 0, level: str = "error", context: str = "", source: str = "tex"
    ):
        """添加错误记录"""
        entry = {
            "file": file,
            "line": line,
            "level": level,
            "message": message.strip(),
            "context": context.strip(),
            "source": source,
        }
        self.errors.append(entry)

    def _add_warning(
        self,
        message: str,
        file: str = "",
        line: int = 0,
        level: str = "warning",
        context: str = "",
        source: str = "tex",
    ):
        """添加警告记录"""
        entry = {
            "file": file,
            "line": line,
            "level": level,
            "message": message.strip(),
            "context": context.strip(),
            "source": source,
        }
        self.warnings.append(entry)
        self._warning_count += 1

    def _extract_line_number(self, line: str, context_lines: List[str] = None) -> int:
        """从行内容中提取行号"""
        match = LINE_L_DOT_RE.search(line)
        if match:
            return int(match.group(1))
        match = LINE_AT_LINE_RE.search(line)
        if match:
            return int(match.group(1))
        if context_lines:
            for ctx in reversed(context_lines[-5:]):
                match = LINE_L_DOT_RE.search(ctx)
                if match:
                    return int(match.group(1))
                match = LINE_AT_LINE_RE.search(ctx)
                if match:
                    return int(match.group(1))
        return 0

    def _extract_filename(self, line: str, context_lines: List[str] = None) -> str:
        """从错误上下文中提取源文件名"""
        match = LINE_FILE_COLON_RE.search(line)
        if match:
            return match.group(1)
        if context_lines:
            for ctx in reversed(context_lines[-5:]):
                match = LINE_FILE_COLON_RE.search(ctx)
                if match:
                    return match.group(1)
        return ""

    def _parse_logfile(self):
        """解析 LaTeX .log 主日志文件"""
        lines = self._read_file_safe(self.log)
        if not lines:
            return

        context_buffer: List[str] = []
        current_error_msg: List[str] = []
        in_error = False
        error_file = ""
        error_line = 0

        for i, line in enumerate(lines):
            raw_line = line.rstrip("\n\r")
            stripped = raw_line.strip()

            if not self.engine_type:
                if ENGINE_PDFTEX_RE.search(raw_line):
                    self.engine_type = "pdflatex"
                elif ENGINE_XETEX_RE.search(raw_line):
                    self.engine_type = "xelatex"
                elif ENGINE_LUATEX_RE.search(raw_line):
                    self.engine_type = "lualatex"

            out_match = OUTPUT_WRITTEN_RE.search(raw_line)
            if out_match:
                self.compilation_success = True
                self.output_file = out_match.group(1).strip().strip('"')
                self.pages = int(out_match.group(2))

            if RERUN_TO_GET_RE.search(raw_line):
                self._needs_rerun = True

            for ref_match in UNDEFINED_CITATION_RE.finditer(raw_line):
                self.undefined_citations.add(ref_match.group(1))

            for ref_match in UNDEFINED_REFERENCE_RE.finditer(raw_line):
                self.undefined_references.add(ref_match.group(1))

            no_file_match = NO_FILE_RE.match(stripped)
            if no_file_match:
                fname = no_file_match.group(1).strip()
                if fname:
                    self.missing_files.add(fname)

            if OVERFULL_RE.search(stripped):
                self.overfull_boxes += 1
                self._add_warning(stripped, source="tex", level="overfull")

            if UNDERFULL_RE.search(stripped):
                self.underfull_boxes += 1
                self._add_warning(stripped, source="tex", level="underfull")

            is_error = False
            error_msg = ""
            if ERROR_BANG_RE.match(stripped):
                is_error = True
                error_msg = stripped[1:].strip()
            elif ERROR_PDFTEX_RE.match(stripped):
                is_error = True
                error_msg = stripped
            elif ERROR_XETEX_RE.match(stripped):
                is_error = True
                error_msg = stripped
            elif ERROR_LUATEX_RE.match(stripped):
                is_error = True
                error_msg = stripped
            elif ERROR_EMERGENCY_STOP_RE.search(stripped):
                is_error = True
                error_msg = "Emergency stop."
            elif ERROR_FATAL_ARROW_RE.search(stripped) or ERROR_FATAL_RE.search(stripped):
                is_error = True
                error_msg = stripped
            elif ERROR_CANT_USE_RE.match(stripped):
                is_error = True
                error_msg = stripped

            if is_error:
                if in_error and current_error_msg:
                    ctx = "\n".join(context_buffer[-10:])
                    self._add_error(
                        " ".join(current_error_msg), file=error_file, line=error_line, context=ctx, source="tex"
                    )
                    self._tex_error_count += 1
                in_error = True
                current_error_msg = [error_msg] if error_msg else [stripped]
                ctx_lines = lines[max(0, i - 5) : i] if i > 0 else []
                error_file = self._extract_filename(raw_line, ctx_lines)
                error_line = self._extract_line_number(raw_line)
                context_buffer = [raw_line]
                continue

            if in_error:
                context_buffer.append(raw_line)
                if stripped and not stripped.startswith(" "):
                    l_match = LINE_L_DOT_RE.search(raw_line)
                    if l_match:
                        error_line = int(l_match.group(1))
                    if error_line == 0:
                        error_line = self._extract_line_number(raw_line)
                    if not error_file:
                        error_file = self._extract_filename(raw_line, context_buffer)

                if stripped == "" or (stripped.startswith("l.") and len(current_error_msg) > 1):
                    if current_error_msg:
                        ctx = "\n".join(context_buffer[-15:])
                        self._add_error(
                            " ".join(current_error_msg), file=error_file, line=error_line, context=ctx, source="tex"
                        )
                        self._tex_error_count += 1
                    in_error = False
                    current_error_msg = []
                    context_buffer = []
                    error_file = ""
                    error_line = 0
                else:
                    if stripped:
                        current_error_msg.append(stripped)
                continue

            warn_msg = None
            if WARN_PACKAGE_RE.match(stripped):
                warn_msg = stripped
            elif WARN_CLASS_RE.match(stripped):
                warn_msg = stripped
            elif WARN_LATEX_RE.match(stripped):
                if "undefined" not in stripped.lower():
                    warn_msg = stripped
            elif WARN_PDFTEX_RE.match(stripped):
                warn_msg = stripped
            elif WARN_XETEX_RE.match(stripped):
                warn_msg = stripped
            elif WARN_LUATEX_RE.match(stripped):
                warn_msg = stripped

            if warn_msg:
                ctx_lines = lines[max(0, i - 5) : i] if i > 0 else []
                wfile = self._extract_filename(raw_line, ctx_lines)
                wline = self._extract_line_number(raw_line, ctx_lines)
                self._add_warning(warn_msg, file=wfile, line=wline, source="tex")

            for fmatch in FILE_ENTRY_RE.finditer(raw_line):
                fname = fmatch.group(1)
                if fname not in self.loaded_files:
                    self.loaded_files.append(fname)

        if in_error and current_error_msg:
            ctx = "\n".join(context_buffer[-15:]) if context_buffer else ""
            self._add_error(" ".join(current_error_msg), file=error_file, line=error_line, context=ctx, source="tex")
            self._tex_error_count += 1

    def _parse_blgfile(self):
        """解析 BibTeX/Biber .blg 日志文件"""
        lines = self._read_file_safe(self.blg)
        if not lines:
            return

        is_biber = False
        if lines:
            first_lines = "".join(lines[:5])
            if "Biber" in first_lines or "biber" in first_lines.lower():
                is_biber = True

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if is_biber:
                if BIBER_FATAL_RE.match(stripped):
                    self._add_error(stripped, source="biber", level="fatal")
                    self._bib_error_count += 1
                elif BIBER_ERROR_RE.match(stripped):
                    self._add_error(stripped, source="biber")
                    self._bib_error_count += 1
                elif BIBER_WARN_RE.match(stripped):
                    self._add_warning(stripped, source="biber")
            else:
                if BIBTEX_FATAL_RE.match(stripped):
                    self._add_error(stripped, source="bibtex", level="fatal")
                    self._bib_error_count += 1
                elif BIBTEX_ERROR_RE.match(stripped):
                    if stripped.startswith("Warning--"):
                        self._add_warning(stripped, source="bibtex")
                    else:
                        self._add_error(stripped, source="bibtex")
                        self._bib_error_count += 1

    def _parse_ilgfile(self):
        """解析 Makeindex .ilg 日志文件"""
        lines = self._read_file_safe(self.ilg)
        if not lines:
            return

        is_xindy = False
        for line in lines[:5]:
            if "xindy" in line.lower():
                is_xindy = True
                break

        if is_xindy:
            self._parse_xindy_content(lines)
            return

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if MAKEINDEX_BANG_RE.match(stripped):
                self._add_error(stripped, source="makeindex")
                self._index_error_count += 1
            elif MAKEINDEX_NOTFOUND_RE.search(stripped):
                self._add_error(stripped, source="makeindex")
                self._index_error_count += 1
                self.missing_files.add(self.ind.name)
            elif MAKEINDEX_ERROR_RE.search(stripped):
                self._add_error(stripped, source="makeindex")
                self._index_error_count += 1
            elif MAKEINDEX_WARN_RE.search(stripped):
                self._add_warning(stripped, source="makeindex")

    def _parse_xindy_content(self, lines: List[str]):
        """解析 xindy 日志内容（可能在 .ilg 中）"""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if XINDY_FATAL_RE.search(stripped):
                self._add_error(stripped, source="xindy", level="fatal")
                self._index_error_count += 1
            elif XINDY_ERROR_RE.match(stripped):
                self._add_error(stripped, source="xindy")
                self._index_error_count += 1
            elif XINDY_OPEN_RE.search(stripped):
                self._add_error(stripped, source="xindy")
                self._index_error_count += 1
                self.missing_files.add(self.ind.name)
            elif XINDY_WARN_RE.match(stripped):
                self._add_warning(stripped, source="xindy")

    def _parse_xlgfile(self):
        """解析 Xindy .xlg 日志文件"""
        lines = self._read_file_safe(self.xlg)
        if not lines:
            return
        self._parse_xindy_content(lines)

    def _parse_glgfile(self):
        """解析 Glossaries .glg 日志文件"""
        lines = self._read_file_safe(self.glg)
        if not lines:
            return

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if GLG_ERROR_RE.match(stripped) or "error" in stripped.lower():
                self._add_error(stripped, source="glossaries")
                self._index_error_count += 1
            elif "warning" in stripped.lower():
                self._add_warning(stripped, source="glossaries")

    def _parse_nlgfile(self):
        """解析 Nomencl .nlg 日志文件"""
        lines = self._read_file_safe(self.nlg)
        if not lines:
            return

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if NLG_ERROR_RE.match(stripped) or "error" in stripped.lower():
                self._add_error(stripped, source="nomencl")
                self._index_error_count += 1
            elif "warning" in stripped.lower():
                self._add_warning(stripped, source="nomencl")

    def view_log(self):
        """使用 rich 表格展示错误和警告信息"""
        if not self._parsed:
            self.parse_all()

        if self.compilation_success and not self.errors and not self.warnings:
            console.print(f"[bold green]{_('编译成功')}[/bold green]")
            if self.output_file:
                console.print(f"  {_('输出文件')}: [cyan]{self.output_file}[/cyan]")
            if self.pages:
                console.print(f"  {_('页数')}: [cyan]{self.pages}[/cyan]")
            if self.engine_type:
                console.print(f"  {_('引擎')}: [cyan]{self.engine_type}[/cyan]")
            return

        if self.errors:
            table = Table(
                title=f"[bold red]{_('错误')} ({len(self.errors)})[/bold red]", box=box.ROUNDED, show_lines=True
            )
            table.add_column(_("来源"), style="magenta", width=10)
            table.add_column(_("文件"), style="cyan", overflow="fold")
            table.add_column(_("行号"), justify="right", width=6)
            table.add_column(_("级别"), style="yellow", width=8)
            table.add_column(_("消息"), overflow="fold")

            for err in self.errors:
                table.add_row(
                    err.get("source", "?"),
                    err.get("file", "") or "-",
                    str(err.get("line", 0) or "-"),
                    err.get("level", "error"),
                    err.get("message", ""),
                )
            console.print(table)

        if self.warnings:
            warn_table = Table(
                title=f"[bold yellow]{_('警告')} ({len(self.warnings)})[/bold yellow]", box=box.ROUNDED, show_lines=True
            )
            warn_table.add_column(_("来源"), style="magenta", width=10)
            warn_table.add_column(_("文件"), style="cyan", overflow="fold")
            warn_table.add_column(_("行号"), justify="right", width=6)
            warn_table.add_column(_("级别"), style="yellow", width=10)
            warn_table.add_column(_("消息"), overflow="fold")

            for warn in self.warnings:
                warn_table.add_row(
                    warn.get("source", "?"),
                    warn.get("file", "") or "-",
                    str(warn.get("line", 0) or "-"),
                    warn.get("level", "warning"),
                    warn.get("message", ""),
                )
            console.print(warn_table)

        if self.undefined_citations:
            console.print(
                f"[bold yellow]{_('未定义引用')}:[/bold yellow] {', '.join(sorted(self.undefined_citations))}"
            )

        if self.undefined_references:
            console.print(
                f"[bold yellow]{_('未定义交叉引用')}:[/bold yellow] {', '.join(sorted(self.undefined_references))}"
            )

        if self.missing_files:
            console.print(f"[bold yellow]{_('缺失文件')}:[/bold yellow] {', '.join(sorted(self.missing_files))}")

        if self.overfull_boxes or self.underfull_boxes:
            console.print(
                f"[blue]Overfull/Underfull:[/blue] Overfull={self.overfull_boxes}, Underfull={self.underfull_boxes}"
            )

        if self.compilation_success:
            console.print(
                f"[bold green]{_('编译成功')}[/bold green] - {_('输出')}: {self.output_file}, {_('页数')}: {self.pages}"
            )
        else:
            console.print(f"[bold red]{_('编译失败')}[/bold red]")

    def check_warning(self) -> int:
        """
        检查警告数量（保持向后兼容）

        :return: 警告总数
        """
        if not self._parsed:
            self.parse_all()
        return self._warning_count

    def check_tex_error(self) -> int:
        """
        检查 TeX 错误数量（保持向后兼容）

        :return: TeX 错误数
        """
        if not self._parsed:
            self.parse_all()
        return self._tex_error_count

    def check_bib_error(self) -> int:
        """
        检查 BibTeX/Biber 错误数量（保持向后兼容）

        :return: Bib 错误数
        """
        if not self._parsed:
            self.parse_all()
        return self._bib_error_count

    def check_index_error(self) -> int:
        """
        检查索引相关错误数量（Makeindex/Xindy/Glossaries/Nomencl）

        :return: 索引错误数
        """
        if not self._parsed:
            self.parse_all()
        return self._index_error_count

    def get_errors(self) -> List[Dict[str, Any]]:
        """返回所有错误列表"""
        if not self._parsed:
            self.parse_all()
        return list(self.errors)

    def get_warnings(self) -> List[Dict[str, Any]]:
        """返回所有警告列表"""
        if not self._parsed:
            self.parse_all()
        return list(self.warnings)

    def get_undefined_citations(self) -> Set[str]:
        """返回未定义的 citation key 集合"""
        if not self._parsed:
            self.parse_all()
        return set(self.undefined_citations)

    def get_undefined_references(self) -> Set[str]:
        """返回未定义的 ref label 集合"""
        if not self._parsed:
            self.parse_all()
        return set(self.undefined_references)

    def get_missing_files(self) -> Set[str]:
        """返回缺失的文件名集合"""
        if not self._parsed:
            self.parse_all()
        return set(self.missing_files)

    def has_citation_errors(self) -> bool:
        """是否有未定义引用（需要重编译 bib）"""
        if not self._parsed:
            self.parse_all()
        return len(self.undefined_citations) > 0

    def has_reference_errors(self) -> bool:
        """是否有未定义交叉引用（需要多编译一次）"""
        if not self._parsed:
            self.parse_all()
        return len(self.undefined_references) > 0

    def has_index_errors(self) -> bool:
        """是否有索引错误"""
        if not self._parsed:
            self.parse_all()
        return self._index_error_count > 0

    def has_fatal_errors(self) -> bool:
        """是否有致命错误（Emergency stop、Fatal error 等）"""
        if not self._parsed:
            self.parse_all()
        for err in self.errors:
            if err.get("level") == "fatal":
                return True
        has_fatal_msg = False
        if self.log.exists():
            try:
                content = self.log.read_text(encoding="utf-8", errors="ignore")
                if ERROR_EMERGENCY_STOP_RE.search(content) or ERROR_FATAL_RE.search(content):
                    has_fatal_msg = True
            except Exception:
                pass
        return has_fatal_msg or (self._tex_error_count > 0 and not self.compilation_success)

    def needs_recompile_bib(self) -> bool:
        """是否需要跑 bib/biber（检测到未定义 citation 或 bbl 文件缺失）"""
        if not self._parsed:
            self.parse_all()
        if self.has_citation_errors():
            return True
        bbl_missing = any(self.bbl.name in m for m in self.missing_files)
        return bbl_missing or self._bib_error_count > 0

    def needs_recompile_index(self) -> bool:
        """是否需要跑 makeindex/xindy（ind 文件缺失或索引错误）"""
        if not self._parsed:
            self.parse_all()
        if self.has_index_errors():
            return True
        ind_missing = any(self.ind.name in m for m in self.missing_files)
        return ind_missing

    def needs_extra_pass(self) -> bool:
        """是否需要额外的编译 pass（未定义引用、Rerun to get 提示）"""
        if not self._parsed:
            self.parse_all()
        return self.has_reference_errors() or self._needs_rerun or self.has_citation_errors()

    def get_compilation_summary(self) -> Dict[str, Any]:
        """
        返回编译结果汇总字典

        :return: 包含编译状态、错误数、警告数、页数、输出文件等信息的字典
        """
        if not self._parsed:
            self.parse_all()
        return {
            "success": self.compilation_success,
            "engine": self.engine_type,
            "output_file": self.output_file,
            "pages": self.pages,
            "tex_errors": self._tex_error_count,
            "bib_errors": self._bib_error_count,
            "index_errors": self._index_error_count,
            "warnings": self._warning_count,
            "overfull_boxes": self.overfull_boxes,
            "underfull_boxes": self.underfull_boxes,
            "undefined_citations": len(self.undefined_citations),
            "undefined_references": len(self.undefined_references),
            "missing_files": list(self.missing_files),
            "needs_recompile_bib": self.needs_recompile_bib(),
            "needs_recompile_index": self.needs_recompile_index(),
            "needs_extra_pass": self.needs_extra_pass(),
            "has_fatal_errors": self.has_fatal_errors(),
        }


# ========================
# 旧 LatexLogParser 类（保持完整向后兼容）
# ========================

LogEntry = Dict[str, Union[str, int]]


class LatexLogParser:
    """旧版日志解析器，兼容现有代码接口"""

    def __init__(self, root_file: str = None):
        self.build_log: List[LogEntry] = []
        self.current_result: Optional[LogEntry] = None
        self.file_stack: List[str] = []
        self.root_file: str = root_file or ""
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0
        self._resolved_paths = {}

    def parse(self, log: str, root_file: Optional[str] = None) -> List[LogEntry]:
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            logger.warning(_("根文件未指定，无法继续解析日志"))
            return []

        self.file_stack = [self.root_file]
        self.build_log.clear()
        self.reset_state()

        lines = log.split("\n")
        for line in lines:
            self.parse_line(line)

        if self.current_result and not bib_empty_re.match(self.current_result.get("text", "")):
            self.build_log.append(self.current_result)

        logger.info(_("共解析 %(args)s 条日志消息") % {"args": len(self.build_log)})
        return self.build_log

    def reset_state(self):
        self.current_result = {"type": "", "file": "", "line": 1, "text": "", "error_pos_text": ""}
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0

    def parse_line(self, line: str):
        line = line.strip("\x00")

        if self.search_empty_line:
            if not line or (self.inside_error and line.startswith(" ")):
                self.current_result["text"] += "\n" + line
                self.search_empty_line = False
                self.inside_error = False
                return
            else:
                self.current_result["text"] += "\n" + line
                self.search_empty_line = False
                return

        error_match = None
        for pattern in [latex_error_re1, latex_error_re2]:
            error_match = pattern.match(line)
            if error_match:
                break
        if error_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            file = error_match.group(1) or self.get_current_file()
            line_num = int(error_match.group(2)) if error_match.group(2) else 1
            msg_parts = []
            if error_match.group(3):
                msg_parts.append(error_match.group(3) + " Error:")
            if error_match.group(4):
                msg_parts.append(error_match.group(4))
            msg = " ".join(msg_parts) if msg_parts else line
            self.current_result = {
                "type": LogType.ERROR,
                "file": file,
                "line": line_num,
                "text": msg,
                "error_pos_text": "",
            }
            self.search_empty_line = True
            self.inside_error = True
            return

        warn_match = latex_warn_re.match(line)
        if warn_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            category = warn_match.group(1)
            level = warn_match.group(2)
            message = warn_match.group(3) or ""
            line_num = warn_match.group(4)
            suffix = warn_match.group(5) or ""
            full_message = f"{category} {level}: {message}"
            if suffix:
                full_message += "." + suffix

            log_type = LogType.WARNING if level == "Warning" else LogType.INFO

            self.current_result = {
                "type": log_type,
                "file": self.get_current_file(),
                "line": int(line_num) if line_num else 1,
                "text": full_message,
            }
            self.search_empty_line = True
            return

        if undefined_reference_re.match(line):
            match = undefined_reference_re.match(line)
            if match:
                ref_type, label, line_num = match.groups()
                if self.current_result and self.current_result["type"]:
                    self.build_log.append(self.current_result)
                ref_type_cn = "引用" if ref_type == "Citation" else "交叉引用"
                self.current_result = {
                    "type": LogType.WARNING,
                    "file": self.get_current_file(),
                    "line": int(line_num),
                    "text": f"找不到 {ref_type_cn} `{label}`",
                    "error_pos_text": label,
                }
                self.search_empty_line = False
                return

        if self.parse_bad_box(line):
            return

        miss_match = missing_char_re.match(line)
        if miss_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            self.current_result = {
                "type": LogType.WARNING,
                "file": self.get_current_file(),
                "line": 1,
                "text": miss_match.group(1),
            }
            self.search_empty_line = False
            return

        if self.inside_error:
            match = message_line_re.match(line)
            if match:
                sub_line = match.group(2)
                self.current_result["error_pos_text"] = sub_line
                self.search_empty_line = False
                self.inside_error = False
                return

        self.parse_file_stack(line)

    def parse_bad_box(self, line: str) -> bool:
        bad_box_patterns = [
            overfull_box_re,
            overfull_box_alt_re,
            underfull_box_re,
            underfull_box_alt_re,
        ]
        for pattern in bad_box_patterns:
            match = pattern.match(line)
            if match:
                if self.current_result and self.current_result["type"]:
                    self.build_log.append(self.current_result)
                file = self.get_current_file()
                text = match.group(1)
                groups = match.groups()
                line_num = 1
                if len(groups) >= 2 and groups[1]:
                    try:
                        line_num = int(groups[1])
                    except (ValueError, TypeError):
                        line_num = 1
                self.current_result = {"type": LogType.TYPESET, "file": file, "line": line_num, "text": text}
                self.inside_box_warn = True
                self.search_empty_line = False
                return True
        return False

    def parse_file_stack(self, line: str):
        open_matches = list(file_stack_open_re.finditer(line))
        close_count = line.count(")")

        for match in open_matches:
            path_part = match.group(1).strip()
            if path_part:
                self.file_stack.append(path_part)
            else:
                self.nested += 1

        for _ in range(close_count):
            if self.nested > 0:
                self.nested -= 1
            else:
                if len(self.file_stack) > 1:
                    self.file_stack.pop()

    def get_current_file(self) -> str:
        current_path = self.file_stack[-1]
        if current_path in self._resolved_paths:
            return self._resolved_paths[current_path]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / current_path).resolve())
        except Exception:
            resolved = current_path

        self._resolved_paths[current_path] = resolved
        return resolved

    def show_log(self, use_logger=True, show_info=False):
        """
        展示日志（可集成到 CLI 或 GUI）

        :param use_logger: 是否使用 logging 输出，默认为是
        :param show_info: 是否显示 info 类型日志
        """
        sorted_logs = sorted(self.build_log, key=lambda x: x["type"])

        errors = [entry for entry in sorted_logs if entry["type"] == LogType.ERROR]
        warnings = [entry for entry in sorted_logs if entry["type"] == LogType.WARNING]
        typesets = [entry for entry in sorted_logs if entry["type"] == LogType.TYPESET]
        fonts = [entry for entry in sorted_logs if entry["type"] == LogType.FONT]
        graphics = [entry for entry in sorted_logs if entry["type"] == LogType.GRAPHIC]
        pages = [entry for entry in sorted_logs if entry["type"] == LogType.PAGE]
        infos = [entry for entry in sorted_logs if entry["type"] == LogType.INFO]

        def format_message(entry: Dict[str, Any]) -> str:
            file_path = Path(entry["file"])
            try:
                rel_path = file_path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                rel_path = file_path.name
            text = entry["text"]
            return f"{rel_path}:{entry['line']} --> {text}"

        for entry in errors:
            msg = format_message(entry)
            logger.error(msg) if use_logger else print(msg)

        for entry in warnings:
            msg = format_message(entry)
            logger.warning(msg) if use_logger else print(msg)

        for entry in typesets:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in fonts:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in graphics:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in pages:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in infos:
            if show_info:
                msg = format_message(entry)
                logger.info(msg) if use_logger else print(msg)

        if not (errors or warnings or typesets or fonts or graphics or pages):
            success_msg = _("未发现错误或警告")
            logger.info(success_msg) if use_logger else print(success_msg)

    def show_editor_jump_format(self):
        for entry in sorted(self.build_log, key=lambda x: x["type"]):
            file_path = Path(entry["file"]).name
            msg = f"{file_path}:{entry['line']}: {entry['text']}"
            logger.info(msg)
