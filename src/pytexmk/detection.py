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

BIBER_CITE_PATTERN = re.compile(
    r"\\abx@aux@cite{.*?}\{(.*)\}"
)
BIBTEX_CITE_PATTERN = re.compile(r"\\citation\{(.*)\}")
THEBIB_CITE_PATTERN = re.compile(r"\\bibcite\{(.*?)\}")

RERUN_LOG_PATTERNS = [
    re.compile(r"LaTeX Warning: There were undefined references\."),
    re.compile(r"LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\."),
    re.compile(r"Package lastpage Warning: Rerun to get the references right"),
    re.compile(r"Package rerunfilecheck Warning: .* Rerun"),
    re.compile(r"LaTeX Warning: Citation .* undefined"),
    re.compile(r"LaTeX Warning: There were multiply-defined labels\."),
]


def _count_citations(file_name):
    _ = set_language("detection")
    counter = defaultdict(int)

    with open(file_name, "r", encoding="utf-8") as aux_file:
        aux_content = aux_file.read()
    match = BIBER_CITE_PATTERN.search(aux_content)
    if match:
        for match in BIBER_CITE_PATTERN.finditer(aux_content):
            name = match.groups()[0]
            counter[name] += 1
    match = BIBTEX_CITE_PATTERN.search(aux_content)
    if match:
        for match in BIBTEX_CITE_PATTERN.finditer(aux_content):
            name = match.groups()[0]
            counter[name] += 1
    match = THEBIB_CITE_PATTERN.search(aux_content)
    if match:
        for match in THEBIB_CITE_PATTERN.finditer(aux_content):
            name = match.groups()[0]
            counter[name] += 1
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
        _ = set_language("detection")
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            cite_counter = self._generate_citation_counter()
            index_aux_content_dict_old = self._index_aux_content_get()
        else:
            cite_counter = {f"{self.project_name}.aux": defaultdict(int)}
            index_aux_content_dict_old = {}
        toc_file_path = Path(f"{self.project_name}.toc")
        if toc_file_path.exists():
            with open(toc_file_path, "r", encoding="utf-8") as fobj:
                toc_file = fobj.read()
        else:
            toc_file = ""

        return cite_counter, toc_file, index_aux_content_dict_old

    def _generate_citation_counter(self):
        _ = set_language("detection")
        cite_counter = {}
        file_name = f"{self.project_name}.aux"
        with open(file_name, "r", encoding="utf-8") as fobj:
            main_aux_content = fobj.read()
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
        _ = set_language("detection")
        file_name = Path(
            f"{self.project_name}.aux"
        )
        index_aux_content_dict_old = {}

        if file_name.exists():
            if any(
                Path(f"{self.project_name}{ext}").exists()
                for ext in [".glo", ".acn", ".slo"]
            ):
                with open(file_name, "r", encoding="utf-8") as fobj:
                    main_aux = fobj.read()
                pattern = r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
                for match in re.finditer(
                    pattern, main_aux
                ):
                    _name, ext_o, ext_i = (
                        match.groups()
                    )
                    if (
                        Path(f"{self.project_name}{ext_i}").exists()
                        and Path(f"{self.project_name}{ext_o}").exists()
                    ):
                        with open(
                            Path(f"{self.project_name}{ext_o}"), "r", encoding="utf-8"
                        ) as fobj:
                            index_ext_i_content = fobj.read()
                        index_aux_content_dict_old[f"{self.project_name}.{ext_i}"] = (
                            index_ext_i_content
                        )
            if Path(f"{self.project_name}.nlo").exists() and (
                Path(f"{self.project_name}.nlo").exists()
                and Path(f"{self.project_name}.nls").exists()
            ):
                with open(
                    Path(f"{self.project_name}.nlo"), "r", encoding="utf-8"
                ) as fobj:
                    index_ext_i_content = fobj.read()
                index_aux_content_dict_old[f"{self.project_name}.nlo"] = (
                    index_ext_i_content
                )

            if Path(f"{self.project_name}.idx").exists() and (
                Path(f"{self.project_name}.idx").exists()
                and Path(f"{self.project_name}.ind").exists()
            ):
                with open(
                    Path(f"{self.project_name}.idx"), "r", encoding="utf-8"
                ) as fobj:
                    index_ext_i_content = fobj.read()
                index_aux_content_dict_old[f"{self.project_name}.idx"] = (
                    index_ext_i_content
                )
        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")

        return index_aux_content_dict_old

    def toc_changed_judgment(self, toc_file):
        _ = set_language("detection")
        file_name = Path(self.project_name).with_suffix(
            ".toc"
        )
        if file_name.exists():
            with open(file_name, "r", encoding="utf-8") as fobj:
                if fobj.read() != toc_file:
                    return True

    def bib_judgment(self, old_cite_counter):
        _ = set_language("detection")
        bib_engine = None
        target_name_bib = None
        Latex_compilation_times = 0
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            with aux_file_path.open("r", encoding="utf-8") as fobj:
                aux_content = fobj.read()
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
                    with bcf_file_path.open(
                        "r", encoding="utf-8"
                    ) as fobj:
                        match_biber_bib = BIBER_BIB_PATTERN.search(
                            fobj.read()
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
        _ = set_language("detection")
        make_index = False
        if re.search(
            f"No file {index_aux_infile}.", self.out
        ):
            make_index = True
        elif (
            Path(index_aux_infile).exists() and Path(index_aux_outfile).exists()
        ):
            with open(index_aux_infile, "r", encoding="utf-8") as fobj:
                file_content = fobj.read()
            if file_content is not None:
                if (
                    str(index_aux_content_dict_old[index_aux_infile]) != file_content
                ):
                    make_index = True
        else:
            make_index = True
        return make_index

    def index_judgment(self, index_aux_content_dict_old):
        _ = set_language("detection")
        file_name = Path(
            f"{self.project_name}.aux"
        )
        run_index_list_cmd = []
        if any(
            Path(f"{self.project_name}{ext}").exists()
            for ext in [".glo", ".acn", ".slo"]
        ):
            with open(file_name, "r", encoding="utf-8") as fobj:
                main_aux = fobj.read()
            pattern = r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
            for match in re.finditer(
                pattern, main_aux
            ):
                name, ext_o, ext_i = (
                    match.groups()
                )
                make_index = self._index_changed_judgment(
                    index_aux_content_dict_old,
                    f"{self.project_name}{ext_i}",
                    f"{self.project_name}{ext_o}",
                )
                if make_index:
                    run_index_list_cmd.append(
                        [
                            f"glossaries {name}",
                            f"makeindex -s {self.project_name}.ist -o {self.project_name}{ext_o} {self.project_name}{ext_i}",
                        ]
                    )
        elif Path(f"{self.project_name}.nlo").exists():
            make_index = self._index_changed_judgment(
                index_aux_content_dict_old,
                f"{self.project_name}.nlo",
                f"{self.project_name}.nls",
            )
            if make_index:
                run_index_list_cmd.append(
                    [
                        "nomencl",
                        f"makeindex -s nomencl.ist -o {self.project_name}.nls {self.project_name}.nlo",
                    ]
                )

        elif Path(f"{self.project_name}.idx").exists():
            make_index = self._index_changed_judgment(
                index_aux_content_dict_old,
                f"{self.project_name}.idx",
                f"{self.project_name}.ind",
            )
            if make_index:
                run_index_list_cmd.append(
                    ["makeidx", f"makeindex {self.project_name}.idx"]
                )
        return run_index_list_cmd

    def prepare_aux_out_snapshots(self):
        _ = set_language("detection")
        aux_content_old = ""
        out_content_old = ""

        aux_paths = [
            Path(f"{self.project_name}.aux"),
            Path(self.auxdir) / f"{self.project_name}.aux",
        ]
        for aux_path in aux_paths:
            try:
                if aux_path.exists():
                    with open(aux_path, "r", encoding="utf-8") as fobj:
                        aux_content_old = fobj.read()
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
                    with open(out_path, "r", encoding="utf-8") as fobj:
                        out_content_old = fobj.read()
                    break
            except (OSError, UnicodeDecodeError):
                out_content_old = ""

        return aux_content_old, out_content_old

    @staticmethod
    def _normalize_aux_like(content: str) -> str:
        _ = set_language("detection")
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
        _ = set_language("detection")
        aux_paths = [
            Path(f"{self.project_name}.aux"),
            Path(self.auxdir) / f"{self.project_name}.aux",
        ]
        current = ""
        for aux_path in aux_paths:
            try:
                if aux_path.exists():
                    with open(aux_path, "r", encoding="utf-8") as fobj:
                        current = fobj.read()
                    break
            except (OSError, UnicodeDecodeError):
                return False
        return self._normalize_aux_like(current) != self._normalize_aux_like(aux_content_old)

    def out_changed_judgment(self, out_content_old):
        _ = set_language("detection")
        out_paths = [
            Path(f"{self.project_name}.out"),
            Path(self.auxdir) / f"{self.project_name}.out",
        ]
        current = ""
        for out_path in out_paths:
            try:
                if out_path.exists():
                    with open(out_path, "r", encoding="utf-8") as fobj:
                        current = fobj.read()
                    break
            except (OSError, UnicodeDecodeError):
                return False
        return self._normalize_aux_like(current) != self._normalize_aux_like(out_content_old)

    def log_has_rerun_warnings(self, log_path=None):
        _ = set_language("detection")
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
                    with open(candidate, "r", encoding="utf-8") as fobj:
                        log_content = fobj.read()
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
