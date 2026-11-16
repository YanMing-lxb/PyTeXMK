"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888·888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【实际 subprocess 级编译执行 + 对检测的最小必要组合调用】。
  具体职责：
    1. LaTeX / BibTeX / Biber / bib2gls / MakeIndex / Glossaries / dvipdfmx 的真实 subprocess 调用。
    2. 原生目录构建（-output-directory）：辅助文件不再往返搬运。
  调用依赖关系拓扑：
    compile_engine.RUN 实例化 CompileLaTeX 执行实际编译 + 检测编排。
    CompileLaTeX 通过 self.detector 持有 CompilationDetector 引用，检测方法直接走 .detector.*。
  下游依赖：
    subprocess_runner / file_ops / version / pytexlogs / detection / diagnostics。
"""

import logging
import re
import shlex
from pathlib import Path

from pytexmk.detection import BibEngine
from pytexmk.diagnostics import report_failure
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_COMPILE_FAILED, exit_pytexmk
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError
from pytexmk.ui_theme import console

_ = set_language("compile")

#: 触发 ``-shell-escape`` 的宏包/命令特征。
#: 默认不再无条件开启：只有源码真的用到这些能力时才开，避免给任意 .tex
#: 默认授予执行外部程序的权限（C5）。
SHELL_ESCAPE_PATTERNS = (
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{minted\}"),
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{pythontex\}"),
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{shellesc\}"),
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{svg\}"),
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{gnuplottex\}"),
    re.compile(r"\\tikzexternalize"),
    re.compile(r"\\write18"),
    re.compile(r"\\directlua"),
    re.compile(r"\\py\b|\\(pyc|pyb|pys)"),
)


def detect_shell_escape(tex_files) -> bool:
    """扫描源码判断是否需要 ``-shell-escape``。"""
    for path in tex_files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(pattern.search(text) for pattern in SHELL_ESCAPE_PATTERNS):
            return True
    return False


class CompileLaTeX:
    def __init__(
        self,
        project_name,
        compiled_program,
        out_files,
        aux_files,
        outdir,
        auxdir,
        non_quiet,
        shell_escape=False,
        native=False,
        extra_args=None,
        interaction=None,
        jobname=None,
        max_extra_args=None,
        write_report=False,
        report_path=None,
        include_only=None,
    ):
        self.logger = logging.getLogger(__name__)

        self.project_name = project_name
        self.compiled_program = compiled_program
        self.out_files = out_files
        self.aux_files = aux_files
        self.auxdir = auxdir
        self.outdir = outdir
        self.non_quiet = non_quiet
        self.shell_escape = bool(shell_escape)
        self.native = bool(native)
        self.extra_args = list(extra_args or [])
        self.interaction = interaction
        self.jobname = jobname or project_name
        self.max_extra_args = max_extra_args
        self.write_report = bool(write_report)
        self.report_path = report_path
        self.include_only = include_only

        self.MRO = FileMoveRemoveManager()
        self.MSP = MySubProcess(outdir, auxdir, self.jobname)

        from .detection import CompilationDetector
        self.detector = CompilationDetector(
            project_name=self.project_name,
            compiled_program=self.compiled_program,
            out_files=self.out_files,
            aux_files=self.aux_files,
            outdir=self.outdir,
            auxdir=self.auxdir,
            non_quiet=self.non_quiet,
            MRO=self.MRO,
            jobname=self.jobname,
        )

    # ------------------------------------------------------------------ 失败收尾

    def _on_subprocess_failure(self):
        """统一处理 SubprocessFailedError：打印可执行诊断后退出。"""
        report_failure(
            self.jobname,
            self.auxdir,
            root_file=f"{self.project_name}.tex",
            translate_fn=set_language("log_parser"),
            write_report=self.write_report,
            report_path=self.report_path,
        )
        if self.write_report:
            destination = self.report_path or str(
                Path(self.auxdir) / f"{self.jobname}.pytexmk-report.json"
            )
            console.print(f"[dim]诊断报告: {destination}[/dim]")
        exit_pytexmk(EXIT_COMPILE_FAILED)

    # ------------------------------------------------------------------ 命令构造

    def _interaction_flag(self) -> str:
        if self.interaction:
            return f"-interaction={self.interaction}"
        return "-interaction=nonstopmode" if self.non_quiet else "-interaction=batchmode"

    def _latex_command(self) -> list[str]:
        command = [
            self.compiled_program.lower(),
            "-recorder",  # 产出 .fls：依赖收集（投稿打包/PDF 修复范围）都靠它
            "-file-line-error",
            "-halt-on-error",
            "-synctex=1",
            self._interaction_flag(),
        ]
        if self.shell_escape:
            command.insert(1, "-shell-escape")
        if self.native:
            command.append(f"-output-directory={Path(self.auxdir).resolve()}")
        if self.jobname and self.jobname != self.project_name:
            command.append(f"-jobname={self.jobname}")
        elif self.native:
            command.append(f"-jobname={self.project_name}")
        if not self.native and self.compiled_program == "XeLaTeX":
            # 传统两段式：先出 .xdv 再 dvipdfmx。原生构建直接出 PDF，省掉这一步
            command.append("-no-pdf")
        command.extend(self.extra_args)
        if self.include_only:
            # 部分编译：命令行执行 \includeonly 后 \input 主文件；不改用户源码。
            command.append(
                f"\\includeonly{{{self.include_only}}}\\input{{{self.project_name}.tex}}"
            )
        else:
            command.append(f"{self.project_name}.tex")
        return command

    def compile_tex(self):
        command = self._latex_command()
        try:
            self.MSP.run_command(
                command, self.out_files, self.aux_files, self.compiled_program
            )
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def compile_bib(self, bib_engine):
        if bib_engine == BibEngine.BIBER:
            command = ["biber"]
            if not self.non_quiet:
                command.append("-quiet")
            if self.native:
                command.extend(["--input-directory", ".", "--output-directory", str(self.auxdir)])
            command.append(self.jobname)
        else:
            command = ["bibtex"]
            if self.native:
                # bibtex 把 .bbl 写在 .aux 所在目录，正好落在 auxdir
                command.append(str(Path(self.auxdir) / self.jobname))
            else:
                command.append(self.jobname)

        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, bib_engine)
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def compile_bib2gls(self):
        """glossaries-extra + bib2gls：索引条目由 bib2gls 生成。

        历史上 PyTeXMK 只置了 ``bib2gls_mode`` 标记却从不真正调用，
        导致 glossary 永远停在 "Glossary entries have changed" 状态。
        """
        command = ["bib2gls"]
        if not self.non_quiet:
            command.append("--quiet")
        if self.native:
            command.append(f"--dir={Path(self.auxdir).resolve()}")
        command.append(self.jobname)
        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, "bib2gls")
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def _pythontex_code_path(self) -> Path | None:
        """返回本轮 LaTeX 生成的 ``.pytxcode``；原生构建优先找 auxdir。"""
        candidates = (
            (Path(self.auxdir) / f"{self.jobname}.pytxcode", Path(f"{self.jobname}.pytxcode"))
            if self.native
            else (Path(f"{self.jobname}.pytxcode"), Path(self.auxdir) / f"{self.jobname}.pytxcode")
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def has_pythontex_code(self) -> bool:
        """首轮 LaTeX 是否产出了 PythonTeX 待处理代码。"""
        return self._pythontex_code_path() is not None

    def compile_pythontex(self):
        """运行 ``pythontex``，把 .pytxcode 里的代码块转成 LaTeX 可读输出。

        PythonTeX 的工作目录必须与 ``.pytxcode`` 所在目录一致：
        原生构建在 auxdir，传统构建在项目根目录。否则 pythontex 找不到
        输入文件，也不会把生成内容写回 LaTeX 期望的位置。
        """
        code_path = self._pythontex_code_path()
        if code_path is None:
            return
        cwd = code_path.parent.resolve()
        command = ["pythontex", self.jobname]
        try:
            self.MSP.run_command(
                command,
                self.out_files,
                self.aux_files,
                "pythontex",
                cwd=cwd,
            )
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def _resolve_index_token(self, token: str) -> str:
        """把索引命令里的 ``proj.xxx`` 换成实际存在的路径（原生构建在 auxdir）。"""
        if not self.native:
            return token
        prefix = f"{self.jobname}."
        if token == self.jobname or token.startswith(prefix):
            candidate = Path(self.auxdir) / token
            if candidate.exists() or token.startswith(prefix):
                return str(candidate)
        return token

    def compile_index(self, cmd):
        command = [self._resolve_index_token(tok) for tok in shlex.split(cmd[1])]
        # 主程序名也允许带路径（tools 不在 PATH 时由 detection 给出）
        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, cmd[0])
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def compile_xdv(self):
        if self.native:
            xdv = Path(self.auxdir) / f"{self.jobname}.xdv"
            pdf = Path(self.outdir) / f"{self.jobname}.pdf"
            command = ["dvipdfmx", "-V", "2.0", "-o", str(pdf), str(xdv)]
        else:
            command = ["dvipdfmx", "-V", "2.0", f"{self.jobname}"]
        if not self.non_quiet:
            command.insert(1, "-q")
        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, "dvipdfmx")
        except SubprocessFailedError:
            self._on_subprocess_failure()

    def verify_pdf_exists(self) -> bool:
        """编译结束后确认 PDF 真的产出（原生构建时它先在 auxdir 里）。"""
        candidates = (
            Path(self.outdir) / f"{self.jobname}.pdf",
            Path(self.auxdir) / f"{self.jobname}.pdf",
        )
        return any(p.exists() and p.stat().st_size > 0 for p in candidates)
