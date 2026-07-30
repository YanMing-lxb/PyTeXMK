"""Asymptote 图形绘图日志解析器实现。"""
from __future__ import annotations

"""Asymptote 图形绘图日志解析器实现。"""
import re
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

asymptote_error_re = re.compile(r"^Error:\s*(.+)")
asymptote_warning_re = re.compile(r"^WARNING:\s*(.+)")
asymptote_loading_re = re.compile(r"Loading\s+(.+\.asy)")
asymptote_output_re = re.compile(r"Output written on\s+(.+?\.(?:pdf|eps))")


class AsymptoteParser(BaseLogParser):
    """Asymptote .asy 日志解析器。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 AsymptoteParser：调用父类并设置默认工具名与类别。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._figures_processed = 0
        self._loading_asy_files: list[str] = []

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Asymptote 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._figures_processed = 0
        self._loading_asy_files = []

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "figures_processed": self._figures_processed,
            "loading_asy_files": self._loading_asy_files[:],
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="asymptote",
            category="graphics",
            importance="medium",
            stats=stats,
        )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")

        error_match = asymptote_error_re.match(line)
        if error_match:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=error_match.group(1).strip(),
                )
            )
            return

        warning_match = asymptote_warning_re.match(line)
        if warning_match:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self.root_file,
                    line=1,
                    text=warning_match.group(1).strip(),
                )
            )
            return

        loading_match = asymptote_loading_re.search(line)
        if loading_match:
            asy_file = loading_match.group(1).strip()
            self._loading_asy_files.append(asy_file)
            self.build_log.append(
                LogEntry(
                    level=LogLevel.INFO,
                    file=self.root_file,
                    line=1,
                    text=f"Loading {asy_file}",
                )
            )
            return

        output_match = asymptote_output_re.search(line)
        if output_match:
            self._figures_processed += 1
            return
