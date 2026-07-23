"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·····
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
LastEditTime : 2025-07-23 22:27:29 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/compile.py
Description  :
 -----------------------------------------------------------------------
"""

# -*- coding: utf-8 -*-
import re
import time
import shlex
import logging
import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional, List, Dict, Any

from rich.console import Console

from pytexmk.language import set_language
from pytexmk.additional import MoveRemoveOperation, MySubProcess, MainFileOperation
from pytexmk.toolchain import ToolchainManager
from pytexmk.log_analysis import LogAnalysis
from pytexmk.exceptions import (
    CompilationError,
    CompilationTimeoutError,
    ToolchainNotFoundError,
    FileOperationError,
)
from pytexmk.auxiliary_fun import setup_signal_handlers
from pytexmk.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_AUX_DIR,
    DEFAULT_COMPILE_TIMES,
    DEFAULT_TIMEOUT,
)

_ = set_language("compile")

console = Console(legacy_windows=False)

BIBER_PATTERN = re.compile(r"\\abx@aux@refcontext")
BIBTEX_PATTERN = re.compile(r"\\bibdata")

BIBER_BIB_PATTERN = re.compile(r"<bcf:datasource[^>]*>\s*(.*?)\s*</bcf:datasource>")
BIBTEX_BIB_PATTERN = re.compile(r"\\bibdata\{(.*)\}")

BIBER_CITE_PATTERN = re.compile(r"\\abx@aux@cite{.*?}\{(.*)\}")
BIBTEX_CITE_PATTERN = re.compile(r"\\citation\{(.*)\}")


class CompileLaTeX(object):
    def __init__(self, *args, **kwargs):
        self.out = ""
        self.err = ""
        self.logger = logging.getLogger(__name__)

        self._compat_mode = False
        self.project_name = ""
        self.compiled_program = "xelatex"
        self.out_files: List[str] = []
        self.aux_files: List[str] = []
        self.auxdir = DEFAULT_AUX_DIR
        self.outdir = DEFAULT_OUTPUT_DIR
        self.non_quiet = False
        self.bib_file = ""
        self.runs = DEFAULT_COMPILE_TIMES

        self.program = "xelatex"
        self.bibtex_tool: Optional[str] = None
        self.index_tool: Optional[str] = None
        self.run_count = DEFAULT_COMPILE_TIMES
        self.draft = False
        self.quiet = False
        self.shell_escape = True
        self.synctex = True
        self.timeout = DEFAULT_TIMEOUT
        self.auto_detect = True

        self.MRO = MoveRemoveOperation()
        self.MSP = MySubProcess()
        self.MFO = MainFileOperation()

        self.toolchain = ToolchainManager()
        self.engine = None
        self.bib_tool = None
        self.index_tool_instance = None
        self.dvipdfmx_tool = None

        self.compilation_errors: List[str] = []
        self.bib_needed = False
        self.index_needed = False
        self.glsmacros_needed = False
        self.nomencl_needed = False
        self.max_extra_passes = 2

        self.bib_judgment = False
        self.index_judgment = False

        self.start_time: Optional[datetime.datetime] = None
        self.end_time: Optional[datetime.datetime] = None
        self.start_doing: Optional[float] = None
        self.end_doing: Optional[float] = None

        self._parse_init_args(args, kwargs)

        self.toolchain.detect_all()

        if self.auto_detect and not self._compat_mode:
            self.engine = self.toolchain.get_engine(preference=self.program)
        else:
            engine_name = self.compiled_program.lower()
            self.engine = self.toolchain.get_engine(preference=engine_name)

        if self.bibtex_tool and not self._compat_mode:
            self.bib_tool = self.toolchain.get_bib_tool(self.bibtex_tool)

        if self.index_tool and not self._compat_mode:
            self.index_tool_instance = self.toolchain.get_index_tool(self.index_tool)

        self.dvipdfmx_tool = self.toolchain.dvipdfmx

        self.logger = logging.getLogger(__name__)

    def _parse_init_args(self, args: tuple, kwargs: dict):
        if len(args) >= 1 and isinstance(args[0], str):
            first_arg = args[0].lower()
            engine_names = ["xelatex", "pdflatex", "lualatex", "latex", "pdftex", "xetex", "luatex"]
            if first_arg not in engine_names and len(args) >= 2:
                self._compat_mode = True
                self.project_name = args[0]
                if len(args) >= 2:
                    self.compiled_program = args[1]
                    self.program = args[1].lower() if args[1] else "xelatex"
                if len(args) >= 3:
                    self.out_files = args[2] if args[2] else []
                if len(args) >= 4:
                    self.aux_files = args[3] if args[3] else []
                if len(args) >= 5:
                    self.outdir = args[4] if args[4] else DEFAULT_OUTPUT_DIR
                if len(args) >= 6:
                    self.auxdir = args[5] if args[5] else DEFAULT_AUX_DIR
                if len(args) >= 7:
                    self.non_quiet = args[6]
                return

        self.program = kwargs.get("program", "xelatex")
        self.bibtex_tool = kwargs.get("bibtex_tool", None)
        self.index_tool = kwargs.get("index_tool", None)
        self.outdir = kwargs.get("outdir", DEFAULT_OUTPUT_DIR)
        self.auxdir = kwargs.get("auxdir", DEFAULT_AUX_DIR)
        self.run_count = kwargs.get("run_count", DEFAULT_COMPILE_TIMES)
        self.runs = self.run_count
        self.draft = kwargs.get("draft", False)
        self.quiet = kwargs.get("quiet", False)
        self.shell_escape = kwargs.get("shell_escape", True)
        self.non_quiet = kwargs.get("non_quiet", False)
        self.synctex = kwargs.get("synctex", True)
        self.timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)
        self.auto_detect = kwargs.get("auto_detect", True)

        self.compiled_program = self.program
        if self.project_name:
            self.project_name = kwargs.get("project_name", self.project_name)
        else:
            self.project_name = kwargs.get("project_name", "")

    def _error_callback(self):
        try:
            if self.aux_files:
                self.MRO.move_specific_files(self.aux_files, ".", self.auxdir)
            if self.out_files:
                self.MRO.move_specific_files(self.out_files, ".", self.outdir)
        except Exception as e:
            self.logger.warning(_("文件清理失败: ") + str(e))

    def set_project_name(self, name: str):
        self.project_name = name

    def _check_exist(self) -> bool:
        tex_file = Path(f"{self.project_name}.tex")
        if not tex_file.exists():
            self.logger.error(_("文件不存在: ") + f"{self.project_name}.tex")
            raise FileOperationError(filepath=f"{self.project_name}.tex", message=_("主 .tex 文件不存在"))

        if self.engine:
            self.engine.ensure_available()

        if self.bib_tool:
            self.bib_tool.ensure_available()

        if self.index_tool_instance:
            self.index_tool_instance.ensure_available()

        return True

    def _run_tex(self, no_pdf: bool = False, run_num: Optional[int] = None) -> bool:
        if run_num is not None:
            console.print(
                f"\n[bold cyan]>>> {_('第')} {run_num} {_('次')} {self.engine.name} {_('编译')} <<<[/bold cyan]"
            )

        is_xelatex = self.engine.name == "xelatex"
        build_kwargs: Dict[str, Any] = {
            "project_name": self.project_name,
            "non_quiet": self.non_quiet,
            "shell_escape": self.shell_escape,
            "synctex": self.synctex,
        }

        if is_xelatex:
            build_kwargs["no_pdf"] = no_pdf

        cmd = self.engine.build_command(**build_kwargs)

        try:
            success, output = self.MSP.run_command(
                cmd,
                self.engine.name,
                cwd=None,
                timeout=self.timeout,
                error_callback=self._error_callback,
            )
            self.out = output
            self._analyze_logs_update_state()
            return True
        except CompilationTimeoutError:
            console.print(f"[bold red]{_('编译超时')} ({self.timeout}s)[/bold red]")
            self._error_callback()
            return False
        except CompilationError as e:
            console.print(f"[bold red]{_('编译失败')}: {e.message}[/bold red]")
            self._error_callback()
            self._view_log_current()
            return False

    def _run_bib(self) -> bool:
        if not self.bib_tool:
            console.print(f"[yellow]{_('未配置参考文献工具，跳过 bib 编译')}[/yellow]")
            return False

        quiet = not self.non_quiet
        cmd = self.bib_tool.build_command(
            project_name=self.project_name,
            quiet=quiet,
        )

        try:
            success, output = self.MSP.run_command(
                cmd,
                self.bib_tool.name,
                cwd=None,
                timeout=self.timeout,
                error_callback=self._error_callback,
            )
            self.out = output
            return True
        except CompilationTimeoutError:
            console.print(f"[bold red]{_('Bib 编译超时')}[/bold red]")
            return False
        except CompilationError as e:
            console.print(f"[bold red]{_('Bib 编译失败')}: {e.message}[/bold red]")
            return False

    def _run_index(self, index_type: str = "makeidx") -> bool:
        index_tool = self.index_tool_instance
        if not index_tool:
            index_tool = self.toolchain.get_index_tool("makeindex")

        build_kwargs: Dict[str, Any] = {
            "project_name": self.project_name,
        }

        if index_type == "nomencl":
            if index_tool.name == "xindy":
                build_kwargs["module"] = "nomencl"
                build_kwargs["out_ext"] = "nls"
                build_kwargs["in_ext"] = "nlo"
                build_kwargs["language"] = "general"
                build_kwargs["codepage"] = "utf8"
            else:
                build_kwargs["style_file"] = "nomencl.ist"
                build_kwargs["out_ext"] = "nls"
                build_kwargs["in_ext"] = "nlo"
        elif index_type == "glossaries":
            if index_tool.name == "xindy":
                build_kwargs["out_ext"] = "gls"
                build_kwargs["in_ext"] = "glo"
                build_kwargs["language"] = "general"
                build_kwargs["codepage"] = "utf8"
            else:
                build_kwargs["style_file"] = f"{self.project_name}.ist"
                build_kwargs["out_ext"] = "gls"
                build_kwargs["in_ext"] = "glo"
        else:
            build_kwargs["out_ext"] = "ind"
            build_kwargs["in_ext"] = "idx"

        cmd = index_tool.build_command(**build_kwargs)

        try:
            success, output = self.MSP.run_command(
                cmd,
                index_tool.name,
                cwd=None,
                timeout=self.timeout,
                error_callback=self._error_callback,
            )
            self.out = output
            return True
        except CompilationTimeoutError:
            console.print(f"[bold red]{_('索引编译超时')}[/bold red]")
            return False
        except CompilationError as e:
            console.print(f"[bold red]{_('索引编译失败')}: {e.message}[/bold red]")
            return False

    def _run_dvipdfmx(self) -> bool:
        if not self.dvipdfmx_tool or not self.dvipdfmx_tool.available:
            return False

        xdv_file = Path(f"{self.project_name}.xdv")
        pdf_file = Path(f"{self.project_name}.pdf")
        if pdf_file.exists() and not xdv_file.exists():
            self.logger.info(_("PDF 文件已存在，跳过 dvipdfmx"))
            return True

        if not xdv_file.exists():
            self.logger.info(_("未找到 xdv 文件，跳过 dvipdfmx"))
            return True

        quiet = not self.non_quiet
        cmd = self.dvipdfmx_tool.build_command(
            project_name=self.project_name,
            quiet=quiet,
        )

        try:
            success, output = self.MSP.run_command(
                cmd,
                "dvipdfmx",
                cwd=None,
                timeout=self.timeout,
                error_callback=self._error_callback,
            )
            self.out = output
            return True
        except CompilationTimeoutError:
            console.print(f"[bold red]{_('dvipdfmx 超时')}[/bold red]")
            return False
        except CompilationError as e:
            console.print(f"[bold red]{_('dvipdfmx 失败')}: {e.message}[/bold red]")
            return False

    def _analyze_logs(self) -> LogAnalysis:
        log_analysis = LogAnalysis(self.project_name)
        log_analysis.parse_all()

        self.bib_needed = log_analysis.needs_recompile_bib()
        self.index_needed = log_analysis.needs_recompile_index()
        self.nomencl_needed = any(Path(f"{self.project_name}{ext}").exists() for ext in [".nlo"])
        self.glsmacros_needed = any(Path(f"{self.project_name}{ext}").exists() for ext in [".glo", ".acn", ".slo"])

        return log_analysis

    def _analyze_logs_update_state(self):
        try:
            log_analysis = LogAnalysis(self.project_name)
            log_analysis.parse_all()
            self.bib_needed = log_analysis.needs_recompile_bib()
            self.index_needed = log_analysis.needs_recompile_index()
        except Exception as e:
            self.logger.debug(_("日志分析失败: ") + str(e))

    def _view_log_current(self):
        try:
            log_analysis = LogAnalysis(self.project_name)
            log_analysis.parse_all()
            log_analysis.view_log()
        except Exception as e:
            self.logger.warning(_("日志展示失败: ") + str(e))

    def _move_files(self):
        if self.auxdir:
            Path(self.auxdir).mkdir(parents=True, exist_ok=True)
        if self.outdir:
            Path(self.outdir).mkdir(parents=True, exist_ok=True)

        if self.aux_files:
            self.MRO.move_specific_files(self.aux_files, ".", self.auxdir)
        else:
            aux_patterns = [
                re.compile(
                    r".*\.(aux|log|out|toc|lof|lot|bbl|blg|bcf|run\.xml|fls|fdb_latexmk|synctex\.gz|nav|snm|vrb|idx|ilg|ind|glo|gls|glg|ist|acn|acr|alg|loe|loa|lol|xdv)$"
                ),
            ]
            self.MRO.move_matched_files(aux_patterns, ".", self.auxdir)

        if self.out_files:
            self.MRO.move_specific_files(self.out_files, ".", self.outdir)
        else:
            out_patterns = [
                re.compile(r".*\.(pdf|dvi|ps)$"),
            ]
            self.MRO.move_matched_files(out_patterns, ".", self.outdir)

    def compile_tex(self):
        if self._compat_mode:
            return self._compile_tex_single_compat()

        return self._compile_tex_full()

    def _compile_tex_single_compat(self):
        build_kwargs: Dict[str, Any] = {
            "project_name": self.project_name,
            "non_quiet": self.non_quiet,
        }
        if self.compiled_program.lower() == "xelatex":
            build_kwargs["no_pdf"] = True

        cmd = self.engine.build_command(**build_kwargs)

        success, output = self.MSP.run_command(
            cmd,
            self.compiled_program,
            error_callback=self._error_callback,
        )
        self.out = output

    def _compile_tex_full(self):
        setup_signal_handlers()

        self.start_time = datetime.datetime.now()
        self.start_doing = time.time()

        console.print("\n" + "=" * 78, style="blue bold")
        console.print(
            f"[bold red on white]| {_('开始执行 PyTeXMK 编译调度')} |[/bold red on white]",
            style="red on white bold",
            justify="center",
        )
        console.print("=" * 78 + "\n", style="blue bold")

        try:
            self._check_exist()
        except (FileOperationError, ToolchainNotFoundError) as e:
            console.print(f"[bold red]{_('检查失败')}: {e.message}[/bold red]")
            raise

        is_xelatex = self.engine.name == "xelatex"

        if self.run_count == 0:
            console.print(f"[yellow]{_('run_count=0，仅执行文件清理/移动')}[/yellow]")
            self._move_files()
            self._finalize()
            return

        first_no_pdf = is_xelatex
        last_no_pdf = False if is_xelatex else None

        if not self._run_tex(no_pdf=first_no_pdf if is_xelatex else False, run_num=1):
            self._finalize()
            return

        self._analyze_logs()

        need_bib = self.bib_needed
        need_index = self.index_needed or self.nomencl_needed or self.glsmacros_needed

        if self.run_count >= 3 and need_bib:
            console.print(f"\n[bold yellow]{_('检测到需要参考文献编译，执行 bib')}[/bold yellow]")
            if not self._run_bib():
                console.print(f"[yellow]{_('Bib 编译失败，继续后续流程')}[/yellow]")

        if need_index:
            console.print(f"\n[bold yellow]{_('检测到需要索引编译，执行 index')}[/bold yellow]")
            if self.nomencl_needed:
                self._run_index("nomencl")
            if self.glsmacros_needed:
                self._run_index("glossaries")
            if self.index_needed:
                self._run_index("makeidx")

        for i in range(2, self.run_count + 1):
            is_last = i == self.run_count
            no_pdf = last_no_pdf if is_last else (first_no_pdf if is_xelatex else False)
            if not self._run_tex(no_pdf=no_pdf, run_num=i):
                self._finalize()
                return

        extra_pass_count = 0
        while extra_pass_count < self.max_extra_passes:
            log_analysis = self._analyze_logs()

            if log_analysis.has_fatal_errors():
                console.print(f"[bold red]{_('检测到致命错误，停止智能补编')}[/bold red]")
                break

            did_action = False

            if log_analysis.needs_recompile_bib() and self.bib_tool:
                extra_pass_count += 1
                console.print(
                    f"\n[bold yellow]{_('智能补编：检测到未定义引用或 bbl 缺失，执行第')} {extra_pass_count} {_('次补编（bib + tex）')}[/bold yellow]"
                )
                if not self._run_bib():
                    break
                if not self._run_tex(no_pdf=False):
                    break
                did_action = True

            elif log_analysis.needs_recompile_index() and self.index_tool_instance:
                extra_pass_count += 1
                console.print(
                    f"\n[bold yellow]{_('智能补编：检测到索引问题，执行第')} {extra_pass_count} {_('次补编（index + tex）')}[/bold yellow]"
                )
                if not self._run_index("makeidx"):
                    break
                if not self._run_tex(no_pdf=False):
                    break
                did_action = True

            elif log_analysis.needs_extra_pass():
                extra_pass_count += 1
                console.print(
                    f"\n[bold yellow]{_('智能补编：检测到交叉引用需要重新计算，执行第')} {extra_pass_count} {_('次补编（tex）')}[/bold yellow]"
                )
                if not self._run_tex(no_pdf=False):
                    break
                did_action = True

            if not did_action:
                break

        if is_xelatex:
            self._run_dvipdfmx()

        console.print("\n" + "=" * 78, style="green bold")

        self._finalize()

    def _finalize(self):
        self.end_time = datetime.datetime.now()
        self.end_doing = time.time()

        if self.start_time and self.end_time:
            elapsed = (self.end_time - self.start_time).total_seconds()
            console.print(f"\n[bold green]{_('编译完成')}[/bold green] [time]({_('总耗时')}: {elapsed:.2f}s)[/time]")

        console.print("=" * 78 + "\n", style="green bold")

    def prepare_LaTeX_output_files(self):
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            cite_counter = self._generate_citation_counter()
            index_aux_content_dict_old = self._index_aux_content_get()
        else:
            cite_counter = {f"{self.project_name}.aux": defaultdict(int)}
            index_aux_content_dict_old = dict()

        toc_file_path = Path(f"{self.project_name}.toc")
        if toc_file_path.exists():
            with open(toc_file_path, "r", encoding="utf-8") as fobj:
                toc_file = fobj.read()
        else:
            toc_file = ""

        return cite_counter, toc_file, index_aux_content_dict_old

    def _generate_citation_counter(self):
        cite_counter = dict()
        file_name = f"{self.project_name}.aux"
        with open(file_name, "r", encoding="utf-8") as fobj:
            main_aux_content = fobj.read()
        cite_counter[file_name] = _count_citations(file_name)

        for match in re.finditer(r"\\@input\{(.*.aux)\}", main_aux_content):
            file_name = match.groups()[0]
            try:
                counter = _count_citations(file_name)
            except IOError:
                self.logger.info(_("文件不存在或无法读取,跳过文件: %(args)s") % {"args": file_name})
                pass
            else:
                cite_counter[file_name] = counter

        return cite_counter

    def _index_aux_content_get(self):
        file_name = Path(f"{self.project_name}.aux")
        index_aux_content_dict_old = dict()

        if file_name.exists():
            if any(Path(f"{self.project_name}{ext}").exists() for ext in [".glo", ".acn", ".slo"]):
                with open(file_name, "r", encoding="utf-8") as fobj:
                    main_aux = fobj.read()
                pattern = r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
                for match in re.finditer(pattern, main_aux):
                    name, ext_o, ext_i = match.groups()
                    if Path(f"{self.project_name}{ext_i}").exists() and Path(f"{self.project_name}{ext_o}").exists():
                        with open(Path(f"{self.project_name}{ext_o}"), "r", encoding="utf-8") as fobj:
                            index_ext_i_content = fobj.read()
                        index_aux_content_dict_old[f"{self.project_name}.{ext_i}"] = index_ext_i_content

            if Path(f"{self.project_name}.nlo").exists():
                if Path(f"{self.project_name}.nlo").exists() and Path(f"{self.project_name}.nls").exists():
                    with open(Path(f"{self.project_name}.nlo"), "r", encoding="utf-8") as fobj:
                        index_ext_i_content = fobj.read()
                    index_aux_content_dict_old[f"{self.project_name}.nlo"] = index_ext_i_content

            if Path(f"{self.project_name}.idx").exists():
                if Path(f"{self.project_name}.idx").exists() and Path(f"{self.project_name}.ind").exists():
                    with open(Path(f"{self.project_name}.idx"), "r", encoding="utf-8") as fobj:
                        index_ext_i_content = fobj.read()
                    index_aux_content_dict_old[f"{self.project_name}.idx"] = index_ext_i_content
        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")

        return index_aux_content_dict_old

    def toc_changed_judgment(self, toc_file):
        file_name = Path(self.project_name).with_suffix(".toc")
        if file_name.exists():
            with open(file_name, "r", encoding="utf-8") as fobj:
                if fobj.read() != toc_file:
                    return True

    def bib_judgment(self, old_cite_counter):
        bib_engine = None
        name_target = None
        Latex_compilation_times = 0
        print_bib = ""
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            with aux_file_path.open("r", encoding="utf-8") as fobj:
                aux_content = fobj.read()
            match_biber = BIBER_PATTERN.search(aux_content)
            match_bibtex = BIBTEX_PATTERN.search(aux_content)
            if match_biber or match_bibtex:
                if match_biber:
                    bcf_file_path = Path(f"{self.project_name}.bcf")
                    with bcf_file_path.open("r", encoding="utf-8") as fobj:
                        match_biber_bib = BIBER_BIB_PATTERN.search(fobj.read())
                    if not match_biber_bib:
                        print_bib = _("未设置参考文献数据库文件: ") + self.bib_file
                    else:
                        self.bib_file = match_biber_bib.group(1)
                        bib_engine = "biber"
                        Latex_compilation_times = 2

                elif match_bibtex:
                    match_bibtex_bib = BIBTEX_BIB_PATTERN.search(aux_content)
                    if not match_bibtex_bib:
                        print_bib = _("未设置参考文献数据库文件: ") + self.bib_file
                    else:
                        self.bib_file = match_bibtex_bib.group(1)
                        bib_engine = "bibtex"
                        Latex_compilation_times = 2

                print_bib = bib_engine + _("编译参考文献")
                name_target = bib_engine

                bib_file_path = Path(self.bib_file)
                if not bib_file_path.exists():
                    print_bib = _("未找到参考文献数据库文件: ") + self.bib_file
                    Latex_compilation_times = 2

                new_cite_counter = self._generate_citation_counter()
                if old_cite_counter == new_cite_counter:
                    print_bib = _("参考文献引用数量没有变化")
                    Latex_compilation_times = 0

                if re.search(f"No file {self.project_name}.bbl.", self.out) or re.search(
                    "LaTeX Warning: Citation .* undefined", self.out
                ):
                    print_bib = _("LaTeX 编译日志中存在 bbl 文件缺失或引用未定义的提示")
                    Latex_compilation_times = 2

            elif re.search(r"\\bibcite", aux_content):
                print_bib = _("thebibliography 环境实现排版")
                Latex_compilation_times = 1

            else:
                print_bib = _("没有引用参考文献或编译工具不属于 bibtex 或 biber")
        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")

        self.bib_judgment = bib_engine is not None and Latex_compilation_times > 0
        return bib_engine, Latex_compilation_times, print_bib, name_target

    def compile_bib(self, bib_engine):
        if not self.bib_tool or self.bib_tool.name != bib_engine:
            self.bib_tool = self.toolchain.get_bib_tool(bib_engine)
        quiet = not self.non_quiet
        cmd = self.bib_tool.build_command(
            project_name=self.project_name,
            quiet=quiet,
        )

        success, output = self.MSP.run_command(
            cmd,
            bib_engine,
            error_callback=self._error_callback,
        )

    def _index_changed_judgment(self, index_aux_content_dict_old, index_aux_infile, index_aux_outfile):
        make_index = False
        if re.search(f"No file {index_aux_infile}.", self.out):
            print_index = _("重新编译索引,因日志文件提示没有输入文件")
            make_index = True
        elif Path(index_aux_infile).exists() and Path(index_aux_outfile).exists():
            with open(index_aux_infile, "r", encoding="utf-8") as fobj:
                file_content = fobj.read()
            if file_content is not None:
                if str(index_aux_content_dict_old.get(index_aux_infile, "")) != file_content:
                    print_index = _("重新编译索引,因词汇表文件内容发生变化")
                    make_index = True
                else:
                    print_index = _("无需编译索引,因词汇表文件内容没有变化")
            else:
                print_index = _("无需编译索引,因没有索引内容")
        else:
            make_index = True
            print_index = (
                _("重新编译索引,因以下索引辅助文件之一存在缺失: ") + f"{index_aux_infile}, {index_aux_outfile}"
            )
        return print_index, make_index

    def index_judgment(self, index_aux_content_dict_old):
        file_name = Path(f"{self.project_name}.aux")
        run_index_list_cmd = []
        print_index = ""

        if any(Path(f"{self.project_name}{ext}").exists() for ext in [".glo", ".acn", ".slo"]):
            if file_name.exists():
                with open(file_name, "r", encoding="utf-8") as fobj:
                    main_aux = fobj.read()
                pattern = r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
                for match in re.finditer(pattern, main_aux):
                    name, ext_o, ext_i = match.groups()
                    idx_print, make_index = self._index_changed_judgment(
                        index_aux_content_dict_old, f"{self.project_name}{ext_i}", f"{self.project_name}{ext_o}"
                    )
                    if make_index:
                        run_index_list_cmd.append(
                            [
                                f"glossaries {name}",
                                f"makeindex -s {self.project_name}.ist -o {self.project_name}{ext_o} {self.project_name}{ext_i}",
                            ]
                        )

        if Path(f"{self.project_name}.nlo").exists():
            print_index, make_index = self._index_changed_judgment(
                index_aux_content_dict_old, f"{self.project_name}.nlo", f"{self.project_name}.nls"
            )
            if make_index:
                run_index_list_cmd.append(
                    ["nomencl", f"makeindex -s nomencl.ist -o {self.project_name}.nls {self.project_name}.nlo"]
                )

        elif Path(f"{self.project_name}.idx").exists():
            print_index, make_index = self._index_changed_judgment(
                index_aux_content_dict_old, f"{self.project_name}.idx", f"{self.project_name}.ind"
            )
            if make_index:
                run_index_list_cmd.append(["makeidx", f"makeindex {self.project_name}.idx"])
        else:
            print_index = _("使用 glossaries、nomencl 和 makeidx 以外宏包或未设置索引,因此不编译索引")

        self.index_judgment = len(run_index_list_cmd) > 0
        return print_index, run_index_list_cmd

    def compile_index(self, cmd):
        name_target = f"{cmd[0]}"
        options = shlex.split(cmd[1])
        success, output = self.MSP.run_command(
            options,
            cmd[0],
            error_callback=self._error_callback,
        )
        return name_target

    def compile_xdv(self):
        quiet = not self.non_quiet
        options = self.toolchain.dvipdfmx.build_command(
            project_name=self.project_name,
            quiet=quiet,
        )

        success, output = self.MSP.run_command(
            options,
            "dvipdfmx",
            error_callback=self._error_callback,
        )

    def move_file(self):
        self._move_files()

    def clean(self):
        if self.auxdir and Path(self.auxdir).exists():
            import shutil

            shutil.rmtree(self.auxdir, ignore_errors=True)
        if self.outdir and Path(self.outdir).exists():
            import shutil

            shutil.rmtree(self.outdir, ignore_errors=True)

    def set_outdir(self, outdir):
        self.outdir = outdir

    def set_auxdir(self, auxdir):
        self.auxdir = auxdir

    def set_non_quiet(self, non_quiet):
        self.non_quiet = non_quiet

    def set_run_count(self, run_count):
        self.run_count = run_count
        self.runs = run_count

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_engine(self, program):
        self.program = program
        self.compiled_program = program
        self.engine = self.toolchain.get_engine(preference=program.lower())

    def view_log(self):
        self._view_log_current()


def _count_citations(file_name):
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
    return counter
