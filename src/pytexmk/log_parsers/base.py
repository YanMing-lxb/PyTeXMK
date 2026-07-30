"""日志解析器公共基类与通用数据结构。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class LogLevel(Enum):
    """日志等级枚举：错误/警告/排版/信息/字体/图形/页面。"""
    ERROR = "error"
    WARNING = "warning"
    TYPESET = "typesetting"
    INFO = "info"
    FONT = "font"
    GRAPHIC = "graphic"
    PAGE = "page"

    def __lt__(self, other: LogLevel) -> bool:
        """按严重程度比较两个 LogLevel 等级大小。"""
        order: dict[LogLevel, int] = {
            LogLevel.ERROR: 0,
            LogLevel.WARNING: 1,
            LogLevel.TYPESET: 2,
            LogLevel.FONT: 3,
            LogLevel.GRAPHIC: 4,
            LogLevel.PAGE: 5,
            LogLevel.INFO: 6,
        }
        return order[self] < order.get(other, 7)


@dataclass(slots=True)
class LogEntry:
    """单条日志条目数据结构：等级、文件、行号、文本、错误上下文。"""
    level: LogLevel
    file: str
    line: int
    text: str
    error_pos_text: str = ""


@dataclass(slots=True)
class ParsedLog:
    """解析后的日志结果：条目列表、原始文本、来源、工具名、统计。"""
    entries: list[LogEntry] = field(default_factory=list)
    raw_text: str = ""
    source_path: str = ""
    tool_name: str = ""
    category: str = ""
    importance: Literal["high", "medium", "low"] = "low"
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[LogEntry]:
        """返回所有等级为 ERROR 的条目列表。"""
        return [e for e in self.entries if e.level == LogLevel.ERROR]

    @property
    def warnings(self) -> list[LogEntry]:
        """返回所有等级为 WARNING 的条目列表。"""
        return [e for e in self.entries if e.level == LogLevel.WARNING]

    @property
    def is_empty(self) -> bool:
        """判断解析结果是否为空（无条目且无原始文本）。"""
        return not self.entries and not self.raw_text


class BaseLogParser(ABC):
    """日志解析器抽象基类：定义 parse/parse_file 接口与编码兜底读取。"""
    _FALLBACK_ENCODINGS: tuple[str, ...] = (
        "utf-8",
        "utf-8-sig",
        "gbk",
        "gb18030",
        "latin-1",
    )

    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BaseLogParser：缓存 root_file。"""
        self.root_file: str = root_file or ""

    @abstractmethod
    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析日志字符串，返回 ParsedLog（由子类实现）。"""
        ...

    def parse_file(self, log_path: str | Path, root_file: str | None = None) -> ParsedLog:
        """读取日志文件并委托 parse 方法解析，多编码兜底。"""
        path = Path(log_path)
        if not path.exists():
            return ParsedLog(source_path=str(path))
        text = self._read_log_text(path)
        result = self.parse(text, root_file or self.root_file)
        result.source_path = str(path)
        return result

    def _read_log_text(self, log_path: str | Path) -> str:
        path = Path(log_path)
        data = path.read_bytes()
        for encoding in self._FALLBACK_ENCODINGS:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")
