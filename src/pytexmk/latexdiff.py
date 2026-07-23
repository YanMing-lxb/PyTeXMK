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
LastEditTime : 2025-07-23 22:27:29 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/latexdiff.py
Description  : LaTeXDiff 功能增强模块
 -----------------------------------------------------------------------
"""

# -*- coding: utf-8 -*-
import re
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Union, Any
from warnings import warn

from rich.console import Console

from pytexmk.language import set_language
from pytexmk.additional import MoveRemoveOperation, MySubProcess
from pytexmk.compile import CompileLaTeX
from pytexmk.exceptions import (
    CompilationError,
    FileOperationError,
    LaTeXDiffError,
    ToolchainNotFoundError,
)

_ = set_language("latexdiff")

console = Console(legacy_windows=False)


class LaTeXDiffTool:
    """LaTeXDiff 工具类，提供完整的 LaTeX 差异对比和编译功能"""

    def __init__(
        self,
        toolchain_manager: Optional[Any] = None,
        timeout: int = 300,
    ):
        """
        初始化 LaTeXDiffTool

        参数:
            toolchain_manager: 可选的 ToolchainManager 实例
            timeout: 子进程超时时间（秒），默认 300 秒
        """
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.MRO = MoveRemoveOperation()
        self.MSP = MySubProcess()
        self._compiler: Optional[CompileLaTeX] = None
        self._toolchain_manager = toolchain_manager

    def detect_available(self) -> bool:
        """
        检测 latexdiff 命令是否可用

        返回:
            bool: latexdiff 是否在 PATH 中可用
        """
        return shutil.which("latexdiff") is not None

    def _ensure_latexdiff_available(self) -> None:
        """确保 latexdiff 可用，否则抛出异常"""
        if not self.detect_available():
            raise LaTeXDiffError(message="未检测到 latexdiff 命令，请确认已安装 LaTeXDiff 并添加到系统 PATH")

    def generate_diff(
        self,
        old_file: Union[str, Path],
        new_file: Union[str, Path],
        output_file: Union[str, Path],
        flatten: bool = False,
        fast: bool = False,
        only_changes: bool = False,
        encoding: str = "utf8",
        extra_args: Optional[List[str]] = None,
    ) -> Path:
        """
        生成差异 TeX 文件

        参数:
            old_file: 旧版本 TeX 文件路径
            new_file: 新版本 TeX 文件路径
            output_file: 输出差异文件路径
            flatten: 是否使用 --flatten 选项压平多文件
            fast: 是否使用 --fast 选项（快速模式，不处理命令参数）
            only_changes: 是否使用 --only-changes 选项（仅标注更改块）
            encoding: 文件编码，默认 utf8
            extra_args: 额外传递给 latexdiff 的命令行参数列表

        返回:
            Path: 输出文件路径

        异常:
            LaTeXDiffError: latexdiff 不可用或执行失败
            FileNotFoundError: 输入文件不存在
        """
        self._ensure_latexdiff_available()

        old_path = Path(old_file).resolve()
        new_path = Path(new_file).resolve()
        output_path = Path(output_file).resolve()

        if not old_path.exists() and old_path.suffix != ".tex":
            old_path = old_path.with_suffix(".tex")
        if not new_path.exists() and new_path.suffix != ".tex":
            new_path = new_path.with_suffix(".tex")
        if output_path.suffix != ".tex":
            output_path = output_path.with_suffix(".tex")

        if not old_path.exists():
            raise FileNotFoundError(f"旧版本文件不存在: {old_path}")
        if not new_path.exists():
            raise FileNotFoundError(f"新版本文件不存在: {new_path}")

        cmd: List[str] = ["latexdiff", f"--encoding={encoding}"]

        if flatten:
            cmd.append("--flatten")
        if fast:
            cmd.append("--fast")
        if only_changes:
            cmd.append("--only-changes")
        if extra_args:
            cmd.extend(extra_args)

        cmd.extend([str(old_path), str(new_path)])

        self.logger.info(f"运行 latexdiff 生成差异文件: {output_path}")
        console.print(f"[bold cyan]>>> {_('运行 latexdiff 生成差异文件')} <<<[/bold cyan]")
        console.print(_("[bold]命令: [/bold]") + f"[cyan]{' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                cwd=str(output_path.parent),
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"返回码: {result.returncode}"
                raise LaTeXDiffError(message=f"latexdiff 执行失败: {error_msg}")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.stdout, encoding="utf-8")

            self.logger.info(f"差异文件已生成: {output_path}")
            console.print(f"[bold green]✓ {_('差异文件已生成')}: {output_path}[/bold green]")

            return output_path

        except subprocess.TimeoutExpired:
            raise LaTeXDiffError(message=f"latexdiff 执行超时（{self.timeout} 秒）")
        except FileNotFoundError:
            raise LaTeXDiffError(message="latexdiff 命令未找到")
        except LaTeXDiffError:
            raise
        except Exception as e:
            raise LaTeXDiffError(message=f"latexdiff 执行时发生异常: {e}") from e

    def flatten_tex(
        self,
        main_file: Union[str, Path],
        output_file: Union[str, Path],
    ) -> Path:
        """
        将 LaTeX 文件及其所有引用的子文件压平为单一文件（不依赖 latexdiff --flatten）

        参数:
            main_file: 主 LaTeX 文件路径（可带或不带 .tex 后缀）
            output_file: 输出压平文件路径

        返回:
            Path: 输出压平文件路径

        异常:
            CompilationError: 文件不存在或压平失败
        """
        main_path = Path(main_file).resolve()
        output_path = Path(output_file).resolve()

        if not main_path.exists() and main_path.suffix != ".tex":
            main_path = main_path.with_suffix(".tex")
        if output_path.suffix != ".tex":
            output_path = output_path.with_suffix(".tex")

        if not main_path.exists():
            raise CompilationError(message=f"主文件不存在: {main_path}")

        input_cmd_pattern = re.compile(r"\\(input|include)\s*\{([^}]*)\}")

        def _find_input_before_comment(line: str):
            r"""在一行中查找注释之前的 \input/\include 命令，返回 (match, filename) 或 (None, None)"""
            comment_pos = None
            i = 0
            escaped = False
            while i < len(line):
                if line[i] == "\\":
                    escaped = not escaped
                elif line[i] == "%" and not escaped:
                    comment_pos = i
                    break
                else:
                    escaped = False
                i += 1

            search_area = line[:comment_pos] if comment_pos is not None else line
            match = input_cmd_pattern.search(search_area)
            if match:
                return match, match.group(2).strip()
            return None, None

        def _flatten_recursive(tex_file: Path, out_handle, _visited: Optional[set] = None):
            r"""递归展开 \input 和 \include"""
            if _visited is None:
                _visited = set()

            resolved = tex_file.resolve()
            if resolved in _visited:
                self.logger.warning(f"检测到循环引用，跳过: {resolved}")
                return
            _visited.add(resolved)

            if not resolved.is_file():
                raise CompilationError(message=f"引用的文件不存在: {resolved}")

            dirpath = resolved.parent

            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                raise CompilationError(message=f"无法读取文件 {resolved}: {e}") from e

            for line in lines:
                match, filename = _find_input_before_comment(line)
                if match:
                    out_handle.write(line[: match.start()])
                    if not filename.endswith(".tex"):
                        filename += ".tex"
                    subfile = dirpath / filename
                    self.logger.debug(f"展开文件: {subfile}")
                    _flatten_recursive(subfile, out_handle, _visited)
                    out_handle.write(line[match.end() :])
                else:
                    out_handle.write(line)

        original_stdout = sys.stdout
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as output_handle:
                _flatten_recursive(main_path, output_handle)

            self.logger.info(f"已压平文件: {output_path}")
            console.print(f"[bold green]✓ {_('已压平文件')}: {output_path}[/bold green]")

            return output_path

        except Exception:
            raise
        finally:
            sys.stdout = original_stdout

    def compile_diff(
        self,
        diff_file: Union[str, Path],
        engine: Optional[str] = None,
        run_count: int = 2,
        **compile_kwargs: Any,
    ) -> bool:
        """
        编译生成的 diff 文件

        参数:
            diff_file: diff TeX 文件路径
            engine: TeX 引擎名称（xelatex/pdflatex/lualatex），默认自动检测
            run_count: 编译次数，默认 2 次
            **compile_kwargs: 传递给 CompileLaTeX 的其他参数

        返回:
            bool: 编译是否成功

        异常:
            LaTeXDiffError: 编译失败
        """
        diff_path = Path(diff_file).resolve()
        if diff_path.suffix != ".tex":
            diff_path = diff_path.with_suffix(".tex")

        if not diff_path.exists():
            raise FileNotFoundError(f"Diff 文件不存在: {diff_path}")

        project_name = diff_path.stem
        cwd = str(diff_path.parent)

        console.print(f"\n[bold cyan]>>> {_('编译差异文件')}: {diff_path.name} <<<[/bold cyan]")

        try:
            compiler_kwargs: Dict[str, Any] = {
                "project_name": project_name,
                "run_count": run_count,
                "auto_detect": True,
            }
            if engine:
                compiler_kwargs["program"] = engine
            compiler_kwargs.update(compile_kwargs)

            import os

            original_cwd = os.getcwd()
            os.chdir(cwd)
            try:
                self._compiler = CompileLaTeX(**compiler_kwargs)
                self._compiler.compile_tex()
            finally:
                os.chdir(original_cwd)

            pdf_path = diff_path.with_suffix(".pdf")
            out_pdf = Path(cwd) / "out" / pdf_path.name
            if not out_pdf.exists():
                out_pdf = Path(cwd) / pdf_path.name

            if out_pdf.exists() or pdf_path.exists():
                self.logger.info(f"差异 PDF 编译成功: {out_pdf}")
                return True
            return False

        except (CompilationError, ToolchainNotFoundError, FileOperationError) as e:
            raise LaTeXDiffError(message=f"差异文件编译失败: {e.message}") from e
        except Exception as e:
            raise LaTeXDiffError(message=f"差异文件编译时发生异常: {e}") from e

    def full_diff_workflow(
        self,
        old_file: str,
        new_file: str,
        output_diff: Optional[str] = None,
        do_compile: bool = True,
        flatten: bool = False,
        engine: Optional[str] = None,
        **compile_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        完整工作流：生成差异文件 → （可选）编译

        参数:
            old_file: 旧版本 TeX 文件路径
            new_file: 新版本 TeX 文件路径
            output_diff: 输出差异文件路径，默认 {new_file}-diff.tex
            do_compile: 是否编译生成 PDF，默认 True
            flatten: 是否使用 latexdiff --flatten 选项
            engine: TeX 引擎名称
            **compile_kwargs: 传递给 compile_diff 的其他参数

        返回:
            dict: {
                "diff_file": Path,       # 生成的 diff 文件路径
                "compiled": bool,        # 是否编译成功
                "output_pdf": Optional[Path]  # 输出 PDF 路径（如果编译）
            }
        """
        new_path = Path(new_file)

        if output_diff is None:
            output_diff = str(new_path.with_name(f"{new_path.stem}-diff"))

        diff_file = self.generate_diff(
            old_file=old_file,
            new_file=new_file,
            output_file=output_diff,
            flatten=flatten,
        )

        result: Dict[str, Any] = {
            "diff_file": diff_file,
            "compiled": False,
            "output_pdf": None,
        }

        if do_compile:
            try:
                compiled = self.compile_diff(
                    diff_file=diff_file,
                    engine=engine,
                    **compile_kwargs,
                )
                result["compiled"] = compiled
                if compiled:
                    pdf_path = diff_file.with_suffix(".pdf")
                    out_pdf = diff_file.parent / "out" / pdf_path.name
                    result["output_pdf"] = out_pdf if out_pdf.exists() else pdf_path
            except LaTeXDiffError as e:
                self.logger.error(f"编译失败: {e.message}")
                console.print(f"[bold red]{_('编译失败')}: {e.message}[/bold red]")
                result["compiled"] = False

        return result


