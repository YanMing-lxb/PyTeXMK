"""LogParserManager：按 step/suffix 调度解析器并汇总结果。"""
from __future__ import annotations

"""LogParserManager：按 step/suffix 调度解析器并汇总结果。"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ._registry import LogParserRegistry, LogParserSpec
from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ToolResultStats:
    """单个解析结果的统计计数器结构。"""
    entries_count: int = 0
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """单个工具解析结果与条目聚合。"""
    tool_name: str = ""
    category: str = ""
    importance: Literal["high", "medium", "low"] = "low"
    source_path: str = ""
    raw_text: str = ""
    entries: list[LogEntry] = field(default_factory=list)
    stats: ToolResultStats = field(default_factory=ToolResultStats)

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
        """判断 ToolResult 是否无任何条目。"""
        return not self.entries and not self.raw_text


def _parsed_log_to_tool_result(
    parsed: ParsedLog,
    tool_name: str,
    category: str,
    importance: Literal["high", "medium", "low"],
) -> ToolResult:
    error_count = sum(1 for e in parsed.entries if e.level == LogLevel.ERROR)
    warning_count = sum(1 for e in parsed.entries if e.level == LogLevel.WARNING)
    merged_stats = dict(parsed.stats)
    merged_stats.setdefault("error", error_count)
    merged_stats.setdefault("warning", warning_count)
    return ToolResult(
        tool_name=tool_name,
        category=category,
        importance=importance,
        source_path=parsed.source_path,
        raw_text=parsed.raw_text,
        entries=parsed.entries,
        stats=ToolResultStats(
            entries_count=len(parsed.entries),
            stats=merged_stats,
        ),
    )


class LogParserManager:
    """解析器管理器：按 step/suffix 路由到对应 BaseLogParser 并汇总。"""
    def __init__(self, registry: LogParserRegistry | None = None) -> None:
        """初始化 LogParserManager：缓存 registry、step→suffix 映射与回退解析器。"""
        self.registry: LogParserRegistry = (
            registry if registry is not None else LogParserRegistry.get_default_registry()
        )
        self._fallback_registered: dict[str, type[BaseLogParser]] = {}

    def register(self, step_name: str, parser_cls: type[BaseLogParser]) -> None:
        """注册自定义解析器 step_name → (suffix, parser_cls)。"""
        self._fallback_registered[step_name] = parser_cls
        self.registry.register(step_name, parser_cls)

    def lookup(self, step_name: str) -> LogParserSpec | None:
        """按 step_name 查询已注册的解析器规格。"""
        return self.registry.lookup(step_name)

    def discover_log_path(
        self,
        parser_cls: type[BaseLogParser],
        jobname: str,
        auxdir: str | Path,
    ) -> Path | None:
        """按解析器后缀在 auxdir 查找日志文件路径。"""
        spec = None
        for s in self.registry._step_to_spec.values():
            if s.parser_cls is parser_cls:
                spec = s
                break
        if spec is None:
            for pc in self._fallback_registered.values():
                if pc is parser_cls:
                    return None
            return None

        if spec.discover_hook is not None:
            result = spec.discover_hook(jobname, Path(auxdir))
            if result is not None:
                return result
        return spec.default_discover(jobname, auxdir)

    def _resolve_parser(self, step_name: str) -> tuple[type[BaseLogParser] | None, LogParserSpec | None]:
        spec = self.registry.lookup(step_name)
        if spec is not None:
            return spec.parser_cls, spec
        fallback_cls = self._fallback_registered.get(step_name)
        if fallback_cls is not None:
            return fallback_cls, None
        return None, None

    def run(
        self,
        jobname: str,
        auxdir: str | Path,
        steps: list[str] | None = None,
        captured_outputs: dict[str, str] | None = None,
    ) -> list[ToolResult]:
        """按 steps 顺序发现并解析日志，返回 list[ToolResult]。"""
        if steps is None:
            steps = [
                "pdflatex",
                "bibtex",
                "biber",
                "makeindex",
                "xindy",
                "makeglossaries",
                "nomencl",
                "pythontex",
                "minted",
                "asymptote",
            ]
        captured_outputs = captured_outputs or {}
        results: list[ToolResult] = []
        seen: set[tuple[str, str]] = set()

        for step_name in steps:
            parser_cls, spec = self._resolve_parser(step_name)
            if parser_cls is None:
                logger.warning("未找到 step=%s 对应的日志 parser，跳过", step_name)
                continue

            parser = parser_cls()
            parser_cls_name = parser_cls.__name__
            parsed: ParsedLog | None = None
            key: str | None = None

            if step_name in captured_outputs:
                key = f"captured:{step_name}"
                if (parser_cls_name, key) in seen:
                    continue
                text = captured_outputs[step_name]
                parsed = parser.parse(text)
                parsed.source_path = key
            else:
                log_path = None
                if spec is not None:
                    if spec.discover_hook is not None:
                        log_path = spec.discover_hook(jobname, Path(auxdir))
                    if log_path is None:
                        log_path = spec.default_discover(jobname, auxdir)
                else:
                    log_path = self.discover_log_path(parser_cls, jobname, auxdir)
                if log_path is None:
                    continue
                key = str(log_path)
                if (parser_cls_name, key) in seen:
                    continue
                parsed = parser.parse_file(log_path)

            if parsed is not None and key is not None:
                seen.add((parser_cls_name, key))
                if spec is not None:
                    result_tool_name = step_name
                    result_category = spec.category
                    result_importance = spec.importance
                else:
                    result_tool_name = step_name
                    result_category = parsed.category or "custom"
                    result_importance = parsed.importance or "low"
                tool_result = _parsed_log_to_tool_result(
                    parsed,
                    tool_name=result_tool_name,
                    category=result_category,
                    importance=result_importance,
                )
                results.append(tool_result)

        return results
