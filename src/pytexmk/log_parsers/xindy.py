"""Xindy 索引 .alg 日志解析器实现。"""
from __future__ import annotations

"""Xindy 索引 .alg 日志解析器实现。"""
import re
from pathlib import Path
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

xindy_error_re = re.compile(r"^ERROR:\s*(.+)")
xindy_warning_re = re.compile(r"^WARNING:\s*(.+)")
xindy_loading_module_re = re.compile(r"Loading module\s+(.+)")
xindy_letter_groups_re = re.compile(r"Added\s+(\d+)\s+letter groups")
xindy_markup_rules_re = re.compile(r"Markup( \S+)?\s*.*?(\d+)\s+rules?")
xindy_total_entries_re = re.compile(r"Total entries:\s*(\d+)")


class XindyParser(BaseLogParser):
    """Xindy 索引解析器：解析 .alg 日志输出。"""
    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Xindy .alg 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file

        check_path = root_file or getattr(self, "_source_path_hint", "") or ""
        if check_path.endswith(".glg"):
            category = "glossary"
        else:
            category = "index"

        stats: dict[str, Any] = {
            "letter_groups_added": 0,
            "modules_loaded": 0,
            "markup_rules": 0,
            "total_entries": 0,
        }
        entries: list[LogEntry] = []

        lines = log_text.split("\n")
        for line in lines:
            line = line.strip("\x00")

            error_match = xindy_error_re.match(line)
            if error_match:
                entries.append(
                    LogEntry(
                        level=LogLevel.ERROR,
                        file=self.root_file or "",
                        line=1,
                        text=error_match.group(1),
                    )
                )
                continue

            warning_match = xindy_warning_re.match(line)
            if warning_match:
                entries.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=self.root_file or "",
                        line=1,
                        text=warning_match.group(1),
                    )
                )
                continue

            loading_match = xindy_loading_module_re.match(line)
            if loading_match:
                stats["modules_loaded"] += 1
                entries.append(
                    LogEntry(
                        level=LogLevel.INFO,
                        file=self.root_file or "",
                        line=1,
                        text=loading_match.group(1),
                    )
                )
                continue

            letter_groups_match = xindy_letter_groups_re.search(line)
            if letter_groups_match:
                stats["letter_groups_added"] = int(letter_groups_match.group(1))
                continue

            markup_rules_match = xindy_markup_rules_re.search(line)
            if markup_rules_match:
                stats["markup_rules"] += int(markup_rules_match.group(2))
                continue

            total_entries_match = xindy_total_entries_re.search(line)
            if total_entries_match:
                stats["total_entries"] = int(total_entries_match.group(1))
                continue

        return ParsedLog(
            entries=entries,
            raw_text=log_text,
            source_path=getattr(self, "_source_path_hint", ""),
            tool_name="xindy",
            category=category,
            importance="medium",
            stats=stats,
        )

    def parse_file(self, log_path: str | Path, root_file: str | None = None) -> ParsedLog:
        """读取 xindy 日志文件并委托 parse 方法解析。"""
        path = Path(log_path)
        if not path.exists():
            return ParsedLog(
                source_path=str(path),
                tool_name="xindy",
                category="index",
                importance="medium",
                stats={
                    "letter_groups_added": 0,
                    "modules_loaded": 0,
                    "markup_rules": 0,
                    "total_entries": 0,
                },
            )
        text = self._read_log_text(path)
        self._source_path_hint = str(path)
        try:
            result = self.parse(text, root_file or self.root_file)
            result.source_path = str(path)
        finally:
            try:
                delattr(self, "_source_path_hint")
            except AttributeError:
                pass
        return result
