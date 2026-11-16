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
from pathlib import Path

from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError

_ = set_language("latexdiff")


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

    # --------------------------------------------------------------------------------
    # 定义 指定的旧TeX辅助文件存在检查函数
    # --------------------------------------------------------------------------------
    def check_aux_files(self, file_name):
        """指定的 TeX 文件辅助文件存在检查.

        返回:
            bool: 所有配置的辅助文件后缀中任一存在即为 True.
        """
        aux_files = [f"{file_name}{suffix}" for suffix in self.suffixes_aux]
        for file in aux_files:
            if (self.auxdir / file).exists():
                return True
        return False

    # --------------------------------------------------------------------------------
    # 定义 压平多文件的函数
    # --------------------------------------------------------------------------------
    # latexdiff 自带的 --flatten 参数可以用于压平多文件,但如果项目用 BibTeX 管理引用,则会在压平后报错.
    def flatten_Latex(self, file_name):
        """把主文件及其 ``\\input``/``\\include`` 子文件压平成一个 .tex。

        与旧实现的区别（3.5）：
          * 直接写文件句柄，**不再把 sys.stdout 重定向**（否则 logger 的每一行
            都会混进生成的 .tex，产出不可编译的文件）；
          * 支持 ``\\input file``（不带花括号）写法；
          * 子文件路径相对**当前被展开文件所在目录**解析，而不是主文件目录；
          * 维护 ``seen`` 集合做环路检测，自引用/互引用不会无限递归。
        """
        pattern = re.compile(r"\\(?:input|include)\s*(?:\{([^}]*)\}|([^\s{}%]+))")
        output_file_name = f"{file_name}-flatten"
        output_path = Path(output_file_name + ".tex")
        root = Path(f"{file_name}.tex")
        if not root.is_file():
            self.logger.error(_("文件不存在: ") + str(root))
            exit_pytexmk(EXIT_ERROR)

        seen: set[Path] = set()

        def expand(path: Path, handle, depth: int = 0) -> None:
            if depth > 64:
                self.logger.warning(_("压平嵌套过深，已跳过: ") + str(path))
                return
            try:
                key = path.resolve()
            except OSError:
                key = path
            if key in seen:
                self.logger.warning(_("检测到循环引用，已跳过: ") + str(path))
                return
            seen.add(key)
            if not path.is_file():
                self.logger.warning(_("被引用的文件不存在，已跳过: ") + str(path))
                return
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True):
                stripped = line.lstrip()
                if stripped.startswith("%"):
                    handle.write(line)
                    continue
                match = pattern.search(line)
                if not match:
                    handle.write(line)
                    continue
                target = (match.group(1) or match.group(2) or "").strip()
                if not target:
                    handle.write(line)
                    continue
                if not target.lower().endswith(".tex"):
                    target += ".tex"
                expand(path.parent / target, handle, depth + 1)

        try:
            with output_path.open("w", encoding="utf-8") as output_file:
                expand(root, output_file)
        except OSError as e:
            self.logger.error(_("压平出错: ") + str(e))
            exit_pytexmk(EXIT_ERROR)

        self.logger.info(_("已压平文件: ") + str(output_path))
        return output_file_name

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
    def compile_LaTeXDiff(self, old_tex_file, new_tex_file, diff_tex_file, suffix, style=None):
        """调用 latexdiff 命令生成差异 TeX 文件；``style`` 为 1/2 时非交互指定。"""
        command = [
            "latexdiff",
            old_tex_file + suffix,
            new_tex_file + suffix,
            "--encoding=utf8",
        ]
        if style:
            command.append(f"--style={style}")
        output_path = diff_tex_file + suffix

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
