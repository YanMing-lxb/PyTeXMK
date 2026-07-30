"""Minted 代码高亮日志解析器实现。"""
from __future__ import annotations

"""Minted 代码高亮日志解析器实现。"""
import re
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

minted_warning_re = re.compile(r"Package minted Warning:\s*(.+)")
minted_no_lexer_re = re.compile(r"Error:\s*no lexer for name '([^']+)'")


class MintedParser(BaseLogParser):
    """Minted 代码高亮解析器：解析 Pygments 相关日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 MintedParser：调用父类并设置 minted 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._code_highlighted = 0

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Minted 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._code_highlighted = 0

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "code_highlighted": self._code_highlighted,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="minted",
            category="code",
            importance="medium",
            stats=stats,
        )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")

        warning_match = minted_warning_re.search(line)
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

        no_lexer_match = minted_no_lexer_re.search(line)
        if no_lexer_match:
            lexer_name = no_lexer_match.group(1)
            text = (
                f"no lexer for name '{lexer_name}': "
                "请检查 Pygments 是否安装或该语言名称是否正确"
            )
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=text,
                )
            )
            return
