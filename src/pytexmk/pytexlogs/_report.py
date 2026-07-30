"""报告数据模型、序列化/反序列化、JSON 读写工具。定义 ParsedPipelineReport 及其子结构，提供 report_to_dict / dict_to_report / write_report / load_report 四大公共 API。."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_VALID_LEVELS = {"error", "warning", "typesetting", "info", "debug"}


@dataclass(slots=True)
class ReportEntry:
    """单条日志条目，仅使用 JSON 兼容类型。."""

    level: str = "info"
    file: str | None = None
    line: int | None = None
    text: str = ""
    error_pos_text: str | None = None
    source: str | None = None


@dataclass(slots=True)
class ToolResultReport:
    """单个工具的解析结果汇总。."""

    tool_name: str = ""
    category: str = ""
    importance: str = "medium"
    source_path: str | None = None
    entries: list[ReportEntry] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    parse_exception: dict[str, str] | None = None


@dataclass(slots=True)
class PipelineMeta:
    """流水线执行元数据。."""

    total_steps: int = 0
    attempted_steps: int = 0
    skipped_steps: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass(slots=True)
class ReferencesReport:
    """引用跟踪变化报告。."""

    current_keys: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    previous_aux_hash: str | None = None
    current_aux_hash: str | None = None
    key_counts: dict[str, int] = field(default_factory=dict)
    top_cited: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ConfigIgnoredReport:
    """配置忽略条目与抑制统计。."""

    ignore_patterns: list[str] = field(default_factory=list)
    suppressed_entries: list[ReportEntry] = field(default_factory=list)
    original_severity_counts: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedPipelineReport:
    """顶层流水线解析报告。."""

    schema_version: int = 1
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    pytexmk_version: str = "unknown"
    jobname: str = ""
    root_file: str = ""
    auxdir: str = ""
    pipeline: PipelineMeta = field(default_factory=PipelineMeta)
    severity_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    tool_results: list[ToolResultReport] = field(default_factory=list)
    references: ReferencesReport = field(default_factory=ReferencesReport)
    config_ignored: ConfigIgnoredReport = field(default_factory=ConfigIgnoredReport)
    custom_fields: dict[str, Any] = field(default_factory=dict)


def _from_dict_simple(cls, d: dict[str, Any]) -> Any:
    """递归构造 dataclass 实例，未知字段入 custom_fields（若有）。."""
    cls_fields = {f.name for f in dataclasses.fields(cls)}
    known: dict[str, Any] = {}
    unknown: dict[str, Any] = {}

    for k, v in d.items():
        if k in cls_fields:
            known[k] = v
        else:
            unknown[k] = v

    for fname in cls_fields:
        if fname not in known:
            continue
        fval = known[fname]

        if isinstance(fval, dict):
            nested_cls = None
            if fname == "pipeline":
                nested_cls = PipelineMeta
            elif fname == "references":
                nested_cls = ReferencesReport
            elif fname == "config_ignored":
                nested_cls = ConfigIgnoredReport
            if nested_cls is not None:
                known[fname] = _from_dict_simple(nested_cls, fval)

        if fname == "entries" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ReportEntry, item) if isinstance(item, dict) else item
                for item in fval
            ]
        if fname == "suppressed_entries" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ReportEntry, item) if isinstance(item, dict) else item
                for item in fval
            ]
        if fname == "tool_results" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ToolResultReport, item) if isinstance(item, dict) else item
                for item in fval
            ]

    if cls is ReportEntry and "level" in known:
        lvl = known["level"]
        if lvl not in _VALID_LEVELS:
            if lvl:
                logger.warning("unknown level %s", lvl)
            known["level"] = "info"

    try:
        instance = cls(**known)
    except TypeError:
        defaults: dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name not in known:
                if f.default is not dataclasses.MISSING:
                    defaults[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:
                    defaults[f.name] = f.default_factory()
        combined = {**defaults, **known}
        instance = cls(**combined)

    if "custom_fields" in cls_fields and unknown:
        key = f"_unknown_keys_{cls.__name__}"
        existing = instance.custom_fields.get(key, [])
        if isinstance(existing, list):
            existing.extend(unknown.keys())
            instance.custom_fields[key] = existing
            for uk, uv in unknown.items():
                if uk not in instance.custom_fields:
                    instance.custom_fields[uk] = uv

    return instance


def report_to_dict(report: ParsedPipelineReport) -> dict[str, Any]:
    """将 ParsedPipelineReport 递归转为 dict；若 references.key_counts 非空但 top_cited 为空则自动补 Top10。."""
    d = dataclasses.asdict(report)
    refs = d.get("references")
    if isinstance(refs, dict):
        kc = refs.get("key_counts")
        tc = refs.get("top_cited")
        if kc and not tc:
            refs["top_cited"] = [
                {"key": k, "count": c} for k, c in Counter(kc).most_common(10)
            ]
    return d


def dict_to_report(d: dict[str, Any]) -> ParsedPipelineReport:
    """从 dict 递归构造 ParsedPipelineReport。."""
    return _from_dict_simple(ParsedPipelineReport, d)


def write_report(report: ParsedPipelineReport, path: str | Path) -> Path | None:
    """原子式写入 JSON 报告到 path，失败返回 None。."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                report_to_dict(report),
                f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        os.replace(tmp, path)
    except OSError:
        logger.warning("报告写入失败: %s", exc_info=True)
        return None
    return path


def load_report(path: str | Path) -> ParsedPipelineReport:
    """从 JSON 文件加载 ParsedPipelineReport，高 schema_version 警告。."""
    with open(path, "r", encoding="utf-8") as f:
        d: dict[str, Any] = json.load(f)
    sv = d.get("schema_version", 1)
    if sv > 1:
        logger.warning("schema_version %d 高于当前 1，部分字段可能被忽略", sv)
    return dict_to_report(d)
