"""日志解析流水线门面：对外暴露 run_pipeline（即 run_log_pipeline）作为唯一入口，内部依次执行日志发现 → 多解析器调度 → 异常隔离 → 严重度汇总 → ignore_patterns 抑制 → 终端摘要 → JSON 报告写盘 → 返回 ParsedPipelineReport，同时整合参考文献变化跟踪。."""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._report import (
    ConfigIgnoredReport,
    ParsedPipelineReport,
    PipelineMeta,
    ReferencesReport,
    ReportEntry,
    ToolResultReport,
)
from ._report import (
    write_report as _write_report,
)
from .manager import LogParserManager
from .reftracker import RefChangeTracker
from .summary import print_summary

logger = logging.getLogger(__name__)


def run_pipeline(
    jobname: str | None = None,
    auxdir: str | Path | None = None,
    steps: list[str] | None = None,
    captured_outputs: dict[str, str] | None = None,
    ignore_patterns: list[str] | None = None,
    project_config: dict[str, Any] | None = None,
    root_file: str | None = None,
    write_report: bool = False,
    report_path: str | Path | None = None,
    print_terminal: bool | None = None,
    ref_tracker_translate_fn: Callable[[str], str] | None = None,
    pytexmk_version: str | None = None,
    text_len_fn: Callable[[str], int] | None = None,
    *,
    tex_engine: str | None = None,
    tex_output: str | None = None,
    bibtex_output: str | None = None,
    biber_output: str | None = None,
    other_engine_outputs: dict[str, str] | None = None,
    quiet: bool | None = None,
) -> ParsedPipelineReport:
    """入口函数，统一执行日志发现 → 解析 → 汇总 → 终端打印 → 报告写盘 → 返回结构化报告.

    支持两套调用签名：
      - 新签名（推荐）：run_pipeline(jobname, auxdir, captured_outputs={...}, steps=[...])
      - 旧兼容签名：run_pipeline(tex_engine='pdflatex', tex_output='', bibtex_output='',
                                    biber_output='', other_engine_outputs={}, quiet=True)

    - ref_tracker_translate_fn: 参考文献跟踪模块的翻译函数，不注入时默认纯英文回退，方便独立库运行。
    - pytexmk_version: PyTeXMK 版本号，不注入时默认为 'unknown'，方便独立库运行。
    - text_len_fn: 文本显示宽度计算函数，不注入时默认 len()（纯英文单宽），方便独立库运行。
    """
    import tempfile as _tf
    from pathlib import Path as _Path

    if tex_engine is not None or tex_output is not None or bibtex_output is not None \
            or biber_output is not None or other_engine_outputs is not None:
        if captured_outputs is None:
            captured_outputs = {}
        _captured = dict(captured_outputs)
        if tex_engine and tex_output is not None:
            _captured.setdefault(tex_engine, tex_output)
        if bibtex_output is not None:
            _captured.setdefault('bibtex', bibtex_output)
        if biber_output is not None:
            _captured.setdefault('biber', biber_output)
        if other_engine_outputs:
            for k, v in other_engine_outputs.items():
                _captured.setdefault(k, v)
        captured_outputs = _captured
        if steps is None:
            steps = list(dict.fromkeys(
                ([tex_engine] if tex_engine else [])
                + (['bibtex'] if bibtex_output is not None else [])
                + (['biber'] if biber_output is not None else [])
                + list(other_engine_outputs.keys() if other_engine_outputs else [])
            )) or ['pdflatex']
        if quiet is not None and print_terminal is None:
            print_terminal = not quiet

    if captured_outputs is None:
        captured_outputs = {}

    if jobname is None or auxdir is None:
        _td = _Path(_tf.mkdtemp(prefix='pytexlogs_aux_'))
        if jobname is None:
            jobname = 'pytexlogs_default_job'
        if auxdir is None:
            auxdir = str(_td)
    else:
        _td = None

    try:
        effective_pytexmk_version = pytexmk_version or 'unknown'
        if steps is None:
            steps = ['pdflatex', 'bibtex', 'biber', 'makeindex', 'xindy', 'makeglossaries',
                     'nomencl', 'pythontex', 'minted', 'asymptote']
        if print_terminal is None:
            print_terminal = True
        return _run_pipeline_impl(
            jobname=jobname,
            auxdir=auxdir,
            steps=steps,
            captured_outputs=captured_outputs,
            ignore_patterns=ignore_patterns,
            project_config=project_config,
            root_file=root_file,
            write_report=write_report,
            report_path=report_path,
            print_terminal=print_terminal,
            ref_tracker_translate_fn=ref_tracker_translate_fn,
            pytexmk_version=effective_pytexmk_version,
            text_len_fn=text_len_fn,
        )
    finally:
        if _td is not None:
            import shutil as _sh
            _sh.rmtree(_td, ignore_errors=True)


