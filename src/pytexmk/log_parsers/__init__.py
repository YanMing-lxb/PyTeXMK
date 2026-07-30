"""log_parsers 公共 API；下划线前缀模块为内部实现，外部禁止 import。."""

from ._facade import run_pipeline as run_log_pipeline
from ._registry import LogParserRegistry, LogParserSpec
from ._report import ParsedPipelineReport, load_report, write_report
from .asymptote import AsymptoteParser
from .base import (
    BaseLogParser,
    LogEntry,
    LogLevel,
    ParsedLog,
)
from .biber import BiberParser
from .bibtex import BibtexParser
from .glossaries import GlossariesParser
from .integration_demo import run_demo
from .latexlog import LatexLogParser
from .makeindex import MakeindexParser
from .manager import LogParserManager
from .minted import MintedParser
from .nomencl import NomenclParser
from .pythontex import PythontexParser
from .reftracker import RefChangeTracker
from .summary import (
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    IMPORTANCE_LABEL,
    print_summary,
)
from .xindy import XindyParser

__all__ = [
    "CATEGORY_LABEL",
    "CATEGORY_ORDER",
    "IMPORTANCE_LABEL",
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
    "load_report",
    "print_summary",
    "run_demo",
    "run_log_pipeline",
    "write_report",
]
