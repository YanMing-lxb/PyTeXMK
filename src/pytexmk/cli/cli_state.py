"""PyTeXMK CLI 工作流共享状态：run_workflow 全流程的运行时变量容器。"""

import argparse
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..file_ops import FileMoveRemoveManager
from ..pdf_tools import PdfFileOperation
from ..tex_project import MainFileOperation

# `-pv` 不带文件名时的哨兵值，须与 cli_args 中 argparse 的 const 保持一致
PREVIEW_AFTER_COMPILE = "preview after compile"

# 输出文件后缀（编译结果，编译后从根目录迁移到 outdir）
SUFFIXES_OUT = [".pdf", ".synctex.gz"]

# 辅助文件后缀（编译中间产物，编译前后在 auxdir 与根目录之间往返）
SUFFIXES_AUX = [
    ".log", ".blg", ".ilg",
    ".aux", ".bbl", ".xml",
    ".toc", ".lof", ".lot",
    ".out", ".bcf", ".idx", ".ind", ".nlo", ".nls", ".ist", ".glo", ".gls",
    ".bak", ".spl", ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc",
    ".listing", ".gz", ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv",
    ".fdb_latexmk", ".run.xml",
]

# 支持的魔法注释键（% !TEX <key> = <value>）
MAGIC_COMMENT_KEYS = ["program", "root", "outdir", "auxdir"]


@dataclass
class WorkflowState:
    """run_workflow 全流程共享的运行时状态。

    运行时参数按「内置默认值 → 配置文件 → 魔法注释 → 命令行」的优先级，
    依次由 cli_context.build / resolve_target / apply_magic_comments 覆盖赋值。
    """

    # ── 输入 ──
    args: argparse.Namespace
    logger: logging.Logger

    # ── 三层合并后的运行时参数 ──
    config_dict: dict = field(default_factory=dict)
    default_file: str = "main"
    compiled_program: str = "XeLaTeX"
    non_quiet: bool = False
    outdir: str = "./Build/"
    auxdir: str = "./Auxiliary/"
    project_name: str = ""

    # ── LaTeXDiff 专属 ──
    old_tex_file: str = "old_file"
    new_tex_file: str = "new_file"
    diff_tex_file: str = "LaTeXDiff"

    # ── 派生 ──
    out_files: list[str] = field(default_factory=list)
    aux_files: list[str] = field(default_factory=list)
    aux_regex_files: list[str] = field(default_factory=list)

    # ── 扫描结果 ──
    main_files_in_root: list[str] = field(default_factory=list)
    all_magic_comments: dict = field(default_factory=dict)
    magic_comments: dict = field(default_factory=dict)

    # ── 累加与开关 ──
    start_time: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    runtime_dict: dict = field(default_factory=dict)
    preview_after_compile: bool = False

    # ── 工具实例（全流程单例复用）──
    mfo: MainFileOperation = field(default_factory=MainFileOperation)
    mro: FileMoveRemoveManager = field(default_factory=FileMoveRemoveManager)
    pfo: PdfFileOperation = field(default_factory=PdfFileOperation)

    @property
    def is_latexdiff(self) -> bool:
        """是否进入 LaTeXDiff 流程：命令行出现 -d / -dc 即为真（含未给文件名的情况）。"""
        return self.args.LaTeXDiff is not None or self.args.LaTeXDiff_compile is not None
