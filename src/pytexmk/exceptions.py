# -*- coding: utf-8 -*-
"""
PyTeXMK 异常定义模块
"""

from pytexmk.language import set_language

_ = set_language("exceptions")


class PyTeXMKError(Exception):
    """PyTeXMK 所有自定义异常的基类"""

    def __init__(self, message: str | None = None, exit_code: int = 1):
        if message is None:
            message = _("PyTeXMK 发生错误")
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


class ToolchainNotFoundError(PyTeXMKError):
    """找不到所需的工具链（如 pdflatex、xelatex 等）"""

    def __init__(self, message: str | None = None, tool_name: str | None = None, exit_code: int = 2):
        if message is None:
            if tool_name:
                message = _("找不到工具链: %(tool)s，请确认已安装并添加到系统 PATH") % {"tool": tool_name}
            else:
                message = _("找不到所需的工具链，请确认已安装并添加到系统 PATH")
        self.tool_name = tool_name
        super().__init__(message, exit_code)


class CompilationError(PyTeXMKError):
    """编译过程中发生错误"""

    def __init__(
        self, message: str | None = None, returncode: int | None = None, log_file: str | None = None, exit_code: int = 3
    ):
        if message is None:
            message = _("编译失败，请查看日志文件以获取详细信息")
        self.returncode = returncode
        self.log_file = log_file
        super().__init__(message, exit_code)


class CompilationTimeoutError(PyTeXMKError):
    """编译超时"""

    def __init__(self, message: str | None = None, timeout: float | None = None, exit_code: int = 4):
        if message is None:
            if timeout is not None:
                message = _("编译超时（%(timeout)s 秒），进程已被强制终止") % {"timeout": timeout}
            else:
                message = _("编译超时，进程已被强制终止")
        self.timeout = timeout
        super().__init__(message, exit_code)


class FileOperationError(PyTeXMKError):
    """文件操作错误"""

    def __init__(self, message: str | None = None, filepath: str | None = None, exit_code: int = 5):
        if message is None:
            if filepath:
                message = _("文件操作失败: %(path)s") % {"path": filepath}
            else:
                message = _("文件操作失败")
        self.filepath = filepath
        super().__init__(message, exit_code)


class ConfigurationError(PyTeXMKError):
    """配置错误"""

    def __init__(self, message: str | None = None, config_key: str | None = None, exit_code: int = 6):
        if message is None:
            if config_key:
                message = _("配置错误: %(key)s") % {"key": config_key}
            else:
                message = _("配置错误")
        self.config_key = config_key
        super().__init__(message, exit_code)


class InvalidEngineError(PyTeXMKError):
    """无效的 TeX 引擎"""

    def __init__(self, message: str | None = None, engine: str | None = None, exit_code: int = 7):
        if message is None:
            if engine:
                message = _("无效的 TeX 引擎: %(engine)s") % {"engine": engine}
            else:
                message = _("无效的 TeX 引擎")
        self.engine = engine
        super().__init__(message, exit_code)


class LaTeXDiffError(PyTeXMKError):
    """LaTeXDiff 相关错误"""

    def __init__(self, message: str | None = None, exit_code: int = 8):
        if message is None:
            message = _("LaTeXDiff 操作失败")
        super().__init__(message, exit_code)
