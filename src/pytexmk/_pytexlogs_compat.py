"""PyTeXLogs 适配层：优先使用已安装的第三方库 `pytexlogs`（remote），fallback 到内嵌子包 pytexmk.pytexlogs（bundled）。

同时负责 remote 场景下的 logger 桥接：独立库 pytexlogs logger 的 handlers/level 与主程序 pytexmk.pytexlogs 对齐。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

_PUBLIC_EXPECTED = [
    "run_log_pipeline",
    "BIBER_WARNING_HINTS",
    "BIBTEX_ERROR_HINTS",
    "CATEGORY_LABEL",
    "CATEGORY_ORDER",
    "IMPORTANCE_LABEL",
    "LATEX_LOG_HINTS",
    "AsymptoteParser",
    "BaseLogParser",
    "BiberParser",
    "BibtexParser",
    "GlossariesParser",
    "LatexLogParser",
    "LogEntry",
    "LogLevel",
    "LogParserManager",
    "LogParserRegistry",
    "LogParserSpec",
    "MakeindexParser",
    "MintedParser",
    "NomenclParser",
    "ParsedLog",
    "ParsedPipelineReport",
    "PythontexParser",
    "RefChangeTracker",
    "XindyParser",
    "format_editor_jumps",
    "load_report",
    "log_editor_jumps",
    "print_summary",
    "run_demo",
    "show_log_entries",
    "write_report",
]


def attach_pytexlogs_handlers_to_pytexmk_logger() -> None:
    """把独立库 pytexlogs logger 的 handlers/level 与主程序 pytexmk.pytexlogs 对齐。

    允许幂等调用（多次调用不重复添加 handler）。
    """
    ref_logger = logging.getLogger("pytexmk.pytexlogs")
    remote_logger = logging.getLogger("pytexlogs")
    remote_logger.setLevel(ref_logger.level)
    remote_logger.propagate = ref_logger.propagate
    existing = {
        type(h).__name__ + repr(getattr(h, "baseFilename", ""))
        for h in remote_logger.handlers
    }
    for h in ref_logger.handlers:
        key = type(h).__name__ + repr(getattr(h, "baseFilename", ""))
        if key not in existing:
            remote_logger.addHandler(h)


_WHERE: str
_REMOTE_ALL: list[str]

try:
    import pytexlogs as _remote_mod  # type: ignore[import-not-found]
    _REMOTE_ALL = list(getattr(_remote_mod, "__all__", _PUBLIC_EXPECTED))
    for _name in _REMOTE_ALL:
        globals()[_name] = getattr(_remote_mod, _name)
    _WHERE = "remote"
    attach_pytexlogs_handlers_to_pytexmk_logger()
except Exception:  # noqa: BLE001
    import pytexmk.pytexlogs as _bundled_mod  # type: ignore[import-not-found]
    _REMOTE_ALL = list(getattr(_bundled_mod, "__all__", _PUBLIC_EXPECTED))
    for _name in _REMOTE_ALL:
        globals()[_name] = getattr(_bundled_mod, _name)
    _WHERE = "bundled"

PYTEXLOGS_SOURCE: str = _WHERE
__all__: list[str] = list(_REMOTE_ALL) + [
    "PYTEXLOGS_SOURCE",
    "attach_pytexlogs_handlers_to_pytexmk_logger",
]

if TYPE_CHECKING:  # pragma: no cover
    from pytexmk.pytexlogs import (  # noqa: F401
        AsymptoteParser,
        BaseLogParser,
        BiberParser,
        BibtexParser,
        BIBER_WARNING_HINTS,
        BIBTEX_ERROR_HINTS,
        CATEGORY_LABEL,
        CATEGORY_ORDER,
        GlossariesParser,
        IMPORTANCE_LABEL,
        LatexLogParser,
        LATEX_LOG_HINTS,
        LogEntry,
        LogLevel,
        LogParserManager,
        LogParserRegistry,
        LogParserSpec,
        MakeindexParser,
        MintedParser,
        NomenclParser,
        ParsedLog,
        ParsedPipelineReport,
        PythontexParser,
        RefChangeTracker,
        XindyParser,
        format_editor_jumps,
        load_report,
        log_editor_jumps,
        print_summary,
        run_demo,
        run_log_pipeline,
        show_log_entries,
        write_report,
    )
