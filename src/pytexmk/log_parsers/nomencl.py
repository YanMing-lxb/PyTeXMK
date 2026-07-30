"""Nomencl 符号表 .nlg 日志解析器实现。"""
from __future__ import annotations

"""Nomencl 符号表 .nlg 日志解析器实现。"""
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog
from .makeindex import (
    entries_re as mi_entries_re,
)
from .makeindex import (
    error_re as mi_error_re,
)
from .makeindex import (
    warning_line_re as mi_warning_line_re,
)


class NomenclParser(BaseLogParser):
    """Nomencl 符号表解析器：解析 .nlg 日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 NomenclParser：调用父类并设置 nomencl 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._nomenclature_entries = 0

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Nomencl .nlg 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._nomenclature_entries = 0

        self._scan_makeindex(log_text)

        stats: dict[str, Any] = {
            "nomenclature_entries": self._nomenclature_entries,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="nomencl",
            category="glossary",
            importance="low",
            stats=stats,
        )

    def _scan_makeindex(self, log_text: str) -> None:
        file_ref = self.root_file
        for line in log_text.split("\n"):
            m = mi_entries_re.match(line)
            if m:
                self._nomenclature_entries = int(m.group(1))
                continue
            m = mi_error_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.ERROR,
                        file=file_ref,
                        line=1,
                        text=m.group(1).strip(),
                    )
                )
                continue
            m = mi_warning_line_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=file_ref,
                        line=int(m.group(1)),
                        text=m.group(2).strip(),
                    )
                )
                continue