def get_version(file_path: str) -> Optional[str]:
    """
    获取文件的版本控制系统版本（预留接口，暂不实现完整功能）

    参数:
        file_path: 文件路径

    返回:
        Optional[str]: 版本标识，不可用时返回 None
    """
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            cwd=str(Path(file_path).parent),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def parse_diff_args(cli_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 CLI 中与 diff 相关的参数（为 Task 12 预留接口）

    参数:
        cli_args: CLI 参数字典，可包含以下键：
            - diff: bool，是否启用 diff 模式
            - diff_old: str，旧版本文件
            - diff_new: str，新版本文件
            - diff_flatten: bool，是否压平
            - diff_fast: bool，是否使用快速模式
            - diff_output: str，输出文件路径
            - diff_engine: str，TeX 引擎

    返回:
        dict: 解析后的配置字典
    """
    config: Dict[str, Any] = {
        "enabled": bool(cli_args.get("diff", False)),
        "old_file": cli_args.get("diff_old"),
        "new_file": cli_args.get("diff_new"),
        "flatten": bool(cli_args.get("diff_flatten", False)),
        "fast": bool(cli_args.get("diff_fast", False)),
        "output": cli_args.get("diff_output"),
        "engine": cli_args.get("diff_engine"),
        "do_compile": True,
    }
    return config


def run_diff_from_cli(cli_args: Dict[str, Any]) -> bool:
    """
    从 CLI 参数执行 diff 工作流（为 Task 12 预留接口）

    参数:
        cli_args: CLI 参数字典

    返回:
        bool: 是否执行成功
    """
    config = parse_diff_args(cli_args)
    if not config["enabled"]:
        return False

    if not config["old_file"] or not config["new_file"]:
        console.print("[bold red]错误: --diff 模式需要指定 --diff-old 和 --diff-new 参数[/bold red]")
        return False

    tool = LaTeXDiffTool()

    if not tool.detect_available():
        console.print("[bold red]错误: 未检测到 latexdiff 命令[/bold red]")
        return False

    try:
        result = tool.full_diff_workflow(
            old_file=config["old_file"],
            new_file=config["new_file"],
            output_diff=config["output"],
            do_compile=config["do_compile"],
            flatten=config["flatten"],
            engine=config["engine"],
        )
        return result["compiled"] or not config["do_compile"]
    except LaTeXDiffError as e:
        console.print(f"[bold red]LaTeXDiff 错误: {e.message}[/bold red]")
        return False
    except Exception as e:
        console.print(f"[bold red]错误: {e}[/bold red]")
        return False


class LaTeXDiff_Aux(LaTeXDiffTool):
    """
    旧版 LaTeXDiff_Aux 类（已弃用），保持向后兼容

    .. deprecated::
        请使用 LaTeXDiffTool 类代替
    """

    def __init__(self, suffixes_aux, auxdir):
        warn(
            "LaTeXDiff_Aux 类已弃用，请使用 LaTeXDiffTool 类代替",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        self.suffixes_aux = suffixes_aux
        self.auxdir = Path(auxdir)

    def check_aux_files(self, file_name):
        """
        指定的旧 TeX 辅助文件存在检查（向后兼容方法）

        参数:
            file_name: 文件名（不带后缀）

        返回:
            bool: 指定的辅助文件是否存在
        """
        aux_files = [f"{file_name}{suffix}" for suffix in self.suffixes_aux]
        for file in aux_files:
            if (self.auxdir / file).exists():
                return True
        return False

    def flatten_Latex(self, file_name):
        """
        压平多文件（向后兼容方法）

        参数:
            file_name: 主 LaTeX 文件名称（不带 .tex 扩展名）

        返回:
            str: 压平后的文件名称（不带后缀）
        """
        warn(
            "flatten_Latex 方法已弃用，请使用 flatten_tex 方法代替",
            DeprecationWarning,
            stacklevel=2,
        )
        output_file_name = f"{file_name}-flatten"
        self.flatten_tex(
            main_file=f"{file_name}.tex",
            output_file=f"{output_file_name}.tex",
        )
        return output_file_name

    def aux_files_both_exist(self, old_file, new_file, suffix):
        """
        判断在指定后缀的新旧辅助文件是否同时存在（向后兼容方法）

        参数:
            old_file: 旧文件名，无后缀
            new_file: 新文件名，无后缀
            suffix: 后缀名，如 '.bbl'

        返回:
            str or None: 如果同时存在返回后缀，否则返回 None
        """
        old_file_path = Path(old_file + suffix)
        new_file_path = Path(new_file + suffix)
        if old_file_path.exists() and new_file_path.exists():
            self.logger.info(f"新旧辅助文件同时存在: {old_file_path} {new_file_path}")
            return suffix
        return None

    def compile_LaTeXDiff(self, old_tex_file, new_tex_file, diff_tex_file, suffix):
        """
        编译 LaTeXDiff（向后兼容方法，已修复 shell 重定向 bug）

        参数:
            old_tex_file: 旧 TeX 文件名（无后缀）
            new_tex_file: 新 TeX 文件名（无后缀）
            diff_tex_file: 输出 diff TeX 文件名（无后缀）
            suffix: 文件后缀（通常为 '.tex'）
        """
        warn(
            "compile_LaTeXDiff 方法已弃用，请使用 generate_diff 方法代替",
            DeprecationWarning,
            stacklevel=2,
        )
        self.generate_diff(
            old_file=f"{old_tex_file}{suffix}",
            new_file=f"{new_tex_file}{suffix}",
            output_file=f"{diff_tex_file}{suffix}",
            encoding="utf8",
        )
