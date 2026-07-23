# -*- coding: utf-8 -*-
"""
工具链管理模块
"""

import shutil
import logging
import subprocess
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Tuple, List

from rich.console import Console

from pytexmk.exceptions import ToolchainNotFoundError
from pytexmk.language import set_language

_ = set_language("toolchain")

logger = logging.getLogger(__name__)
console = Console(legacy_windows=False)


def detect_tool_available(executable: str, custom_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    检测工具是否在 PATH 中可用，返回 (available, version_string)

    参数:
        executable: 可执行文件名
        custom_path: 自定义路径（如果指定则直接使用该路径）

    返回:
        (是否可用, 版本字符串)
    """
    path = custom_path if custom_path else shutil.which(executable)
    if not path:
        return False, None

    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        version_output = result.stdout.strip() or result.stderr.strip()
        if result.returncode == 0 and version_output:
            first_line = version_output.splitlines()[0] if version_output else None
            return True, first_line
        return True, None
    except (subprocess.TimeoutExpired, OSError):
        return True, None


class ToolchainBase(ABC):
    """所有工具的抽象基类"""

    name: str
    executable: str

    def __init__(self):
        self.version: Optional[str] = None
        self.available: bool = False
        self._custom_path: Optional[str] = None

    def detect(self, custom_path: Optional[str] = None) -> bool:
        """
        检测工具是否可用

        参数:
            custom_path: 自定义可执行文件路径

        返回:
            是否可用
        """
        self._custom_path = custom_path
        available, version = detect_tool_available(self.executable, custom_path)
        self.available = available
        self.version = version
        if available:
            logger.debug(_("检测到工具 %(name)s: %(version)s") % {"name": self.name, "version": version or _("未知版本")})
        else:
            logger.debug(_("未检测到工具 %(name)s") % {"name": self.name})
        return available

    def get_executable_path(self) -> str:
        """获取可执行文件路径（优先使用自定义路径）"""
        return self._custom_path if self._custom_path else self.executable

    def get_version(self) -> Optional[str]:
        """
        运行 --version 获取版本字符串

        返回:
            版本字符串或 None
        """
        return self.version

    def ensure_available(self) -> None:
        """
        确保工具可用，否则抛出 ToolchainNotFoundError

        异常:
            ToolchainNotFoundError: 工具不可用时抛出
        """
        if not self.available:
            raise ToolchainNotFoundError(tool_name=self.name)

    @abstractmethod
    def build_command(self, *args, **kwargs) -> List[str]:
        """
        构建命令列表（抽象方法，子类实现）

        返回:
            命令列表
        """
        pass


class PdfLaTeXEngine(ToolchainBase):
    """pdfLaTeX 引擎"""

    name = "pdflatex"
    executable = "pdflatex"

    def build_command(
        self,
        project_name: str,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        non_quiet: bool = False,
        shell_escape: bool = True,
        file_line_error: bool = True,
        halt_on_error: bool = True,
        synctex: bool = True,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        cmd = [self.get_executable_path()]

        if shell_escape:
            cmd.append("-shell-escape")
        if file_line_error:
            cmd.append("-file-line-error")
        if halt_on_error:
            cmd.append("-halt-on-error")

        cmd.append("-interaction=nonstopmode" if non_quiet else "-interaction=batchmode")

        if synctex:
            cmd.append("-synctex=1")

        if outdir:
            cmd.append(f"-output-directory={outdir}")

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(f"{project_name}.tex")
        return cmd


class XeLaTeXEngine(ToolchainBase):
    """XeLaTeX 引擎"""

    name = "xelatex"
    executable = "xelatex"

    def build_command(
        self,
        project_name: str,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        non_quiet: bool = False,
        shell_escape: bool = True,
        file_line_error: bool = True,
        halt_on_error: bool = True,
        synctex: bool = True,
        no_pdf: bool = True,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        cmd = [self.get_executable_path()]

        if shell_escape:
            cmd.append("-shell-escape")
        if file_line_error:
            cmd.append("-file-line-error")
        if halt_on_error:
            cmd.append("-halt-on-error")

        cmd.append("-interaction=nonstopmode" if non_quiet else "-interaction=batchmode")

        if synctex:
            cmd.append("-synctex=1")

        if no_pdf:
            cmd.append("-no-pdf")

        if outdir:
            cmd.append(f"-output-directory={outdir}")

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(f"{project_name}.tex")
        return cmd


class LuaLaTeXEngine(ToolchainBase):
    """LuaLaTeX 引擎"""

    name = "lualatex"
    executable = "lualatex"

    def build_command(
        self,
        project_name: str,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        non_quiet: bool = False,
        shell_escape: bool = True,
        file_line_error: bool = True,
        halt_on_error: bool = True,
        synctex: bool = True,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        cmd = [self.get_executable_path()]

        if shell_escape:
            cmd.append("-shell-escape")
        if file_line_error:
            cmd.append("-file-line-error")
        if halt_on_error:
            cmd.append("-halt-on-error")

        cmd.append("-interaction=nonstopmode" if non_quiet else "-interaction=batchmode")

        if synctex:
            cmd.append("-synctex=1")

        if outdir:
            cmd.append(f"-output-directory={outdir}")

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(f"{project_name}.tex")
        return cmd


class BibTeXTool(ToolchainBase):
    """BibTeX 工具"""

    name = "bibtex"
    executable = "bibtex"

    def build_command(
        self,
        project_name: str,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        quiet: bool = False,
    ) -> List[str]:
        cmd = [self.get_executable_path()]
        cmd.append(project_name)
        return cmd


class BiberTool(ToolchainBase):
    """Biber 工具"""

    name = "biber"
    executable = "biber"

    def build_command(
        self,
        project_name: str,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        quiet: bool = False,
    ) -> List[str]:
        cmd = [self.get_executable_path()]
        if quiet:
            cmd.append("--quiet")
        if outdir:
            cmd.append(f"--output-directory={outdir}")
        cmd.append(project_name)
        return cmd


class MakeindexTool(ToolchainBase):
    """Makeindex 索引工具"""

    name = "makeindex"
    executable = "makeindex"

    def build_command(
        self,
        project_name: str,
        style_file: Optional[str] = None,
        out_ext: Optional[str] = None,
        in_ext: Optional[str] = None,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
    ) -> List[str]:
        cmd = [self.get_executable_path()]

        if style_file:
            cmd.extend(["-s", style_file])
        if out_ext:
            cmd.extend(["-o", f"{project_name}.{out_ext.lstrip('.')}"])
        if in_ext:
            in_file = f"{project_name}.{in_ext.lstrip('.')}"
        else:
            in_file = f"{project_name}.idx"

        cmd.append(in_file)
        return cmd


class XindyTool(ToolchainBase):
    """Xindy 索引工具"""

    name = "xindy"
    executable = "xindy"

    def build_command(
        self,
        project_name: str,
        language: str = "general",
        codepage: str = "utf8",
        module: Optional[str] = None,
        out_ext: Optional[str] = None,
        in_ext: Optional[str] = None,
        log_file: Optional[str] = None,
        outdir: Optional[str] = None,
        auxdir: Optional[str] = None,
        quiet: bool = False,
    ) -> List[str]:
        cmd = [self.get_executable_path()]

        cmd.extend(["-L", language])
        cmd.extend(["-C", codepage])

        if module:
            cmd.extend(["-M", module])

        if log_file:
            cmd.extend(["-t", log_file])
        if quiet:
            cmd.append("-q")

        if out_ext:
            out_file = f"{project_name}.{out_ext.lstrip('.')}"
        else:
            out_file = f"{project_name}.ind"
        cmd.extend(["-o", out_file])

        if in_ext:
            in_file = f"{project_name}.{in_ext.lstrip('.')}"
        else:
            in_file = f"{project_name}.idx"
        cmd.append(in_file)

        return cmd


class DvipdfmxTool(ToolchainBase):
    """DVIPDFMX 工具"""

    name = "dvipdfmx"
    executable = "dvipdfmx"

    def build_command(
        self,
        project_name: str,
        quiet: bool = False,
        version: str = "2.0",
    ) -> List[str]:
        cmd = [self.get_executable_path()]
        if quiet:
            cmd.append("-q")
        cmd.extend(["-V", version])
        cmd.append(project_name)
        return cmd


class ToolchainManager:
    """工具链管理器"""

    ENGINE_PRIORITY = ["xelatex", "lualatex", "pdflatex"]

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        self.engines: Dict[str, ToolchainBase] = {
            "pdflatex": PdfLaTeXEngine(),
            "xelatex": XeLaTeXEngine(),
            "lualatex": LuaLaTeXEngine(),
        }

        self.bib_tools: Dict[str, ToolchainBase] = {
            "bibtex": BibTeXTool(),
            "biber": BiberTool(),
        }

        self.index_tools: Dict[str, ToolchainBase] = {
            "makeindex": MakeindexTool(),
            "xindy": XindyTool(),
        }

        self.dvipdfmx = DvipdfmxTool()

        self._detected = False

    def detect_all(self) -> Dict[str, bool]:
        """
        检测所有工具可用性

        返回:
            {工具名: 是否可用}
        """
        result = {}

        for name, engine in self.engines.items():
            custom_path = self.config.get(f"{name}_path")
            result[name] = engine.detect(custom_path)

        for name, tool in self.bib_tools.items():
            custom_path = self.config.get(f"{name}_path")
            result[name] = tool.detect(custom_path)

        for name, tool in self.index_tools.items():
            custom_path = self.config.get(f"{name}_path")
            result[name] = tool.detect(custom_path)

        custom_path = self.config.get("dvipdfmx_path")
        result["dvipdfmx"] = self.dvipdfmx.detect(custom_path)

        self._detected = True
        logger.debug(_("工具检测结果: %(result)s") % {"result": result})
        return result

    def _auto_detect_if_needed(self) -> None:
        """如果尚未检测，则自动检测"""
        if not self._detected:
            self.detect_all()

    def get_engine(
        self,
        preference: Optional[str] = None,
        auto_detect: bool = True,
        doc_features: Optional[Dict] = None,
    ) -> ToolchainBase:
        """
        获取 TeX 引擎，支持降级

        参数:
            preference: 首选引擎名称
            auto_detect: 如果未检测是否自动检测
            doc_features: 文档特征（预留）

        返回:
            可用的引擎实例

        异常:
            ToolchainNotFoundError: 所有引擎都不可用时抛出
        """
        if auto_detect:
            self._auto_detect_if_needed()

        candidates = []
        if preference:
            pref_lower = preference.lower()
            if pref_lower in self.engines:
                candidates.append(pref_lower)
            for eng in self.ENGINE_PRIORITY:
                if eng != pref_lower and eng not in candidates:
                    candidates.append(eng)
        else:
            candidates = list(self.ENGINE_PRIORITY)

        first_choice = True
        for eng_name in candidates:
            engine = self.engines[eng_name]
            if engine.available:
                if not first_choice:
                    console.print(_("[yellow]警告: 首选引擎不可用，降级使用 %(engine)s[/yellow]") % {"engine": eng_name})
                return engine
            first_choice = False

        raise ToolchainNotFoundError(message=_("未找到任何可用的 TeX 引擎（pdflatex/xelatex/lualatex）"))

    def get_bib_tool(self, bib_engine: str) -> ToolchainBase:
        """
        获取参考文献工具

        参数:
            bib_engine: 工具名称（bibtex/biber）

        返回:
            工具实例

        异常:
            ToolchainNotFoundError: 工具不存在或不可用时抛出
        """
        bib_engine_lower = bib_engine.lower()
        if bib_engine_lower not in self.bib_tools:
            raise ToolchainNotFoundError(tool_name=bib_engine)
        self._auto_detect_if_needed()
        tool = self.bib_tools[bib_engine_lower]
        tool.ensure_available()
        return tool

    def get_index_tool(self, index_engine: str = "makeindex") -> ToolchainBase:
        """
        获取索引工具，xindy 不可用时自动回退到 makeindex

        参数:
            index_engine: 工具名称（makeindex/xindy）

        返回:
            工具实例
        """
        index_engine_lower = index_engine.lower()
        self._auto_detect_if_needed()

        if index_engine_lower == "xindy":
            xindy = self.index_tools["xindy"]
            if xindy.available:
                return xindy
            console.print(_("[yellow]警告: xindy 不可用，回退使用 makeindex[/yellow]"))
            return self.index_tools["makeindex"]

        if index_engine_lower not in self.index_tools:
            raise ToolchainNotFoundError(tool_name=index_engine)

        tool = self.index_tools[index_engine_lower]
        tool.ensure_available()
        return tool

    def select_bib_tool(self, aux_content: str) -> Tuple[Optional[ToolchainBase], Optional[str]]:
        """
        分析 aux 内容自动选择 bib 工具

        参数:
            aux_content: aux 文件内容

        返回:
            (工具实例, bib 文件名)，如果不需要参考文献工具则返回 (None, None)
        """
        self._auto_detect_if_needed()

        if re.search(r"\\abx@aux@refcontext", aux_content):
            biber = self.bib_tools["biber"]
            if biber.available:
                return biber, None

        if re.search(r"\\bibdata", aux_content):
            bibtex = self.bib_tools["bibtex"]
            match = re.search(r"\\bibdata\{(.*)\}", aux_content)
            bib_file = match.group(1) if match else None
            if bibtex.available:
                return bibtex, bib_file

        return None, None

    def select_index_tools(self, aux_content: str, project_name: str) -> List[Tuple[ToolchainBase, Dict]]:
        """
        分析 aux 内容自动检测需要的索引工具及其参数

        参数:
            aux_content: aux 文件内容
            project_name: 项目名称

        返回:
            [(工具实例, 参数字典), ...]
        """
        self._auto_detect_if_needed()
        tools = []

        makeindex = self.index_tools["makeindex"]
        xindy = self.index_tools["xindy"]
        use_xindy = xindy.available

        index_tool = xindy if use_xindy else makeindex

        glossary_pattern = r"\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}"
        for match in re.finditer(glossary_pattern, aux_content):
            name, ext_o, ext_i = match.groups()
            if use_xindy:
                params = {
                    "project_name": project_name,
                    "language": "general",
                    "module": None,
                    "out_ext": ext_o,
                    "in_ext": ext_i,
                }
            else:
                params = {
                    "project_name": project_name,
                    "style_file": f"{project_name}.ist",
                    "out_ext": ext_o,
                    "in_ext": ext_i,
                }
            tools.append((index_tool, params))

        if re.search(r"\\@istfilename", aux_content) or re.search(r"nomencl", aux_content):
            if use_xindy:
                params = {
                    "project_name": project_name,
                    "language": "general",
                    "module": "nomencl",
                    "out_ext": "nls",
                    "in_ext": "nlo",
                }
            else:
                params = {
                    "project_name": project_name,
                    "style_file": "nomencl.ist",
                    "out_ext": "nls",
                    "in_ext": "nlo",
                }
            tools.append((index_tool, params))

        if re.search(r"\\makeindex", aux_content) or re.search(r"\\indexentry", aux_content):
            if use_xindy:
                params = {
                    "project_name": project_name,
                    "language": "general",
                    "out_ext": "ind",
                    "in_ext": "idx",
                }
            else:
                params = {
                    "project_name": project_name,
                    "out_ext": "ind",
                    "in_ext": "idx",
                }
            tools.append((index_tool, params))

        return tools
