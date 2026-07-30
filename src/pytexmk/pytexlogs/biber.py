"""Biber 参考文献 .bcf 日志解析器实现。"""
from __future__ import annotations

"""Biber 参考文献 .bcf 日志解析器实现。"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

__all__ = [
    "BiberParser",
    "BIBER_WARNING_HINTS",
    "biber_error_re",
    "biber_generic_error_re",
    "biber_generic_warning_re",
    "biber_info_re",
    "biber_line_warning_re",
    "biber_missing_entry_re",
]


BIBER_WARNING_HINTS: dict[str, str] = {
    "I didn't find a database entry":
        "Biber 未找到对应参考文献键：检查 .bib 文件中 @xxx{key, 是否存在，或键名与 \\cite/\\autocite 是否一致。",
    "entry `.+?' has":
        "条目重复或字段冲突：检查 .bib 中是否存在重复键，或同一条目同一字段重复定义。",
    "WARN -":
        "通用 Biber 警告：可能是数据校验问题，确认 .bib 字段格式与 biblatex 要求一致。",
}

biber_info_re = re.compile(r"^INFO - Found BibTeX data source \'(.*)\'$")
biber_error_re = re.compile(r"^ERROR - BibTeX subsystem.*, line (\d+), (.*)$")
biber_missing_entry_re = re.compile(
    r"^WARN - (I didn\'t find a database entry for \'.*?\'.*)$"
)
biber_line_warning_re = re.compile(r"^WARN - (.*? entry `(.+?)\' .*)$")
biber_generic_warning_re = re.compile(r"^WARN - (.*)$")
biber_generic_error_re = re.compile(r"^ERROR - (.*)$")


class BiberParser(BaseLogParser):
    """Biber 参考文献解析器：解析 .bcf 与 .blg 日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BiberParser：调用父类并设置 biber 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self.bib_file_stack: list[str] = []
        self._resolved_paths: dict[str, str] = {}
        self._database_files: list[str] = []

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Biber .blg 日志文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.bib_file_stack = [self.root_file]
        self.build_log.clear()
        self._database_files = []

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "database_files": self._database_files[:],
            "total_citations": 0,
            "unique_citations": 0,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="biber",
            category="bibliography",
            importance="high",
            stats=stats,
        )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")

        info_match = biber_info_re.match(line)
        if info_match:
            filename = info_match.group(1)
            resolved_file = self._resolve_bib_file(filename)
            self.bib_file_stack.append(resolved_file)
            if resolved_file not in self._database_files:
                self._database_files.append(resolved_file)
            return

        error_match = biber_error_re.match(line)
        if error_match:
            line_number = int(error_match.group(1))
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=file,
                    line=line_number,
                    text=error_match.group(2),
                )
            )
            return

        missing_match = biber_missing_entry_re.match(line)
        if missing_match:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=missing_match.group(1),
                )
            )
            return

        warning_match = biber_line_warning_re.match(line)
        if warning_match:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=warning_match.group(1),
                )
            )
            return

        warn_generic = biber_generic_warning_re.match(line)
        if warn_generic:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=file,
                    line=1,
                    text=warn_generic.group(1),
                )
            )
            return

        err_generic = biber_generic_error_re.match(line)
        if err_generic:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=file,
                    line=1,
                    text=err_generic.group(1),
                )
            )
            return

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

    @staticmethod
    def parse_bcf(bcf_path: str | Path) -> list[str]:
        """解析 Biber .bcf XML 提取参考文献处理信息。"""
        path = Path(bcf_path)
        result: list[str] = []
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for elem in root.iter():
                if (elem.tag.endswith("}citekey") or elem.tag == "citekey") and elem.text:
                    result.append(elem.text)
        except Exception:  # noqa: BLE001,S110
            pass
        return result
