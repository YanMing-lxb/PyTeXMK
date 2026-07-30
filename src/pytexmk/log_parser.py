"""log_analysis.py - LaTeX 编译日志分析模块（旧 API shim）。

⚠  本文件是**旧 API 薄包装层**，所有解析逻辑、regex 定义、摘要打印等
   **唯一真值在 `pytexmk.log_parsers.*` 子包**。
   请勿在此文件本地新增任何 `re.compile(...)` 或解析 for 循环；
   功能变更请改到 `src/pytexmk/log_parsers/*.py`，这里只保留别名/转发与兼容字段。
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

from pytexmk.language import set_language

logger = logging.getLogger(__name__)
_ = set_language("log_parser")


class LogType(Enum):
    """兼容旧 API 的日志等级类型别名。"""
    ERROR = "error"
    WARNING = "warning"
    TYPESET = "typesetting"
    INFO = "info"
    FONT = "font"
    GRAPHIC = "graphic"
    PAGE = "page"

    def __lt__(self, other):
        """支持按优先级排序"""
        order = {LogType.ERROR: 0, LogType.WARNING: 1, LogType.TYPESET: 2,
                 LogType.FONT: 3, LogType.GRAPHIC: 4, LogType.PAGE: 5, LogType.INFO: 6}
        return order[self] < order.get(other, 7)


LogEntry = dict[str, str | int | LogType]

from pytexmk.log_parsers.base import LogEntry as _NewLogEntry
from pytexmk.log_parsers.base import LogLevel as _LogLevel
from pytexmk.log_parsers.base import ParsedLog as _ParsedLog
from pytexmk.log_parsers.biber import BiberParser as _NewBiberParser
from pytexmk.log_parsers.bibtex import BibtexParser as _NewBibtexParser
from pytexmk.log_parsers.latexlog import LatexLogParser as _NewLatexLogParser
from pytexmk.log_parsers.summary import print_summary as _print_summary


def _log_level_to_logtype(level: _LogLevel) -> LogType:
    name = getattr(level, 'name', str(level))
    val = getattr(level, 'value', '')
    m = {'ERROR': LogType.ERROR, 'WARNING': LogType.WARNING,
         'TYPESETTING': LogType.TYPESET, 'TYPESET': LogType.TYPESET,
         'FONT': LogType.FONT, 'GRAPHIC': LogType.GRAPHIC, 'GRAPHICS': LogType.GRAPHIC,
         'IMAGE': LogType.GRAPHIC, 'PAGE': LogType.PAGE, 'PAGES': LogType.PAGE,
         'error': LogType.ERROR, 'warning': LogType.WARNING, 'typesetting': LogType.TYPESET,
         'font': LogType.FONT, 'graphic': LogType.GRAPHIC, 'page': LogType.PAGE, 'info': LogType.INFO}
    return m.get(name) or m.get(val, LogType.INFO)


def _new_entry_to_old_dict(entry: _NewLogEntry) -> dict[str, Any]:
    return {"type": _log_level_to_logtype(getattr(entry, 'level', _LogLevel.INFO)),
            "file": getattr(entry, 'file', '') or "",
            "line": getattr(entry, 'line', 1) or 1,
            "text": getattr(entry, 'text', '') or "",
            "error_pos_text": getattr(entry, 'error_pos_text', '') or ""}


class LatexLogParser:
    """LaTeX .log 日志解析器（兼容旧 API）。"""
    def __init__(self, root_file: str | None = None):
        self._new = _NewLatexLogParser(root_file)
        self.root_file: str = root_file or ""
        self.build_log: list[LogEntry] = []
        self.current_result: LogEntry | None = None

    @property
    def file_stack(self):
        return self._new.file_stack

    def parse(self, log: str, root_file: str | None = None) -> list[LogEntry]:
        parsed: _ParsedLog = self._new.parse(log, root_file=root_file or self.root_file)
        self.build_log = [_new_entry_to_old_dict(e) for e in parsed.entries]
        if self.build_log:
            self.current_result = self.build_log[-1]
        return self.build_log

    def reset_state(self):
        self._new._reset_state()
        self.current_result = None

    def parse_line(self, line: str):
        self._new._parse_line(line)
        self.build_log = [_new_entry_to_old_dict(e) for e in self._new.build_log]
        self.current_result = self.build_log[-1] if self.build_log else None

    def parse_bad_box(self, line: str) -> bool:
        self.parse_line(line); return False

    def parse_file_stack(self, line: str):
        self._new._parse_file_stack(line)

    def get_current_file(self) -> str:
        return self._new._get_current_file()

    def _rebuild_parsed_log(self, show_info: bool) -> list:
        lm = {LogType.ERROR: _LogLevel.ERROR, LogType.WARNING: _LogLevel.WARNING,
              LogType.TYPESET: _LogLevel.TYPESET, LogType.FONT: _LogLevel.FONT,
              LogType.GRAPHIC: _LogLevel.GRAPHIC, LogType.PAGE: _LogLevel.PAGE}
        ne = []
        for old in self.build_log:
            lv = lm.get(old['type'], _LogLevel.INFO)
            if (not show_info) and lv == _LogLevel.INFO:
                continue
            ne.append(_NewLogEntry(level=lv, file=old.get('file', ''), line=old.get('line', 1),
                                   text=old.get('text', ''), error_pos_text=old.get('error_pos_text', '')))
        s = {'errors_count': sum(1 for e in ne if e.level == _LogLevel.ERROR),
             'warnings_count': sum(1 for e in ne if e.level == _LogLevel.WARNING)}
        return [_ParsedLog(entries=ne, stats=s)]

    def show_log(self, use_logger: bool = True, show_info: bool = False) -> None:
        parsed_logs = self._rebuild_parsed_log(show_info=show_info)
        _print_summary(parsed_logs=parsed_logs, use_logger=use_logger, non_quiet=True,
                       show_info=show_info, ref_change_report=None, ref_added_keys=None,
                       ref_removed_keys=None, ref_total=None, ref_unchanged=None, ref_key_counts=None)

    def show_editor_jump_format(self):
        for entry in sorted(self.build_log, key=lambda x: x["type"]):
            file_path = Path(entry["file"]).name
            msg = f"{file_path}:{entry['line']}: {entry['text']}"
            logger.info(msg)

    def logparser_cli(self, auxdir, project_name):
        from pytexmk.log_parsers import run_log_pipeline
        rf = self.root_file or (project_name + '.tex')
        run_log_pipeline(project_name, auxdir, root_file=rf)


class BibTeXLogParser:
    """旧 API BibTeX 日志解析器（薄转发）。"""

    def __init__(self, root_file: str | None = None) -> None:
        self._bib = _NewBibtexParser(root_file)
        self._biber = _NewBiberParser(root_file)
        self.root_file: str = root_file or ""
        self.build_log: list[LogEntry] = []
        self.current_result: LogEntry | None = None

    def parse(self, log: str, root_file: str | None = None) -> list[LogEntry]:
        if root_file:
            self.root_file = root_file
            self._bib.root_file = root_file
            self._biber.root_file = root_file
        elif not self.root_file:
            return []
        pb = self._bib.parse(log, root_file=self.root_file)
        pbi = self._biber.parse(log, root_file=self.root_file)
        ne = list(pb.entries) + list(pbi.entries)
        seen = set()
        merged = []
        for e in ne:
            key = (getattr(e, 'file', ''), getattr(e, 'line', 1), getattr(e, 'text', ''))
            if key in seen:
                continue
            seen.add(key)
            merged.append(e)
        self.build_log = [_new_entry_to_old_dict(e) for e in merged]
        if self.build_log:
            self.current_result = self.build_log[-1]
        return self.build_log
