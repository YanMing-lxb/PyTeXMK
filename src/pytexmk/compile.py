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

import contextlib
import logging
import os
import re
import shlex
import shutil
from pathlib import Path

from pytexmk.detection import BibEngine
from pytexmk.diagnostics import report_failure
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_COMPILE_FAILED, exit_pytexmk
from pytexmk.runtime_env import is_dir_writable
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError
from pytexmk.ui_theme import console

# xindy 家族的工具名（texindy 只是带默认样式的包装）
_XINDY_TOOLS = frozenset({"xindy", "texindy"})
# 这些选项的值是文件路径，换工作目录重试时必须改成绝对路径
_XINDY_FILE_OPTIONS = frozenset({"-M", "-t", "-o", "-x", "-i", "-s"})

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


SHELL_ESCAPE_FALSE_VALUES = ("false", "0", "no", "off")

#: 默认的 TeX 交互模式。安静模式**不再**改变 TeX 的运行方式：``-q`` / ``-nq``
#: 只决定"编译过程日志是否打到终端"。
#:
#: 旧实现让安静模式走 ``-interaction=batchmode``，于是同一份文档"加不加 -nq"
#: 走的是两套 TeX 语义（batchmode 会吞掉终端提示、遇错也不停），出问题时无法
#: 判断是 PyTeXMK 卡住还是 TeX 本身行为不同。要 batchmode 请写进配置
#: ``[build] interaction``（命令行不再提供该开关）。
DEFAULT_INTERACTION = "nonstopmode"


def effective_interaction(explicit: str | None = None) -> str:
    """本次编译实际使用的 ``-interaction`` 模式（显式设置优先，其余取默认）。"""
    return explicit or DEFAULT_INTERACTION


def normalize_shell_escape_flag(value: object) -> bool:
    """把 ``true/false/1/0/yes/no/on/off`` 字符串统一成 bool。

    ``state.shell_escape`` 是字符串（值域含 ``auto``），直接 ``bool("false")``
    会得到 True —— 这正是历史上 ``--no-shell-escape`` 与
    ``[build] shell_escape = false`` 双双失效的原因（-shell-escape 照旧加上）。
    """
    return str(value).strip().lower() not in SHELL_ESCAPE_FALSE_VALUES


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


def shell_escape_off_flag() -> str:
    """``--no-shell-escape`` 对应的**发行版专用**关闭参数。

    只省略 ``-shell-escape`` 并不等于关闭：MiKTeX 默认允许
    ``restricted \\write18``，日志里仍会写 ``restricted \\write18 enabled``。
    MiKTeX 必须显式 ``--disable-write18``；TeX Live / MacTeX 用
    ``-no-shell-escape``。按发行版特征选择，而不是两条都传（未知选项会让
    引擎直接报错退出）。
    """
    miktex_markers = ("initexmf", "miktex-pdflatex", "miktex-xetex", "miktex-lualatex")
    if os.environ.get("MIKTEX_HOME") or any(shutil.which(name) for name in miktex_markers):
        return "--disable-write18"
    return "-no-shell-escape"


def is_xindy_command(tokens: list[str]) -> bool:
    """命令是否为 xindy / texindy（允许第一个 token 带路径）。

    取 basename 时按 ``/`` 和 ``\\`` 两种分隔符切分：POSIX 的 ``Path`` 不把
    反斜杠当分隔符，Windows 路径 ``C:\\tex\\bin\\xindy.exe`` 会被整体当成文件名，
    于是跨平台跑单测时判定失败。产物只在 Windows 上用到反斜杠路径，但判定函数
    本身应当与宿主平台无关。
    """
    if not tokens:
        return False
    basename = tokens[0].replace("\\", "/").rsplit("/", 1)[-1]
    return Path(basename).stem.lower() in _XINDY_TOOLS


def xindy_fallback_workdirs() -> list[Path]:
    """xindy 的 Windows 兜底工作目录候选（按优先级）。

    xindy.pl 在 Windows 上把启动表达式写进**当前目录**的临时文件，再交给
    ``xindy-lisp.exe`` 载入；部分目录（本机实测：项目目录、含空格/深层路径、
    含 ``.tmp`` 段）在载入这一步会报 ``Win32 error 267 (ERROR_DIRECTORY)``，
    换到 ``%SystemRoot%\\Temp`` 并把文件参数改成绝对路径就能正常产出。

    这里给出候选目录，由调用方逐个重试：先试用户临时目录下的专用子目录
    （有写权限、路径短），再退回系统临时目录。目录不可用时直接跳过。
    """
    if os.name != "nt":
        return []
    candidates: list[Path] = []
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        candidates.append(Path(temp) / "pytexmk-xindy")
    for env_name in ("SystemRoot", "windir"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "Temp")
    usable: list[Path] = []
    for candidate in candidates:
        if candidate in usable:
            continue
        with contextlib.suppress(OSError):
            candidate.mkdir(parents=True, exist_ok=True)
        if candidate.is_dir() and is_dir_writable(candidate):
            usable.append(candidate)
    return usable


_XINDY_LAUNCHER_LOG_MARKERS = ("720005", "log4cxx")


