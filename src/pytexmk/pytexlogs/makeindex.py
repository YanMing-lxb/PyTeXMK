"""Makeindex 索引 .ilg 日志解析器实现。"""
from __future__ import annotations

"""Makeindex 索引 .ilg 日志解析器实现。"""
import re
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

lines_read_re = re.compile(r"^##\s+(\d+)\s+lines read")
entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
warnings_issued_re = re.compile(r"^##\s+(\d+)\s+warnings issued")
processing_time_re = re.compile(r"Processing time:\s*([\d.]+)\s*sec")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning\s*--(.+)$")


class MakeindexParser(BaseLogParser):
    """Makeindex 索引解析器：解析 .ilg 与 makeindex 输出。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 MakeindexParser：调用父类并设置 makeindex 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._lines_read = 0
        self._entries_accepted = 0
        self._entries_rejected = 0
        self._warnings_issued = 0
        self._processing_time_ms = 0.0

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Makeindex .ilg 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._lines_read = 0
        self._entries_accepted = 0
        self._entries_rejected = 0
        self._warnings_issued = 0
        self._processing_time_ms = 0.0

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "lines_read": self._lines_read,
            "entries_accepted": self._entries_accepted,
            "entries_rejected": self._entries_rejected,
            "warnings_issued": self._warnings_issued,
            "processing_time_ms": self._processing_time_ms,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="makeindex",
            category="index",
            importance="medium",
            stats=stats,
        )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")

        m = lines_read_re.match(line)
        if m:
            self._lines_read = int(m.group(1))
            return

        m = entries_re.match(line)
        if m:
            self._entries_accepted = int(m.group(1))
            self._entries_rejected = int(m.group(2))
            return

        m = warnings_issued_re.match(line)
        if m:
            self._warnings_issued = int(m.group(1))
            return

        m = processing_time_re.search(line)
        if m:
            self._processing_time_ms = float(m.group(1)) * 1000
            return

        m = error_re.match(line)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )
            return

        m = warning_line_re.match(line)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self.root_file,
                    line=int(m.group(1)),
                    text=m.group(2).strip(),
                )
            )
            return

        m = warning_dash_re.match(line)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )
            return