def _run_pipeline_impl(
    jobname: str,
    auxdir: str | Path,
    steps: list[str],
    captured_outputs: dict[str, str],
    ignore_patterns: list[str] | None,
    project_config: dict[str, Any] | None,
    root_file: str | None,
    write_report: bool,
    report_path: str | Path | None,
    print_terminal: bool,
    ref_tracker_translate_fn: Callable[[str], str] | None,
    pytexmk_version: str,
    text_len_fn: Callable[[str], int] | None,
) -> ParsedPipelineReport:

    auxdir_path = Path(auxdir)
    auxdir_path.mkdir(parents=True, exist_ok=True)

    captured_outputs = captured_outputs or {}
    ignore_patterns = ignore_patterns or []
    project_config = project_config or {}

    t0 = time.perf_counter()
    manager = LogParserManager()

    skipped_steps: list[str] = []
    tool_reports: list[ToolResultReport] = []
    original_entries_for_summary: list[Any] = []

    for step in steps:
        spec = manager.registry.lookup(step)
        if spec is None:
            skipped_steps.append(step)
            continue

        log_text: str | None = None
        log_path: Path | None = None

        if step in captured_outputs:
            log_text = captured_outputs[step]
            log_path = None
        else:
            log_path = spec.default_discover(jobname, auxdir_path)
            if log_path is not None:
                try:
                    log_text = spec.parser_cls(root_file=root_file)._read_log_text(log_path)
                except Exception:  # noqa: BLE001
                    log_text = None

        if log_text is None:
            skipped_steps.append(step)
            continue

        parse_exception: dict[str, str] | None = None
        parsed_entries: list[Any] = []
        stats: dict[str, Any] = {'entries_count': 0}

        try:
            parser = spec.parser_cls(root_file=root_file)
            parsed = parser.parse(log_text, root_file=root_file)

            if hasattr(parsed, 'entries'):
                raw_entries = parsed.entries
                if hasattr(parsed, 'stats') and isinstance(parsed.stats, dict):
                    stats.update(parsed.stats)
            elif isinstance(parsed, list):
                raw_entries = parsed
            else:
                raw_entries = []

            if isinstance(raw_entries, dict):
                raw_entries = [raw_entries]

            adapted_entries: list[Any] = []
            for e in raw_entries:
                if isinstance(e, dict):
                    level_val = e.get('level') or e.get('type', 'info')
                    if level_val not in ('error', 'warning', 'typesetting', 'info'):
                        level_map = {'error': 'error', 'warning': 'warning',
                                     'typesetting': 'typesetting', 'info': 'info'}
                        level_val = level_map.get(str(level_val).lower(), 'info')
                    adapted_entries.append({
                        'level': level_val,
                        'file': e.get('file'),
                        'line': e.get('line'),
                        'text': e.get('text', ''),
                        'error_pos_text': e.get('error_pos_text'),
                    })
                else:
                    adapted_entries.append(e)

            parsed_entries = adapted_entries

        except Exception as e:  # noqa: BLE001
            parse_exception = {'type': type(e).__name__, 'message': str(e)}
            parsed_entries = []

        report_entries: list[ReportEntry] = []
        for e in parsed_entries:
            if isinstance(e, dict):
                level = e.get('level', 'info')
                report_entries.append(ReportEntry(
                    level=str(level),
                    file=e.get('file'),
                    line=e.get('line'),
                    text=e.get('text', ''),
                    error_pos_text=e.get('error_pos_text'),
                ))
            else:
                lvl = getattr(e, 'level', 'info')
                if hasattr(lvl, 'value'):
                    lvl_str = lvl.value
                else:
                    lvl_str = str(lvl)
                report_entries.append(ReportEntry(
                    level=lvl_str,
                    file=getattr(e, 'file', None),
                    line=getattr(e, 'line', None),
                    text=getattr(e, 'text', ''),
                    error_pos_text=getattr(e, 'error_pos_text', None),
                ))

        level_counts: dict[str, int] = {}
        for re_ in report_entries:
            lvl = re_.level
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        stats.update(level_counts)
        stats['entries_count'] = len(report_entries)

        tool_report = ToolResultReport(
            tool_name=step,
            category=spec.category,
            importance=spec.importance,
            source_path=str(log_path) if log_path else None,
            entries=report_entries,
            stats=stats,
            parse_exception=parse_exception,
        )
        tool_reports.append(tool_report)
        original_entries_for_summary.append((step, spec, parsed_entries, log_path))

    duration_ms = int((time.perf_counter() - t0) * 1000)
    pipeline_meta = PipelineMeta(
        total_steps=len(steps),
        attempted_steps=len(steps) - len(skipped_steps),
        skipped_steps=skipped_steps,
        duration_ms=duration_ms,
    )

    ref_report = ReferencesReport()
    ref_added: list[str] = []
    ref_removed: list[str] = []
    ref_current_keys: list[str] = []
    ref_key_counts: dict[str, int] = {}
    try:
        tracker = RefChangeTracker(auxdir_path, jobname, translate_fn=ref_tracker_translate_fn)
        raw_keys, ref_key_counts = tracker.extract_current_with_counts()
        old_keys = tracker.load_cache()
        diff = tracker.diff(raw_keys, old_keys)
        ref_added = sorted(diff.get('added', set()))
        ref_removed = sorted(diff.get('removed', set()))
        ref_unchanged = sorted(diff.get('unchanged', set()))
        ref_current_keys = sorted(set(raw_keys))
        ref_report = ReferencesReport(
            current_keys=ref_current_keys,
            added=ref_added,
            removed=ref_removed,
            unchanged=ref_unchanged,
            key_counts=ref_key_counts,
            top_cited=[
                {"key": k, "count": c}
                for k, c in Counter(ref_key_counts).most_common(10)
            ],
        )
        try:
            tracker.save_cache(ref_current_keys, key_counts=ref_key_counts)
        except Exception:  # noqa: BLE001,S110
            pass
    except Exception as e:
        logger.warning("参考文献跟踪失败: %s", e, exc_info=True)
        ref_report = ReferencesReport()

    severity_counts: dict[str, dict[str, int]] = {}
    for tool in tool_reports:
        cat = tool.category
        if cat not in severity_counts:
            severity_counts[cat] = {'error': 0, 'warning': 0, 'typesetting': 0, 'info': 0, 'total': 0}
        for e in tool.entries:
            lvl = e.level
            if lvl in severity_counts[cat]:
                severity_counts[cat][lvl] += 1
            severity_counts[cat]['total'] += 1

    config_ignored_report = ConfigIgnoredReport(
        ignore_patterns=list(ignore_patterns),
        suppressed_entries=[],
        original_severity_counts={},
    )

    if ignore_patterns:
        original_severity_counts = deepcopy(severity_counts)
        config_ignored_report.original_severity_counts = original_severity_counts

        compiled_patterns = [re.compile(p) for p in ignore_patterns]

        for tool in tool_reports:
            cat = tool.category
            remaining_entries: list[ReportEntry] = []
            for e in tool.entries:
                suppressed = False
                for p in compiled_patterns:
                    if p.search(e.text):
                        suppressed = True
                        break
                if suppressed:
                    config_ignored_report.suppressed_entries.append(e)
                    lvl = e.level
                    if cat in severity_counts and lvl in severity_counts[cat]:
                        severity_counts[cat][lvl] -= 1
                    if cat in severity_counts:
                        severity_counts[cat]['total'] -= 1
                else:
                    remaining_entries.append(e)
            tool.entries = remaining_entries
            tool.stats['entries_count'] = len(remaining_entries)

    report = ParsedPipelineReport(
        schema_version=1,
        generated_at=datetime.now(tz=UTC).isoformat(),
        pytexmk_version=pytexmk_version,
        jobname=jobname,
        root_file=root_file or '',
        auxdir=str(auxdir_path),
        pipeline=pipeline_meta,
        severity_counts=severity_counts,
        tool_results=tool_reports,
        references=ref_report,
        config_ignored=config_ignored_report,
        custom_fields={},
    )

    if print_terminal:
        from .base import LogEntry, LogLevel, ParsedLog

        parsed_logs_for_summary: list[ParsedLog] = []
        for tool in tool_reports:
            plog_entries: list[LogEntry] = []
            for e in tool.entries:
                lvl_enum = LogLevel.INFO
                lvl_str = e.level
                for le in LogLevel:
                    if le.value == lvl_str:
                        lvl_enum = le
                        break
                plog_entries.append(LogEntry(
                    level=lvl_enum,
                    file=e.file or '',
                    line=e.line if e.line is not None else 0,
                    text=e.text,
                    error_pos_text=e.error_pos_text or '',
                ))
            plog = ParsedLog(
                entries=plog_entries,
                raw_text='',
                source_path=tool.source_path or '',
                tool_name=tool.tool_name,
                category=tool.category,
                importance=tool.importance,
                stats=tool.stats,
            )
            parsed_logs_for_summary.append(plog)

        print_summary(
            parsed_logs_for_summary,
            use_logger=False,
            non_quiet=True,
            ref_change_report=None,
            ref_added_keys=ref_added,
            ref_removed_keys=ref_removed,
            ref_total=len(ref_current_keys),
            ref_unchanged=len(ref_unchanged),
            ref_key_counts=ref_key_counts,
            text_len_fn=text_len_fn,
        )

    if write_report:
        default_report_path = auxdir_path / f"{jobname}.pytexmk-report.json"
        actual_path = report_path or default_report_path
        result_path = _write_report(report, actual_path)
        if result_path is not None:
            report.custom_fields['_report_path'] = str(result_path)

    return report
