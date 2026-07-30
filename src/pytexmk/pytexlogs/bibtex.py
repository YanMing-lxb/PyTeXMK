"""BibTeX 参考文献 .blg 日志解析器实现。"""
from __future__ import annotations

"""BibTeX 参考文献 .blg 日志解析器实现。"""
import re
from pathlib import Path
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

__all__ = [
    "BibtexParser",
    "BIBTEX_ERROR_HINTS",
    "bad_cross_ref_bibtex_re",
    "database_file_re",
    "entries_processed_re",
    "error_aux_file_re",
    "multi_line_bibtex_error_re",
    "multi_line_bibtex_warning_re",
    "multi_line_macro_bibtex_error_re",
    "re_error",
    "single_line_bibtex_warning_re",
]


BIBTEX_ERROR_HINTS: dict[str, str] = {
    "I'm skipping whatever remains of this entry":
        "BibTeX 条目语法错误：检查该条目中是否缺逗号、括号不配对，或字段名拼写错误。",
    "I'm skipping whatever remains of this command":
        "@string / 缩写宏定义错误：检查 @string{key = \"value\"} 语法。",
    "A bad cross reference":
        "交叉引用指向不存在的条目：检查 crossref = {xxx} 中 xxx 是否存在于同一 .bib 文件。",
    "---while reading file":
        "读取辅助文件失败：检查 .aux 是否正常生成（先跑一次 pdflatex），路径是否正确。",
}

single_line_bibtex_warning_re = re.compile(r"^Warning--(.+?)(?:\s+in\s+(?:file\s+)?(\S+))?\s*$")
multi_line_bibtex_warning_re = re.compile(
    r"(?m)^Warning--(.+)\n--line (\d+) of file (.+)$"
)
multi_line_bibtex_error_re = re.compile(
    r"^(.*)---line (\d+) of file (.*)\n([\s\S]*?)\nI'm skipping whatever remains of this entry$",
    re.MULTILINE,
)
bad_cross_ref_bibtex_re = re.compile(
    r'^(A bad cross reference---entry ".+?"\nrefers to entry.+?, which doesn\'t exist)$',
    re.MULTILINE,
)
multi_line_macro_bibtex_error_re = re.compile(
    r"^(.*)\n?---line (\d+) of file (.*)\n([\s\S]*?)\nI'm skipping whatever remains of this command$",
    re.MULTILINE,
)
error_aux_file_re = re.compile(r"^(.*)---while reading file (.*)$", re.MULTILINE)

re_error = re.compile(r"---(line (?P<line>[0-9]+) of|while reading) file (?P<file>.*)")

database_file_re = re.compile(r"^Database file #\d+: (.+)$", re.MULTILINE)
entries_processed_re = re.compile(r"^(\d+) entries, (\d+) warnings?$", re.MULTILINE)


class BibtexParser(BaseLogParser):
    """BibTeX 解析器：解析 .blg 日志并聚合参考文献问题。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BibtexParser：调用父类并设置 bibtex 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._resolved_paths: dict[str, str] = {}
        self._entries_processed = 0
        self._warnings_count = 0
        self._crossref_errors_count = 0
        self._database_files: list[str] = []

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 BibTeX .blg 日志文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._resolved_paths.clear()
        self._entries_processed = 0
        self._warnings_count = 0
        self._crossref_errors_count = 0
        self._database_files = []

        self._scan_multiline_patterns(log_text)
        self._scan_database_files(log_text)
        self._scan_entries_stats(log_text)

        lines = log_text.split("\n")
        last_line = ""
        for line in lines:
            self._parse_line_with_unified_error(line, last_line)
            last_line = line

        stats: dict[str, Any] = {
            "entries_processed": self._entries_processed,
            "warnings_count": self._warnings_count,
            "crossref_errors_count": self._crossref_errors_count,
            "database_files": self._database_files[:],
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="bibtex",
            category="bibliography",
            importance="high",
            stats=stats,
        )

    def _scan_multiline_patterns(self, log_text: str) -> None:
        for m in multi_line_bibtex_warning_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(3))
            filename = self._resolve_bib_file(filename)
            self._warnings_count += 1
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=filename,
                    line=int(m.group(2)),
                    text=m.group(1).strip(),
                )
            )

        for m in multi_line_bibtex_error_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(3))
            filename = self._resolve_bib_file(filename)
            msg = m.group(1).strip() or m.group(4).strip()
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=filename,
                    line=int(m.group(2)),
                    text=msg,
                )
            )

        for m in bad_cross_ref_bibtex_re.finditer(log_text):
            self._crossref_errors_count += 1
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )

        for m in multi_line_macro_bibtex_error_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(3))
            filename = self._resolve_bib_file(filename)
            msg = m.group(1).strip() or m.group(4).strip()
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=filename,
                    line=int(m.group(2)),
                    text=msg,
                )
            )

        for m in error_aux_file_re.finditer(log_text):
            filename = self._resolve_aux_file(m.group(2))
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=filename,
                    line=1,
                    text=m.group(1).strip(),
                )
            )

    def _scan_database_files(self, log_text: str) -> None:
        for m in database_file_re.finditer(log_text):
            filename = self._fix_bib_bib_dup(m.group(1).strip())
            filename = self._resolve_bib_file(filename)
            if filename not in self._database_files:
                self._database_files.append(filename)

    def _scan_entries_stats(self, log_text: str) -> None:
        m = entries_processed_re.search(log_text)
        if m:
            self._entries_processed = int(m.group(1))
            self._warnings_count = max(self._warnings_count, int(m.group(2)))

    def _parse_line_with_unified_error(self, line: str, last_line: str) -> None:
        line = line.strip("\x00")

        match = single_line_bibtex_warning_re.match(line)
        if match:
            raw_file = match.group(2)
            if raw_file:
                filename = self._fix_bib_bib_dup(raw_file)
                filename = self._resolve_bib_file(filename)
            else:
                filename = self.root_file
            self._warnings_count += 1
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=filename,
                    line=1,
                    text=match.group(1).strip(),
                )
            )
            return

        m = re_error.search(line)
        if m:
            if m.start() == 0:
                text = last_line.strip()
            else:
                text = line[:m.start()].strip()

            if not text:
                return

            filename = self._fix_bib_bib_dup(m.group("file"))
            filename = self._resolve_bib_file(filename)

            line_num = int(m.group("line")) if m.group("line") else 1

            already = any(
                e.file == filename
                and e.line == line_num
                and e.text == text
                for e in self.build_log
            )
            if already:
                return

            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=filename,
                    line=line_num,
                    text=text,
                )
            )

    @staticmethod
    def _fix_bib_bib_dup(filename: str) -> str:
        if filename.endswith(".bib.bib"):
            return filename[:-4]
        return filename

    def _resolve_bib_file(self, filename: str) -> str:
        if not filename:
            return self.root_file

        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / filename).resolve())
        except Exception:  # noqa: BLE001
            resolved = filename

        self._resolved_paths[filename] = resolved
        return resolved

    def _resolve_aux_file(self, filename: str) -> str:
        filename = filename.replace(".aux", ".tex")
        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / filename).resolve())
        except Exception:  # noqa: BLE001
            resolved = filename

        self._resolved_paths[filename] = resolved
        return resolved
