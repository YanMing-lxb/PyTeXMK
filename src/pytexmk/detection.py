"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-29 15:43:26 +0800
LastEditTime : 2025-05-15 18:37:17 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/detection.py
Description  :
 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【6 维编译状态检测的布尔/次数计算 + 辅助文件快照读取】。
  具体职责：
    1. 6 维编译状态检测的布尔/次数计算：bib / idx / toc / aux / out / log。
    2. 辅助文件快照读取 prepare_LaTeX_output_files / prepare_aux_out_snapshots。
  调用依赖关系拓扑：
    compile.CompileLaTeX 实例化 CompilationDetector 持有引用；
    compile_engine.RUN 通过 compile_model.detector.* 调用检测方法。
  下游依赖：
    file_ops / logger / timing / Path / language。
"""

import locale
import logging
import re
from collections import defaultdict
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("detection")

BIBER_PATTERN = re.compile(r"\\abx@aux@refcontext")
BIBTEX_PATTERN = re.compile(r"\\bibdata")

BIBER_BIB_PATTERN = re.compile(
    r"<bcf:datasource[^>]*>\s*(.*?)\s*</bcf:datasource>"
)
BIBTEX_BIB_PATTERN = re.compile(r"\\bibdata\{(.*)\}")

# 三种引用命令：Biber / BibTeX / thebibliography
_CITE_PATTERNS = (
    re.compile(r"\\abx@aux@cite{.*?}\{(.*)\}"),   # Biber
    re.compile(r"\\citation\{(.*)\}"),             # BibTeX
    re.compile(r"\\bibcite\{(.*?)\}"),             # thebibliography
)

RERUN_LOG_PATTERNS = [
    re.compile(r"LaTeX Warning: There were undefined references\."),
    re.compile(r"LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\."),
    re.compile(r"Package lastpage Warning: Rerun to get the references right"),
    re.compile(r"Package rerunfilecheck Warning: .* Rerun"),
    re.compile(r"LaTeX Warning: Citation .* undefined"),
    re.compile(r"LaTeX Warning: There were multiply-defined labels\."),
]

# ── 索引系统注册表 ──────────────────────────────────────────────────
# 统一描述三种 LaTeX 索引系统的快照/检测元信息，快照和检测都从此驱动。
# 每条规则字段：
#   name        : 索引系统标识
#   triggers    : 触发扩展名列表（任一存在即命中 → any 语义）
#   pattern     : .aux 中正则（仅 glossaries 需要，因为它的 ext_i/ext_o 是动态解析的）
#   cmd_builder : (proj, *args...) -> list[list[str]]，生成要执行的索引命令
#
# glossaries 特殊：每个 .aux 中的 \\@newglossary 条目不只是一套，一个项目可能有多套
#                  (glossaries 有多个 glossary 类型：main/acronyms/symbols 等)，
#                  所以它的 cmd_builder 接收 match 的动态 (name, ext_o, ext_i)。
_NGLOSSARY_PATTERN = re.compile(
    r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
)

_INDEX_REGISTRY: tuple[dict, ...] = (
    {
        "name": "glossaries",
        "triggers": [".glo", ".acn", ".slo"],
        "pattern": _NGLOSSARY_PATTERN,
        # match.groups() = (_name, ext_o, ext_i)
        "cmd_builder": lambda proj, _name, ext_o, ext_i: [
            f"glossaries {_name}",
            f"makeindex -s {proj}.ist -o {proj}{ext_o} {proj}{ext_i}",
        ],
    },
    {
        "name": "nomencl",
        "triggers": [".nlo"],                      # 任一存在即命中
        "fixed_in": ".nlo",
        "fixed_out": ".nls",
        "cmd_builder": lambda proj: [
            "nomencl",
            f"makeindex -s nomencl.ist -o {proj}.nls {proj}.nlo",
        ],
    },
    {
        "name": "makeidx",
        "triggers": [".idx"],                      # 任一存在即命中
        "fixed_in": ".idx",
        "fixed_out": ".ind",
        "cmd_builder": lambda proj: [
            "makeidx", f"makeindex {proj}.idx",
        ],
    },
)


def _read_file_content(path: str | Path) -> str:
    """容错读取 LaTeX 辅助文件内容，避免因编码不同导致编译检测崩溃。

    中文字典类文档（如 CTeX/cct 的 GBK 方案）生成的 .aux/.toc/.out 等
    辅助文件常为本地编码（Windows 中文环境为 cp936），并非 UTF-8。此处
    优先严格按 UTF-8 解码，失败则退回系统本地编码，最后再以
    errors="replace" 兜底，保证检测阶段的快照与重读永不因解码异常中断。
    """
    data = Path(path).read_bytes()
    for enc in ("utf-8", locale.getpreferredencoding(False)):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _count_citations(file_name):
    counter = defaultdict(int)

    aux_content = _read_file_content(file_name)
    for pattern in _CITE_PATTERNS:
        for match in pattern.finditer(aux_content):
            counter[match.group(1)] += 1
    return counter


class CompilationDetector:
    def __init__(
        self,
        project_name,
        compiled_program,
        out_files,
        aux_files,
        outdir,
        auxdir,
        non_quiet,
        MRO,
    ):
        self.logger = logging.getLogger(__name__)

        self.project_name = project_name
        self.compiled_program = compiled_program
        self.out_files = out_files
        self.aux_files = aux_files
        self.auxdir = auxdir
        self.outdir = outdir
        self.non_quiet = non_quiet
        self.MRO = MRO

        self.bib_file = ""
        self.out = ""

    def prepare_LaTeX_output_files(self):
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            cite_counter = self._generate_citation_counter()
            index_aux_content_dict_old = self._index_aux_content_get()
        else:
            cite_counter = {f"{self.project_name}.aux": defaultdict(int)}
            index_aux_content_dict_old = {}
        toc_file_path = Path(f"{self.project_name}.toc")
        if toc_file_path.exists():
            toc_file = _read_file_content(toc_file_path)
        else:
            toc_file = ""

        return cite_counter, toc_file, index_aux_content_dict_old

    def _generate_citation_counter(self):
        cite_counter = {}
        file_name = f"{self.project_name}.aux"
        main_aux_content = _read_file_content(file_name)
        cite_counter[file_name] = _count_citations(file_name)

        for match in re.finditer(r"\\@input\{(.*.aux)\}", main_aux_content):
            file_name = match.groups()[0]
            try:
                counter = _count_citations(file_name)
            except OSError:
                self.logger.info(
                    _("文件不存在或无法读取,跳过文件: %(args)s") % {"args": file_name}
                )
            else:
                cite_counter[file_name] = counter

        return cite_counter

    def _index_aux_content_get(self):
        """快照阶段：扫描三种索引系统，为命中的系统记录 ext_i（输入文件）旧内容。

        统一语义：快照存 ext_i，检测也比较 ext_i。
        原先 glossaries 分支误读 ext_o（输出文件）已在此修正。
        nomencl/makeidx 原先要求 ext_i 和 ext_o 两文件都存在才快照，
        现在统一改为任一触发扩展名存在即快照（与检测阶段对齐）。
        """
        index_aux_content_dict_old: dict[str, str] = {}

        aux_path = Path(f"{self.project_name}.aux")
        if not aux_path.exists():
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")
            return index_aux_content_dict_old

        for rule in _INDEX_REGISTRY:
            if not any(
                Path(f"{self.project_name}{ext}").exists()
                for ext in rule["triggers"]
            ):
                continue

            if rule["name"] == "glossaries":
                main_aux = _read_file_content(aux_path)
                for match in rule["pattern"].finditer(main_aux):
                    _name, _ext_o, ext_i = match.groups()
                    key = f"{self.project_name}.{ext_i}"
                    infile_path = Path(key)
                    if infile_path.exists():
                        index_aux_content_dict_old[key] = _read_file_content(infile_path)
            else:
                # nomencl / makeidx：固定 ext_i
                ext_i = rule["fixed_in"]
                key = f"{self.project_name}{ext_i}"
                infile_path = Path(key)
                if infile_path.exists():
                    index_aux_content_dict_old[key] = _read_file_content(infile_path)

        return index_aux_content_dict_old

    def toc_changed_judgment(self, toc_file):
        file_name = Path(self.project_name).with_suffix(
            ".toc"
        )
        return file_name.exists() and _read_file_content(file_name) != toc_file

    def bib_judgment(self, old_cite_counter):
        bib_engine = None
        target_name_bib = None
        Latex_compilation_times = 0
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            aux_content = _read_file_content(aux_file_path)
            match_biber = BIBER_PATTERN.search(
                aux_content
            )
            match_bibtex = BIBTEX_PATTERN.search(
                aux_content
            )
            if match_biber or match_bibtex:
                if match_biber:
                    bcf_file_path = Path(
                        f"{self.project_name}.bcf"
                    )
                    match_biber_bib = BIBER_BIB_PATTERN.search(
                        _read_file_content(bcf_file_path)
                    )
                    if match_biber_bib:
                        self.bib_file = match_biber_bib.group(1)
                        bib_engine = "biber"
                        Latex_compilation_times = 2

                elif match_bibtex:
                    match_bibtex_bib = BIBTEX_BIB_PATTERN.search(
                        aux_content
                    )
                    if match_bibtex_bib:
                        self.bib_file = match_bibtex_bib.group(1)
                        bib_engine = "bibtex"
                        Latex_compilation_times = 2

                target_name_bib = bib_engine

                bib_file_path = Path(self.bib_file)
                if not bib_file_path.exists() and bib_engine is not None:
                    Latex_compilation_times = 2

                new_cite_counter = self._generate_citation_counter()
                if old_cite_counter == new_cite_counter:
                    Latex_compilation_times = 0

                if (
                    re.search(
                        f"No file {self.project_name}.bbl.", self.out
                    )
                    or re.search("LaTeX Warning: Citation .* undefined", self.out)
                ):
                    Latex_compilation_times = 2

            elif re.search(r"\\bibcite", aux_content):
                new_cite_counter = self._generate_citation_counter()
                Latex_compilation_times = 0 if old_cite_counter == new_cite_counter else 1

        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")
        return bib_engine, Latex_compilation_times, target_name_bib

    def _index_changed_judgment(
        self, index_aux_content_dict_old, index_aux_infile, index_aux_outfile
    ):
        """判断单次索引是否需要重跑。

        三种情况返回 True：
          1. self.out 中出现 "No file {index_aux_infile}." → 从未跑过索引
          2. 当前输入文件存在且内容与快照不同 → 发生了变化
          3. 其他（输入/输出文件缺失）→ 视为首次，需要跑

        .get() 兜底：当快照 dict 里没有 key 时（快照阶段没捕获到该文件），
        视为快照内容与任何值都不同 → 触发重跑。
        """
        if re.search(f"No file {index_aux_infile}.", self.out):
            return True
        if not (
            Path(index_aux_infile).exists() and Path(index_aux_outfile).exists()
        ):
            return True
        file_content = _read_file_content(index_aux_infile)
        # 用 .get() 而非 dict[key]，避免快照/检测触发条件不一致导致 KeyError
        return index_aux_content_dict_old.get(index_aux_infile, "") != file_content

    def index_judgment(self, index_aux_content_dict_old):
        """检测阶段：统一遍历注册表，为命中的系统决定是否需要重跑索引。"""
        run_index_list_cmd: list[list[str]] = []

        for rule in _INDEX_REGISTRY:
            if not any(
                Path(f"{self.project_name}{ext}").exists()
                for ext in rule["triggers"]
            ):
                continue

            if rule["name"] == "glossaries":
                aux_path = Path(f"{self.project_name}.aux")
                if not aux_path.exists():
                    continue
                main_aux = _read_file_content(aux_path)
                for match in rule["pattern"].finditer(main_aux):
                    _name, ext_o, ext_i = match.groups()
                    make_index = self._index_changed_judgment(
                        index_aux_content_dict_old,
                        f"{self.project_name}{ext_i}",
                        f"{self.project_name}{ext_o}",
                    )
                    if make_index:
                        run_index_list_cmd.append(
                            rule["cmd_builder"](self.project_name, _name, ext_o, ext_i)
                        )
            else:
                ext_i = rule["fixed_in"]
                ext_o = rule["fixed_out"]
                make_index = self._index_changed_judgment(
                    index_aux_content_dict_old,
                    f"{self.project_name}{ext_i}",
                    f"{self.project_name}{ext_o}",
                )
                if make_index:
                    run_index_list_cmd.append(
                        rule["cmd_builder"](self.project_name)
                    )

        return run_index_list_cmd

    def prepare_aux_out_snapshots(self):
        aux_content_old = ""
        out_content_old = ""

        aux_paths = [
            Path(f"{self.project_name}.aux"),
            Path(self.auxdir) / f"{self.project_name}.aux",
        ]
        for aux_path in aux_paths:
            try:
                if aux_path.exists():
                    aux_content_old = _read_file_content(aux_path)
                    break
            except (OSError, UnicodeDecodeError):
                aux_content_old = ""

        out_paths = [
            Path(f"{self.project_name}.out"),
            Path(self.auxdir) / f"{self.project_name}.out",
        ]
        for out_path in out_paths:
            try:
                if out_path.exists():
                    out_content_old = _read_file_content(out_path)
                    break
            except (OSError, UnicodeDecodeError):
                out_content_old = ""

        return aux_content_old, out_content_old

    @staticmethod
    def _normalize_aux_like(content: str) -> str:
        if not content:
            return ""
        stripped_lines: list[str] = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("%"):
                continue
            comment_idx = -1
            for i, ch in enumerate(line):
                if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                    comment_idx = i
                    break
            if comment_idx >= 0:
                line = line[:comment_idx].strip()
                if not line:
                    continue
            if line in (r"\relax", "\\relax", "\\relax{}"):
                continue
            if re.fullmatch(r"\\bookmarksetup\{.*\}", line):
                continue
            if re.fullmatch(r"\\@outlinefile\s*\{.*\}", line):
                continue
            if re.fullmatch(r"\\gdef\s*\\@abspage@last\{.*\}", line) or re.fullmatch(r"\\xdef\s*\\@abspage@last\{.*\}", line):
                continue
            if re.fullmatch(r"\\global\\\@namedef\{ver@.*\}\{.*\}", line):
                continue
            stripped_lines.append(line)
        return "\n".join(stripped_lines)

    def aux_changed_judgment(self, aux_content_old):
        aux_paths = [
            Path(f"{self.project_name}.aux"),
            Path(self.auxdir) / f"{self.project_name}.aux",
        ]
        current = ""
        for aux_path in aux_paths:
            try:
                if aux_path.exists():
                    current = _read_file_content(aux_path)
                    break
            except (OSError, UnicodeDecodeError):
                return False
        return self._normalize_aux_like(current) != self._normalize_aux_like(aux_content_old)

    def out_changed_judgment(self, out_content_old):
        out_paths = [
            Path(f"{self.project_name}.out"),
            Path(self.auxdir) / f"{self.project_name}.out",
        ]
        current = ""
        for out_path in out_paths:
            try:
                if out_path.exists():
                    current = _read_file_content(out_path)
                    break
            except (OSError, UnicodeDecodeError):
                return False
        return self._normalize_aux_like(current) != self._normalize_aux_like(out_content_old)

    def log_has_rerun_warnings(self, log_path=None):
        log_content = ""

        if log_path is not None:
            candidate_paths = [Path(log_path)]
        else:
            candidate_paths = [
                Path(f"{self.project_name}.log"),
                Path(self.auxdir) / f"{self.project_name}.log",
            ]

        for candidate in candidate_paths:
            try:
                if candidate.exists():
                    log_content = _read_file_content(candidate)
                    break
            except (OSError, UnicodeDecodeError):
                log_content = ""

        for pattern in RERUN_LOG_PATTERNS:
            if pattern.search(log_content):
                return True
        return False

    def run_full_detection(self, *, cite_counter_old, toc_file_old, index_aux_content_old, aux_content_old, out_content_old):
        """六维状态检测聚合接口（FR-A5 Task 2.3）。一次性返回 (dims, next_extra, bib_engine, index_run_cmds, times_bib)。

        返回：
            dims: dict[str, int]          —— {"bib":0/1, "idx":0/1, "toc":0/1, "aux":0/1, "out":0/1, "log":0/1}
            next_extra: int               —— max(...) 仍需的额外 LaTeX 编译次数，供 compile_engine while 收敛判断
            bib_engine: str|None          —— BibTeX/Biber 引擎名，供 compile_engine 内 schedule 决定是否调用 compile_bib
            times_bib: int                —— bib 维度需要的 LaTeX 额外次数
            index_run_cmds: list          —— index 维度的实际执行命令列表，空列表表示无需执行索引编译
        """
        bib_engine, times_bib, _name_target = self.bib_judgment(cite_counter_old)
        index_run_cmds = self.index_judgment(index_aux_content_old)
        times_toc = 1 if self.toc_changed_judgment(toc_file_old) else 0
        aux = 1 if self.aux_changed_judgment(aux_content_old) else 0
        out = 1 if self.out_changed_judgment(out_content_old) else 0
        log = 1 if self.log_has_rerun_warnings() else 0

        dims = {
            "bib": 1 if times_bib > 0 else 0,
            "idx": 1 if len(index_run_cmds) > 0 else 0,
            "toc": times_toc,
            "aux": aux,
            "out": out,
            "log": log,
        }
        next_extra = max(
            times_bib,
            1 if index_run_cmds else 0,
            times_toc,
            aux,
            out,
            log,
        )
        return dims, next_extra, bib_engine, index_run_cmds, times_bib
