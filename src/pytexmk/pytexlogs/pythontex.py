"""PythonTeX 代码执行日志解析器实现。"""
from __future__ import annotations

"""PythonTeX 代码执行日志解析器实现。"""
import re
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

pythontex_warning_re = re.compile(r"Warning\s*\(pythontex\):\s*(.+)")
pythontex_code_blocks_re = re.compile(
    r"PythonTeX:\s*processed\s+(\d+)\s+code blocks"
)
pythontex_traceback_error_re = re.compile(r"Traceback[\s\S]*?(\w+Error):\s*(.+)")


class PythontexParser(BaseLogParser):
    """PythonTeX 代码执行解析器：解析 .pytxcode 相关日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 PythontexParser：调用父类并设置 pythontex 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._code_blocks_processed = 0
        self._py_errors = 0

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 PythonTeX 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._code_blocks_processed = 0
        self._py_errors = 0

        self._scan_traceback_errors(log_text)

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "code_blocks_processed": self._code_blocks_processed,
            "py_errors": self._py_errors,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="pythontex",
            category="code",
            importance="high",
            stats=stats,
        )

    def _scan_traceback_errors(self, log_text: str) -> None:
        for m in pythontex_traceback_error_re.finditer(log_text):
            self._py_errors += 1
            error_type = m.group(1)
            error_msg = m.group(2).strip()
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=f"{error_type}: {error_msg}",
                )
            )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")

        warning_match = pythontex_warning_re.search(line)
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

        code_blocks_match = pythontex_code_blocks_re.search(line)
        if code_blocks_match:
            self._code_blocks_processed = int(code_blocks_match.group(1))
            return
