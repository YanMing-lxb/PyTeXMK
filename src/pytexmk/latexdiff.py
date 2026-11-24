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
Date         : 2024-08-02 10:44:16 +0800
LastEditTime : 2025-10-01 11:17:47 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/latexdiff.py
Description  :
 -----------------------------------------------------------------------
"""

import logging
import re
import tempfile
from pathlib import Path

from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError
from pytexmk.tex_source import mask_tex_noncode

_ = set_language("latexdiff")

#: LaTeX 内建的 ``\input``/``\include`` 命令（花括号或裸文件名两种写法）。
#: 命令名后必须是边界：``\inputsection{...}`` 之类自定义宏不能被当成
#: ``\input section`` 展开。只处理 LaTeX 内建命令；作者自定义的 include 宏
#: 保持原样，交给作者自己的宏展开。
_INPUT_PATTERN = re.compile(
    r"\\(?:input|include)(?![A-Za-z@])\s*(?:\{([^}]*)\}|([^\s{}%]+))"
)

#: import 宏包的常用 include 命令：``\import{path/}{file}`` /
#: ``\subimport{path/}{file}`` 及其 input/include 别名。它们属于广泛使用的
#: 宏包命令，压平时应按同样的规则展开；``\subfile`` 会把子文件的导言区一起
#: 引进来，语义上与 ``\input`` 不同，故意不处理。
_IMPORT_PATTERN = re.compile(
    r"\\(?P<command>"
    r"import|subimport|inputfrom|includefrom|subinputfrom|subincludefrom"
    r")(?![A-Za-z@])\s*\{([^}]*)\}\s*\{([^}]*)\}"
)

#: 压平递归的硬上限，防御异常嵌套（正常论文不会超过十几层）
_MAX_FLATTEN_DEPTH = 64


class LaTeXDiff_Aux:
    """latexdiff 辅助类：负责 TeX 文件展开、diff 调用、目录清理。"""
    def __init__(self, outdir, suffixes_out, suffixes_aux, auxdir):
        """初始化 LaTeXDiff_Aux：缓存输出/辅助目录、后缀列表与子进程包装。"""
        self.logger = logging.getLogger(__name__)
        self.suffixes_out = suffixes_out
        self.suffixes_aux = suffixes_aux
        self.outdir = Path(outdir)
        self.auxdir = Path(auxdir)

        self.MRO = FileMoveRemoveManager()
        self.MSP = MySubProcess(outdir, auxdir, latexdiff=True)
        #: 每次压平独占一个临时目录：绝不在项目根目录写出 `<stem>-flatten.tex`，
        #: 否则会覆盖作者已有的同名文件（实测过）。
        self._tempdirs: list[tempfile.TemporaryDirectory] = []

    def cleanup(self) -> None:
        """删除本次运行创建的所有压平临时目录（可重复调用）。"""
        for handle in self._tempdirs:
            try:
                handle.cleanup()
            except OSError:
                pass
        self._tempdirs.clear()

    # --------------------------------------------------------------------------------
    # 定义 指定的旧TeX辅助文件存在检查函数
    # --------------------------------------------------------------------------------
    def check_aux_files(self, file_name):
        """指定的 TeX 文件辅助文件存在检查.

        返回:
            bool: 所有配置的辅助文件后缀中任一存在即为 True.
        """
        return any(
            (self.auxdir / f"{file_name}{suffix}").exists()
            for suffix in self.suffixes_aux
        )

    # --------------------------------------------------------------------------------
    # 定义 压平多文件的函数
    # --------------------------------------------------------------------------------
    # latexdiff 自带的 --flatten 参数可以用于压平多文件,但如果项目用 BibTeX 管理引用,则会在压平后报错.
    def flatten_Latex(self, file_name):
        """把主文件及其 include 子文件压平成一个 .tex。

        展开范围只包括 LaTeX 内建 ``\\input`` / ``\\include``，以及 import
        宏包的 ``\\import`` / ``\\subimport`` 与 input/include 别名；``\\subfile``、
        ``\\inputsection`` 等自定义或语义不同的命令保持原样。

        与旧实现的区别：
          * **独占临时目录**：不再写出 ``<stem>-flatten.tex`` 到项目根目录，
            不会覆盖作者已有的同名文件，两个项目并行运行也不会互相踩；
          * **保留命令行两侧的正文**：旧实现只把命中的 ``\\input`` 行换成子文件，
            同一行里的 ``\\section{...}\\input{x}`` 前半段会被整段丢掉；
          * 环路用**递归栈**判断，而不是全局 ``seen``：同一个子文件被两个章节
            正常引用（公共导言区片段）不应被误判为循环；
          * 子文件路径**先按编译工作目录（通常是项目根）解析**，再退回被展开
            文件所在目录；TeX 的 ``\\input`` 本身并不相对于当前子文件，只按
            子文件目录找会让 ``chapters/intro.tex`` 里的 ``\\input{chapters/section}``
            压平失败。
        """
        root = Path(f"{file_name}.tex")
        if not root.is_file():
            self.logger.error(_("文件不存在: ") + str(root))
            exit_pytexmk(EXIT_ERROR)

        handle = tempfile.TemporaryDirectory(prefix="pytexmk-flatten-")
        self._tempdirs.append(handle)
        output_stem = Path(handle.name) / f"{Path(file_name).name}-flatten"
        output_path = output_stem.with_suffix(".tex")

        try:
            # CLI 在项目根执行；嵌套主文件（chapters/main）里的 \input 仍以
            # 项目根为基准。绝对路径调用（API/临时文件）则退回其父目录。
            base = Path.cwd() if not root.is_absolute() else root.resolve().parent
            text = self._flatten_text(root, stack=set(), depth=0, base=base)
            output_path.write_text(text, encoding="utf-8")
        except OSError as e:
            self.logger.error(_("压平出错: ") + str(e))
            exit_pytexmk(EXIT_ERROR)

        self.logger.info(_("已压平文件: ") + str(output_path))
        # 返回**不含 .tex 的绝对路径**：compile_LaTeXDiff 仍按 suffix 拼接，
        # 但不会再落到项目根目录。
        return str(output_stem)

    def _flatten_text(
        self, path: Path, *, stack: set[Path], depth: int, base: Path
    ) -> str:
        """递归展开一个文件，返回展开后的完整文本。"""
        if depth > _MAX_FLATTEN_DEPTH:
            self.logger.warning(_("压平嵌套过深，已跳过: ") + str(path))
            return ""
        try:
            key = path.resolve()
        except OSError:
            key = path
        if key in stack:
            self.logger.warning(_("检测到循环引用，已跳过: ") + str(path))
            return ""
        if not path.is_file():
            self.logger.warning(_("被引用的文件不存在，已跳过: ") + str(path))
            return ""
        stack.add(key)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            # 注释 / verbatim / \verb 里的 \input 不是命令，先屏蔽再匹配；
            # 屏蔽结果与原文等长，展开时仍切原文，verbatim 内容原样保留。
            masked = mask_tex_noncode(text)
            return "".join(
                self._expand_line(line, mask_line, path, stack=stack, depth=depth, base=base)
                for line, mask_line in zip(
                    text.splitlines(keepends=True),
                    masked.splitlines(keepends=True),
                    strict=True,
                )
            )
        finally:
            stack.discard(key)

    def _expand_line(
        self,
        line: str,
        mask_line: str,
        path: Path,
        *,
        stack: set[Path],
        depth: int,
        base: Path,
    ) -> str:
        """展开一行里的内建 include 与 import 宏包命令，其余正文原样保留。"""
        matches: list[tuple[int, int, str, str, str]] = []
        for match in _INPUT_PATTERN.finditer(mask_line):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    "input",
                    "",
                    (match.group(1) or match.group(2) or "").strip(),
                )
            )
        for match in _IMPORT_PATTERN.finditer(mask_line):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    match.group("command"),
                    match.group(2).strip(),
                    match.group(3).strip(),
                )
            )
        if not matches:
            return line

        # 两类正则在边界上互斥，但保险起见仍跳过重叠命中，避免同一段被切两次。
        matches.sort(key=lambda item: item[0])
        selected: list[tuple[int, int, str, str, str]] = []
        last_end = -1
        for item in matches:
            if item[0] < last_end:
                continue
            selected.append(item)
            last_end = item[1]

        parts: list[str] = []
        last = 0
        for start, end, command, import_path, target in selected:
            parts.append(line[last:start])
            child_path = self._resolve_include_path(
                command, import_path, target, path, base
            )
            if child_path is None:
                parts.append(line[start:end])
                last = end
                continue

            child = self._flatten_text(child_path, stack=stack, depth=depth + 1, base=base)
            remainder = line[end:]
            # 命令后面同一行还有非空正文 → 内联展开，不能把子文件末尾的换行带进来
            # （否则会把一个段落切成两段）。
            inline = bool(remainder.strip("\r\n").strip())
            if inline:
                child = child.rstrip("\r\n")
            elif line.endswith("\n") and not child.endswith("\n"):
                child += "\n"
            parts.append(child)
            last = end
        parts.append(line[last:])
        return "".join(parts)

    def _resolve_include_path(
        self,
        command: str,
        import_path: str,
        target: str,
        current: Path,
        base: Path,
    ) -> Path | None:
        """按命令语义把 include 参数解析成真实文件。

        ``\\import`` / ``\\inputfrom`` / ``\\includefrom`` 的路径相对主文件目录；
        ``\\subimport`` / ``\\subinputfrom`` / ``\\subincludefrom`` 相对当前文件
        目录。内建 ``\\input`` / ``\\include`` 沿用 TeX 的工作目录规则，仍保留
        “主目录优先、当前子文件目录兜底”的兼容行为。
        """
        if not target:
            return None
        if not target.lower().endswith(".tex"):
            target += ".tex"

        if command == "input":
            root_relative = base / target
            sibling = current.parent / target
            if root_relative.is_file():
                return root_relative
            if sibling.is_file():
                return sibling
            self.logger.warning(_("被引用的文件不存在，已跳过: ") + str(root_relative))
            return None

        relative_root = current.parent if command.startswith("sub") else base
        candidate = relative_root / import_path / target
        if candidate.is_file():
            return candidate
        self.logger.warning(_("被引用的文件不存在，已跳过: ") + str(candidate))
        return None

    # --------------------------------------------------------------------------------
    # 判断在指定后缀的新旧辅助文件是否同时存在
    # --------------------------------------------------------------------------------
    def aux_files_both_exist(self, old_file, new_file, suffix):
        """检查新旧辅助文件是否同时存在."""
        old_file_path = Path(old_file + suffix)
        new_file_path = Path(new_file + suffix)
        if old_file_path.exists() and new_file_path.exists():
            self.logger.info(
                _("新旧辅助文件同时存在: ")
                + str(old_file_path)
                + " "
                + str(new_file_path)
            )
            return suffix
        return None

    # --------------------------------------------------------------------------------
    # 定义 LaTeXDiff 编译函数
    # --------------------------------------------------------------------------------
    def compile_LaTeXDiff(self, old_tex_file, new_tex_file, diff_tex_file, suffix):
        """调用 latexdiff 生成差异 TeX 文件。

        注意：latexdiff 的 ``--style`` 取的是**样式文件路径**，不是 1/2 这种
        编号；0.5 把 PyTeXMK 自己的"1/2 显示风格"直接拼成 ``--style=1``，
        latexdiff 会去找名为 ``1`` 的样式文件并报错。1/2 只是本工具决定
        "是否逐个比对 .bbl/.nls/.gls/.idx" 的开关，与 latexdiff 参数无关，
        因此这里不向 latexdiff 传任何 style 参数。
        """
        command = [
            "latexdiff",
            old_tex_file + suffix,
            new_tex_file + suffix,
            "--encoding=utf8",
        ]
        output_path = diff_tex_file + suffix

        # 输出路径与任一输入相同 → 重定向会在 latexdiff 读取输入前把它截断成空文件，
        # 结果是“命令执行了、差异稿为空”，源文件也可能被一起毁掉。直接拒绝。
        try:
            out_resolved = Path(output_path).resolve()
            inputs = {
                Path(old_tex_file + suffix).resolve(),
                Path(new_tex_file + suffix).resolve(),
            }
        except OSError:
            out_resolved = Path(output_path)
            inputs = {Path(old_tex_file + suffix), Path(new_tex_file + suffix)}
        if out_resolved in inputs:
            self.logger.error(
                _("LaTeXDiff 输出文件与输入文件相同，拒绝执行（会截断源文件）: ")
                + str(output_path)
            )
            exit_pytexmk(EXIT_ERROR)

        if Path(old_tex_file).is_absolute() or Path(new_tex_file).is_absolute():
            # 压平文件在临时目录：失败时不能把它们“归还”到 outdir/auxdir。
            out_files: list[str] = []
            aux_files: list[str] = []
        else:
            old_out_files = [f"{old_tex_file}{suffix}" for suffix in self.suffixes_out]
            new_out_files = [f"{new_tex_file}{suffix}" for suffix in self.suffixes_out]
            diff_out_files = [f"{diff_tex_file}{suffix}" for suffix in self.suffixes_out]
            out_files = old_out_files + new_out_files + diff_out_files
            old_aux_files = [f"{old_tex_file}{suffix}" for suffix in self.suffixes_aux]
            new_aux_files = [f"{new_tex_file}{suffix}" for suffix in self.suffixes_aux]
            aux_files = old_aux_files + new_aux_files

        try:
            self.MSP.run_command(
                command, out_files, aux_files, "latexdiff", stdout_path=output_path
            )
        except SubprocessFailedError:
            exit_pytexmk(EXIT_COMPILE_FAILED)

        # latexdiff 可能以 0 退出却没有产出（被信号截断/磁盘满/发布失败）；
        # 空差异稿若继续拿去编译，报错点会跑到 xelatex 里，误导排查方向。
        try:
            produced = Path(output_path).stat().st_size
        except OSError:
            produced = 0
        if produced <= 0:
            self.logger.error(_("latexdiff 未生成有效输出: ") + str(output_path))
            exit_pytexmk(EXIT_COMPILE_FAILED)
