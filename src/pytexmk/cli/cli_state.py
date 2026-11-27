"""PyTeXMK CLI 工作流共享状态：run_workflow 全流程的运行时变量容器。"""

import argparse
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..file_ops import FileMoveRemoveManager
from ..layout import AUX_SUFFIXES, OUT_SUFFIXES, SYNCTEX_SUFFIXES
from ..pdf_tools import PdfFileOperation
from ..tex_project import MainFileOperation

# `-pv` 不带文件名时的哨兵值，须与 cli_args 中 argparse 的 const 保持一致
PREVIEW_AFTER_COMPILE = "preview after compile"

# 输出/辅助文件后缀统一由 pytexmk.layout 维护（含"不要写裸 .gz"等约束说明）
SUFFIXES_OUT = OUT_SUFFIXES
SUFFIXES_AUX = AUX_SUFFIXES

# 支持的魔法注释键（% !TEX <key> = <value>）
MAGIC_COMMENT_KEYS = ["program", "root", "outdir", "auxdir"]


@dataclass(slots=True)
class WorkflowState:
    """run_workflow 全流程共享的运行时状态。

    运行时参数按「内置默认值 → 配置文件 → 魔法注释 → 命令行」的优先级，
    依次由 cli_context.build / resolve_target / apply_magic_comments 覆盖赋值。

    slots=True（3.10+ 的 dataclass 选项，在 3.15 工具链下可放心使用）让实例不再带
    每实例 __dict__：字段集在类层面固定，字段名拼错立即 AttributeError 而不是
    悄悄新建一个属性；同时实例更省内存、属性访问更快。
    注意 slots 类不能随意挂未声明属性，新增状态请照旧在此声明字段。
    """

    # ── 输入 ──
    args: argparse.Namespace
    logger: logging.Logger

    # ── 三层合并后的运行时参数 ──
    config_dict: dict = field(default_factory=dict)
    default_file: str = "main"
    #: 主文件是否来自显式选择（命令行文档或文件型子项目别名）。
    #: 为 True 时配置文件里的 default_file 不得覆盖它——否则 `-s one`
    #: （one="one/paper.tex"）会被根配置的 default_file="main" 抢走。
    explicit_default: bool = False
    compiled_program: str = "XeLaTeX"
    non_quiet: bool = False
    outdir: str = "./Build/"
    auxdir: str = "./Auxiliary/"
    project_name: str = ""
    output_name: str = ""             # 输出名，始终由主文件名派生

    # ── 构建行为（配置文件 / 命令行可覆盖）──
    native_build: bool = True
    shell_escape: str = "true"       # true | false | auto（默认开启）
    synctex: bool = True              # 是否生成 .synctex.gz（编辑器跳转依赖）
    interaction: str = ""
    extra_args: list[str] = field(default_factory=list)
    max_extra_compilations: int = 8

    # ── 投稿打包（[submission] 段，`-sp` 使用）──
    submission_reproducible: bool = True       # 打包时固定时间戳/排序，可复现
    submission_output_dir: str = "./Submission/"  # 投稿包输出目录
    submission_keep_preamble: bool = False     # 保留原导言区（不注释 fontspec 等）

    # ── 编译前检查（[preflight] 段）──
    preflight_enabled: bool = True

    # ── 派生 ──
    out_files: list[str] = field(default_factory=list)
    aux_files: list[str] = field(default_factory=list)
    aux_regex_files: list[str] = field(default_factory=list)

    def refresh_file_lists(self, name: str | None = None) -> None:
        """按 ``name``（缺省 ``output_name``）重算输出/辅助文件清单。

        新增后缀只在 ``layout`` 里加一次，所有调用点都走这里，避免漏改其中一处。
        """
        base = name if name is not None else self.output_name
        self.out_files = [f"{base}{suffix}" for suffix in SUFFIXES_OUT]
        self.aux_files = [f"{base}{suffix}" for suffix in SUFFIXES_AUX]
        # 递归清理（-ca）额外认两种 SyncTeX：只删编译定位产物，不用裸 `.gz`
        # 通配，否则会把用户自己的 .gz 数据文件一并删掉。
        # 后缀内的点必须转义；末尾必须加 `$` 锚点：旧实现只有 ".*\.aux"，
        # 会把 `chapter.aux.notes.tex` 这类**源文件**当成 .aux 产物删除。
        self.aux_regex_files = [
            f".*{re.escape(suffix)}$" for suffix in SUFFIXES_AUX
        ]
        self.aux_regex_files.extend(
            rf".*{re.escape(suffix)}$" for suffix in SYNCTEX_SUFFIXES
        )

    # ── 扫描结果 ──
    main_files_in_root: list[str] = field(default_factory=list)
    all_magic_comments: dict = field(default_factory=dict)
    magic_comments: dict = field(default_factory=dict)

    # ── 累加与开关 ──
    start_time: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    #: 单调时钟基准：统计表用 perf_counter 差值，避免 NTP/夏令时跳变。
    start_perf: float = field(default_factory=time.perf_counter)
    runtime_dict: dict = field(default_factory=dict)
    preview_after_compile: bool = False

    # ── 工具实例（全流程单例复用）──
    mfo: MainFileOperation = field(default_factory=MainFileOperation)
    mro: FileMoveRemoveManager = field(default_factory=FileMoveRemoveManager)
    pfo: PdfFileOperation = field(default_factory=PdfFileOperation)