def xindy_perl_command(tokens: list[str]) -> list[str] | None:
    """用 ``perl xindy.pl`` 复刻同一条 xindy 命令，绕开 MiKTeX 启动器。

    MiKTeX 的 ``xindy.exe`` 只是个启动器，启动时先打开
    ``<texmfs>/data/miktex/log/xindy.log``；该路径不可写时（受限令牌、只读
    安装目录）启动器直接放弃，xindy 根本没跑起来，只留下
    ``log4cxx ... 720005``。脚本 ``xindy.pl`` 本身没有这个前置动作，直接用
    系统 perl 调它就能跳过这段。找不到 ``perl`` 或 ``xindy.pl`` 时返回 None。
    """
    if not tokens or not is_xindy_command(tokens):
        return None
    executable = shutil.which(tokens[0])
    if not executable:
        return None
    # .../texmfs/install/miktex/bin/x64/xindy.exe -> .../texmfs/install
    install = Path(executable).resolve().parents[3]
    script = install / "scripts" / "xindy" / "xindy.pl"
    perl = shutil.which("perl")
    if not perl or not script.is_file():
        return None
    return [perl, str(script), *tokens[1:]]


def absolutize_xindy_tokens(tokens: list[str], base: Path) -> list[str]:
    """把 xindy 命令里的相对文件参数改成相对 ``base`` 的绝对路径。

    只认 ``-M/-t/-o/-x/-i/-s`` 这几个取文件路径的选项，``-L english``、
    ``-I xindy``、``-C utf8`` 这类值不是路径，原样保留；末尾的输入文件若在
    ``base`` 下真实存在，也一并改成绝对路径。
    """
    result: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _XINDY_FILE_OPTIONS and index + 1 < len(tokens):
            value = Path(tokens[index + 1])
            result.extend([token, str(value if value.is_absolute() else base / value)])
            index += 2
            continue
        result.append(token)
        index += 1
    if result:
        last = result[-1]
        if not last.startswith("-") and not Path(last).is_absolute():
            candidate = base / last
            if candidate.exists():
                result[-1] = str(candidate)
    return result


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
        synctex=True,
        native=False,
        extra_args=None,
        interaction=None,
        jobname=None,
        max_extra_args=None,
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
        self.synctex = bool(synctex)
        self.native = bool(native)
        self.extra_args = list(extra_args or [])
        self.interaction = interaction
        self.jobname = jobname or project_name
        self.max_extra_args = max_extra_args

        self.MRO = FileMoveRemoveManager()
        self.MSP = MySubProcess(
            outdir, auxdir, self.jobname, stream_output=self.non_quiet
        )

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
            native=self.native,
        )

    # ------------------------------------------------------------------ 失败收尾

    def _on_subprocess_failure(self):
        """统一处理 SubprocessFailedError：打印可执行诊断后退出。"""
        report_failure(
            self.jobname,
            self.auxdir,
            root_file=f"{self.project_name}.tex",
            translate_fn=set_language("diagnostics"),
        )
        exit_pytexmk(EXIT_COMPILE_FAILED)

    def _on_index_failure(self, program: str, output: str) -> None:
        """索引工具（makeindex / xindy / makeglossaries）失败时的收尾。

        这类失败不会写进 LaTeX ``.log``：真原因（样式文件找不到、xindy 环境
        损坏、.glo 里有非法条目）只在工具自己的输出里。沿用 LaTeX 日志诊断
        只会打印"日志里没有解析出 error 条目"，把原因彻底藏起来。
        """
        tail = "\n".join(output.strip().splitlines()[-12:]) if output else ""
        console.print(
            "[bold red]"
            + _("索引工具执行失败: %(p)s") % {"p": program}
            + "[/bold red]"
        )
        if tail:
            console.print(tail, style="dim", markup=False)
        exit_pytexmk(EXIT_COMPILE_FAILED)

    # ------------------------------------------------------------------ 命令构造

    def _interaction_flag(self) -> str:
        # 安静与非安静都用同一个 nonstopmode：两者的 TeX 行为必须完全一致，
        # 差别只应出现在"输出是否显示"上（见 DEFAULT_INTERACTION 的说明）。
        return f"-interaction={effective_interaction(self.interaction)}"

    def _latex_command(self) -> list[str]:
        command = [
            self.compiled_program.lower(),
            "-recorder",  # 产出 .fls：依赖收集（投稿打包/PDF 修复范围）都靠它
            "-file-line-error",
            "-halt-on-error",
        ]
        if self.synctex:
            # 编辑器正/反向跳转依赖它；投稿版可在配置里设 synctex = false 关掉
            command.append("-synctex=1")
        command.append(self._interaction_flag())
        if self.shell_escape:
            command.insert(1, "-shell-escape")
        else:
            # 显式关闭必须落到发行版真正认的禁用参数，否则 MiKTeX 仍是
            # `restricted \write18 enabled`，配置里的 shell_escape = false 形同虚设。
            command.insert(1, shell_escape_off_flag())
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
                # native 构建把 .bcf 写在 auxdir；biber 的 input 目录必须指向
                # auxdir，否则会在项目根目录找不到 main.bcf 并以退出码 5 失败。
                command.extend(
                    [
                        "--input-directory",
                        str(self.auxdir),
                        "--output-directory",
                        str(self.auxdir),
                    ]
                )
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

    @staticmethod
    def _strip_wrapping_quotes(token: str) -> str:
        """去掉 ``posix=False`` 分词后保留在两端的引号（列表传参时不应带引号）。"""
        if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
            return token[1:-1]
        return token

    def compile_index(self, cmd):
        # 用 posix=False 分词：POSIX 规则会把 Windows 路径里的反斜杠当转义符，
        # `-s C:\tex\nomencl.ist` 会被拆成 `C:texnomencl.ist` 从而整条命令失败。
        try:
            tokens = shlex.split(cmd[1], posix=False)
        except ValueError as exc:
            # 引号不配对等语法错误：直接用整串单参数执行，至少不会崩在分词上
            self.logger.warning(_("索引命令分词失败，按单参数执行: %(cmd)s (%(e)s)") % {"cmd": cmd[1], "e": exc})
            tokens = [cmd[1]]
        tokens = [self._strip_wrapping_quotes(tok) for tok in tokens]
        # 原生构建把 .idx/.nlo/.glo 都写在 auxdir 里，索引命令里的路径都是相对
        # 文件名；直接在 auxdir 里执行，命名索引（author.idx）也不需要再猜前缀。
        # 非原生构建此时辅助文件还在项目根目录（编译后才搬去 auxdir），cwd 不变。
        run_cwd = Path(self.auxdir) if self.native else None
        if run_cwd is not None:
            run_cwd.mkdir(parents=True, exist_ok=True)
        base_dir = (Path(run_cwd) if run_cwd is not None else Path.cwd()).resolve()
        # 主程序名也允许带路径（tools 不在 PATH 时由 detection 给出）
        try:
            self.MSP.run_command(
                tokens, self.out_files, self.aux_files, cmd[0],
                cwd=run_cwd, log_hint=False,
            )
        except SubprocessFailedError as exc:
            output = f"{exc.stdout or ''}{exc.stderr or ''}"
            if self._retry_xindy(tokens, base_dir, output):
                return
            self._on_index_failure(cmd[0], exc.stdout or "")

    def _retry_xindy(self, tokens: list[str], base_dir: Path, output: str) -> bool:
        """xindy 启动阶段失败时换形态/换目录重试。

        两类失败各有对策：

        * ``Win32 error 267 (ERROR_DIRECTORY)`` —— ``xindy.pl`` 把启动表达式写到
          当前目录，交给内核载入时某些目录（本机实测项目目录、含空格或深层路径）
          会报这个错。对策：改到临时目录、文件参数全部绝对化。
        * ``log4cxx ... 720005`` —— MiKTeX 启动器写不了自己的 ``xindy.log``，
          xindy 压根没被执行。对策：改用 ``perl xindy.pl`` 直接跑，并同样换到
          可写的临时目录。

        只对这些启动期错误重试：``.xdy`` 写错、``.glo`` 格式错之类重试也不会好，
        只会把真实报错刷掉。
        """
        if not is_xindy_command(tokens):
            return False
        path_failure = "267" in output or "ERROR_DIRECTORY" in output
        launcher_failure = all(marker in output for marker in _XINDY_LAUNCHER_LOG_MARKERS)
        if not (path_failure or launcher_failure):
            return False

        variants: list[tuple[list[str], str]] = []
        if launcher_failure:
            perl_command = xindy_perl_command(tokens)
            if perl_command:
                variants.append((perl_command, "perl xindy.pl"))
        if path_failure or not variants:
            variants.append((absolutize_xindy_tokens(tokens, base_dir), "xindy"))

        for command, label in variants:
            for workdir in [base_dir, *xindy_fallback_workdirs()]:
                if label == "xindy" and workdir == base_dir:
                    continue  # 原始形态已经在 base_dir 试过了
                if not is_dir_writable(workdir):
                    continue
                self.logger.warning(
                    "xindy 启动失败（%s），改用 %s 在 %s 重试（文件参数已转为绝对路径）",
                    "启动器日志不可写" if launcher_failure else "Win32 267",
                    label,
                    workdir,
                )
                try:
                    self.MSP.run_command(
                        command, self.out_files, self.aux_files, tokens[0],
                        cwd=workdir, log_hint=False,
                    )
                except SubprocessFailedError:
                    continue
                return True
        return False

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
        """编译结束后确认 PDF 真的产出。

        候选顺序覆盖三种落点：outdir（本轮已归档/同目录构建）、auxdir
        （native 构建）、项目根目录（``--no-native`` + dvipdfmx）。
        旧实现漏了根目录，非原生构建每次都会误报“未检测到编译输出的 PDF”。
        """
        candidates = (
            Path(self.outdir) / f"{self.jobname}.pdf",
            Path(self.auxdir) / f"{self.jobname}.pdf",
            Path(f"{self.jobname}.pdf"),
        )
        return any(p.exists() and p.stat().st_size > 0 for p in candidates)
