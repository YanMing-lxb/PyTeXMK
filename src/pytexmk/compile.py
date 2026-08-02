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
FilePath     : /PyTeXMK/src/pytexmk/compile.py
Description  :
 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【实际 subprocess 级编译执行 + 对检测的最小必要组合调用】。
  具体职责：
    1. LaTeX / BibTeX / Biber / MakeIndex / Glossaries / dvipdfmx 的真实 subprocess 调用。
  调用依赖关系拓扑：
    compile_engine.RUN 实例化 CompileLaTeX 执行实际编译 + 检测编排。
    CompileLaTeX 通过 self.detector 持有 CompilationDetector 引用，检测方法直接走 .detector.*。
  下游依赖：
    subprocess_runner / file_ops / version / pytexlogs / detection。
"""

import shlex
import logging

import pytexlogs

from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.lifecycle import exit_pytexmk
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError
from pytexmk.version import __version__

_ = set_language("compile")


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
    ):
        self.logger = logging.getLogger(__name__)

        self.project_name = project_name
        self.compiled_program = compiled_program
        self.out_files = out_files
        self.aux_files = aux_files
        self.auxdir = auxdir
        self.outdir = outdir
        self.non_quiet = non_quiet

        self.MRO = FileMoveRemoveManager()
        self.MSP = MySubProcess(outdir, auxdir, project_name)

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
        )

    def compile_tex(self):

        command = [
            self.compiled_program.lower(),
            "-shell-escape",
            "-file-line-error",
            "-halt-on-error",
            "-synctex=1",
            f"{self.project_name}.tex",
        ]
        if self.compiled_program == "XeLaTeX":
            command.insert(5, "-no-pdf")
        if self.non_quiet:
            command.insert(4, "-interaction=nonstopmode")
        else:
            command.insert(4, "-interaction=batchmode")

        try:
            self.MSP.run_command(
                command, self.out_files, self.aux_files, self.compiled_program
            )
        except SubprocessFailedError:
            pytexlogs.run_log_pipeline(
                self.project_name, self.auxdir, root_file=None,
                pytexmk_version=__version__,
                ref_tracker_translate_fn=set_language("log_parser"),
            )
            exit_pytexmk()

    def compile_bib(self, bib_engine):
        command = [bib_engine, self.project_name]

        if not self.non_quiet and bib_engine == "biber":
            command.insert(1, "-quiet")

        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, bib_engine)
        except SubprocessFailedError:
            pytexlogs.run_log_pipeline(
                self.project_name, self.auxdir, root_file=None,
                pytexmk_version=__version__,
                ref_tracker_translate_fn=set_language("log_parser"),
            )
            exit_pytexmk()

    def compile_index(self, cmd):
        name_target = f"{cmd[0]}"
        command = shlex.split(cmd[1])
        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, cmd[0])
        except SubprocessFailedError:
            pytexlogs.run_log_pipeline(
                self.project_name, self.auxdir, root_file=None,
                pytexmk_version=__version__,
                ref_tracker_translate_fn=set_language("log_parser"),
            )
            exit_pytexmk()
        return name_target

    def compile_xdv(self):
        command = ["dvipdfmx", "-V", "2.0", f"{self.project_name}"]
        if not self.non_quiet:
            command.insert(1, "-q")
        try:
            self.MSP.run_command(command, self.out_files, self.aux_files, "dvipdfmx")
        except SubprocessFailedError:
            pytexlogs.run_log_pipeline(
                self.project_name, self.auxdir, root_file=None,
                pytexmk_version=__version__,
                ref_tracker_translate_fn=set_language("log_parser"),
            )
            exit_pytexmk()
