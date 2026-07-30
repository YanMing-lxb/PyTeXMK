"""pytexlogs 公共 API；下划线前缀模块为内部实现，外部禁止 import。.

Architecture rule (DO NOT BREAK):
  - 本包为「潜在独立第三方库 pytexlogs」：未来可直接整体复制到任意 Python 项目，作为顶级包 import。
  - **禁止使用双点级别的相对 import（任何跳出子包的 from <parent-pkg> ...）**，因为当它作为顶级包时上级目录不存在。
  - 禁止直接 `import pytexmk.language / pytexmk.version / pytexmk.config ...` 的任何主包非子包模块；外部依赖必须通过 run_pipeline 的可空参数注入（默认纯英文/unknown）。
  - 禁止在本包外新建 `log_parser.py` 薄转发文件；所有外部使用必须走本 __all__ 列表中的公共 API。
"""

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
from .biber import BiberParser, BIBER_WARNING_HINTS
from .bibtex import BibtexParser, BIBTEX_ERROR_HINTS
from .glossaries import GlossariesParser
from .integration_demo import run_demo
from .latexlog import LatexLogParser, LATEX_LOG_HINTS
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
    format_editor_jumps,
    log_editor_jumps,
    print_summary,
    show_log_entries,
)
from .xindy import XindyParser

__all__ = [
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
    "run_log_pipeline",
    "show_log_entries",
    "write_report",
]
