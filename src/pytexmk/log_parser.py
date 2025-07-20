# -*- coding: utf-8 -*-
"""
log_analysis.py - LaTeX 编译日志分析模块

功能：
1. 解析 LaTeX 编译输出中的错误、警告和排版信息。
2. 支持 BibTeX 和 Biber 日志解析。
3. 支持忽略用户配置的特定日志条目。
4. 支持 Bad Box 提示显示。
5. 结构化输出用于 UI 显示或命令行提示。
"""

import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import toml

from pytexmk.language import set_language

logger = logging.getLogger(__name__)
_ = set_language("log_parser")


# ========================
# 日志类型枚举
# ========================


class LogType(Enum):
    ERROR = "error"
    WARNING = "warning"
    TYPESET = "typesetting"
    INFO = "info"
    FONT = "font"
    GRAPHIC = "graphic"
    PAGE = "page"

    def __lt__(self, other):
        """支持按优先级排序"""
        order = {
            LogType.ERROR: 0,
            LogType.WARNING: 1,
            LogType.TYPESET: 2,
            LogType.FONT: 3,
            LogType.GRAPHIC: 4,
            LogType.PAGE: 5,
            LogType.INFO: 6,
        }
        return order[self] < order.get(other, 7)


# ========================
# 数据结构定义
# ========================

LogEntry = Dict[str, Union[str, int, LogType]]


# ========================
# 正则表达式定义（与 latexlog.ts 完全一致）
# ========================

# 错误相关
latex_error_re1 = re.compile(r"^(?:(.*):(\d+):|!)(?: (.+) Error:)? (.+?)$")
latex_error_re2 = re.compile(r"^!(?: (.+) Error:)? (.+?)$")

# 排版警告（Bad Boxes）
overfull_box_re = re.compile(
    r"^(Overfull \$[vh]box $[^)]+\$) in paragraph at lines (\d+)--(\d+)$"
)
overfull_box_alt_re = re.compile(
    r"^(Overfull \$[vh]box $[^)]+\$) detected at line (\d+)$"
)
overfull_box_output_re = re.compile(
    r"^(Overfull \$[vh]box $[^)]+\$) has occurred while \\output is active(?: \$(\d+)\$)?$"
)

underfull_box_re = re.compile(
    r"^(Underfull \$[vh]box $[^)]+\$) in paragraph at lines (\d+)--(\d+)$"
)
underfull_box_alt_re = re.compile(
    r"^(Underfull \$[vh]box $[^)]+\$) detected at line (\d+)$"
)
underfull_box_output_re = re.compile(
    r"^(Underfull \$[vh]box $[^)]+\$) has occurred while \\output is active(?: \$(\d+)\$)?$"
)

# 警告信息
latex_warn_re = re.compile(
    r"^((?:(?:Class|Package|Module) \S)|LaTeX(?: \S*)?|LaTeX3) (Warning|Info):\s+(.*?)(?: on(?: input)? line (\d+))?(\.|\?)?$"
)

# 包警告后续行
package_warning_extra_lines_re = re.compile(
    r"^$\.$([a-zA-Z]+)\s+(.+?)(?: +on input line (\d+))?$"
)

# 缺失字符
missing_char_re = re.compile(r"^\s(Missing character:.+?!)$")

# 空参考文献
bib_empty_re = re.compile(r"^Empty `thebibliography\' environment$")

# Biber 警告
biber_warn_re = re.compile(
    r"^Biber warning:.*WARN - I didn\'t find a database entry for \'([^\']+)\'$"
)

# 未定义引用
undefined_reference_re = re.compile(
    r"^LaTeX Warning: (Reference|Citation) `(.*?)\' on page \d+ undefined on input line (\d+)\.$"
)

# 消息行（带代码位置）
message_line_re = re.compile(r"^l\.\d+\s(...)?(.*)$")

# 文件栈开始与结束
file_stack_open_re = re.compile(r"$([^$]*)")
file_stack_close_re = re.compile(r"$")


# ========================
# 日志分析器类
# ========================


class LatexLogParser:
    def __init__(self, root_file: str = None):
        self.build_log: List[LogEntry] = []
        self.current_result: Optional[LogEntry] = None
        self.file_stack: List[str] = []
        self.root_file: str = root_file or ""
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0
        self._resolved_paths = {}

    def parse(self, log: str, root_file: Optional[str] = None) -> List[LogEntry]:
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            logger.warning(_("根文件未指定，无法继续解析日志"))
            return []

        self.file_stack = [self.root_file]
        self.build_log.clear()
        self.reset_state()

        lines = log.split("\n")
        for line in lines:
            self.parse_line(line)

        # 最后一条日志入栈
        if self.current_result and not re.match(
            bib_empty_re, self.current_result["text"]
        ):
            self.build_log.append(self.current_result)

        logger.info(_("共解析 %(args)s 条日志消息" % {"args": len(self.build_log)}))
        return self.build_log

    def reset_state(self):
        """重置解析状态"""
        self.current_result = {
            "type": "",
            "file": "",
            "line": 1,
            "text": "",
            "error_pos_text": "",
        }
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0

    def parse_line(self, line: str):
        line = line.strip("\x00")  # 去除多余空字符

        # 忽略空行
        if self.search_empty_line:
            if not line or (self.inside_error and line.startswith(" ")):
                self.current_result["text"] += "\n" + line
                self.search_empty_line = False
                self.inside_error = False
                return
            else:
                package_match = package_warning_extra_lines_re.match(line)
                if package_match:
                    self.current_result["text"] += (
                        f"\n({package_match.group(1)})\t{package_match.group(2)}"
                    )
                    self.current_result["line"] = (
                        int(package_match.group(3)) if package_match.group(3) else 1
                    )
                else:
                    self.current_result["text"] += "\n" + line
                self.search_empty_line = False
                return

        # 解析错误
        error_match = None
        for pattern in [latex_error_re1, latex_error_re2]:
            error_match = pattern.match(line)
            if error_match:
                break
        if error_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            file = error_match.group(1) or self.get_current_file()
            line_num = int(error_match.group(2)) if error_match.group(2) else 1
            msg = (error_match.group(3) or "") + ": " + (error_match.group(4) or "")
            self.current_result = {
                "type": LogType.ERROR,
                "file": file,
                "line": line_num,
                "text": msg,
                "error_pos_text": "",
            }
            self.search_empty_line = True
            self.inside_error = True
            return

        # 解析警告
        warn_match = latex_warn_re.match(line)
        if warn_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            category = warn_match.group(1)
            level = warn_match.group(2)
            message = warn_match.group(3) or ""
            line_num = warn_match.group(4)
            suffix = warn_match.group(5) or ""
            full_message = (
                f"{category} {level}: {message}{('.' + suffix) if suffix else ''}"
            )

            log_type = LogType.WARNING if level == "Warning" else LogType.INFO

            self.current_result = {
                "type": log_type,
                "file": self.get_current_file(),
                "line": int(line_num) if line_num else 1,
                "text": full_message,
            }
            self.search_empty_line = True
            return

        # 解析未定义引用
        if undefined_reference_re.match(line):
            match = undefined_reference_re.match(line)
            if match:
                ref_type, label, line_num = match.groups()
                if self.current_result and self.current_result["type"]:
                    self.build_log.append(self.current_result)
                self.current_result = {
                    "type": LogType.WARNING,
                    "file": self.get_current_file(),
                    "line": int(line_num),
                    "text": f"找不到 {ref_type.lower()} `{label}`",
                    "error_pos_text": label,
                }
                self.search_empty_line = False
                return

        # 解析 Bad Box
        if self.parse_bad_box(line):
            return

        # 解析缺失字符
        miss_match = missing_char_re.match(line)
        if miss_match:
            if self.current_result and self.current_result["type"]:
                self.build_log.append(self.current_result)
            self.current_result = {
                "type": LogType.WARNING,
                "file": self.get_current_file(),
                "line": 1,
                "text": miss_match.group(1),
            }
            self.search_empty_line = False
            return

        # 处理消息行（错误代码片段）
        if self.inside_error:
            match = message_line_re.match(line)
            if match:
                sub_line = match.group(2)
                self.current_result["error_pos_text"] = sub_line
                self.search_empty_line = False
                self.inside_error = False
                return

        # 文件栈处理
        self.parse_file_stack(line)

    def parse_bad_box(self, line: str) -> bool:
        bad_box_patterns = [
            overfull_box_re,
            overfull_box_alt_re,
            overfull_box_output_re,
            underfull_box_re,
            underfull_box_alt_re,
            underfull_box_output_re,
        ]
        for pattern in bad_box_patterns:
            match = pattern.match(line)
            if match:
                if self.current_result and self.current_result["type"]:
                    self.build_log.append(self.current_result)
                file = self.get_current_file()
                text = match.group(1)
                line_num = (
                    int(match.group(2)) if match.groups() >= 3 and match.group(2) else 1
                )
                self.current_result = {
                    "type": LogType.TYPESET,
                    "file": file,
                    "line": line_num,
                    "text": text,
                }
                self.inside_box_warn = True
                self.search_empty_line = False
                return True
        return False

    def parse_file_stack(self, line: str):
        open_match = file_stack_open_re.search(line)
        close_match = file_stack_close_re.search(line)

        if open_match:
            path_part = open_match.group(1).strip()
            if path_part:
                self.file_stack.append(path_part)
            else:
                self.nested += 1
        elif close_match:
            if self.nested > 0:
                self.nested -= 1
            else:
                if len(self.file_stack) > 1:
                    self.file_stack.pop()

    def get_current_file(self) -> str:
        current_path = self.file_stack[-1]
        if current_path in self._resolved_paths:
            return self._resolved_paths[current_path]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / current_path).resolve())
        except Exception:
            resolved = current_path

        self._resolved_paths[current_path] = resolved
        return resolved

    def show_log(self, use_logger=True, show_info=False):
        """
        展示日志（可集成到 CLI 或 GUI）

        :param use_logger: 是否使用 logging 输出，默认为是
        :param show_info: 是否显示 info 类型日志
        """
        # 按优先级排序
        sorted_logs = sorted(self.build_log, key=lambda x: x["type"])

        # 分类提取
        errors = [entry for entry in sorted_logs if entry["type"] == LogType.ERROR]
        warnings = [entry for entry in sorted_logs if entry["type"] == LogType.WARNING]
        typesets = [entry for entry in sorted_logs if entry["type"] == LogType.TYPESET]
        fonts = [entry for entry in sorted_logs if entry["type"] == LogType.FONT]
        graphics = [entry for entry in sorted_logs if entry["type"] == LogType.GRAPHIC]
        pages = [entry for entry in sorted_logs if entry["type"] == LogType.PAGE]
        infos = [entry for entry in sorted_logs if entry["type"] == LogType.INFO]

        def format_message(entry: Dict[str, Any]) -> str:
            file_path = Path(entry["file"])
            try:
                rel_path = file_path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                rel_path = file_path.name  # 只显示文件名
            level = entry["type"].value.upper()
            text = entry["text"]
            return f"{rel_path}:{entry['line']} --> {text}"

        # 输出各类消息
        for entry in errors:
            msg = format_message(entry)
            logger.error(msg) if use_logger else print(msg)

        for entry in warnings:
            msg = format_message(entry)
            logger.warning(msg) if use_logger else print(msg)

        for entry in typesets:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in fonts:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in graphics:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in pages:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        for entry in infos:
            msg = format_message(entry)
            logger.info(msg) if use_logger else print(msg)

        if not (
            errors
            or warnings
            or typesets
            or fonts
            or graphics
            or pages
            or (show_info and infos)
        ):
            success_msg = _("未发现错误或警告")
            logger.info(success_msg) if use_logger else print(success_msg)

    def show_editor_jump_format(self):
        for entry in sorted(self.build_log, key=lambda x: x["type"]):
            file_path = Path(entry["file"]).name
            msg = f"{file_path}:{entry['line']}: {entry['text']}"
            logger.info(msg)

    def logparser_cli(self, auxdir, project_name):
        """
        命令行接口：解析编译日志并输出结果

        :param auxdir: 辅助文件所在目录
        :param project_name: LaTeX 项目的主文件名（不带扩展名）
        """
        # 构建日志文件路径
        log_path = Path(auxdir) / f"{project_name}.log"

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
        except FileNotFoundError:
            logger.error(_("找不到日志文件: %(args)s") % {"args": str(log_path)})
            return

        self.root_file = project_name + ".tex"
        log_entries = self.parse(log_content)
        self.show_log(use_logger=True, show_info=True)


# ========================
# BibTeX 日志相关
# ========================

# BibTeX 警告
single_line_bibtex_warning_re = re.compile(r"^Warning--(.+) in ([^\s]+)\s*$")
multi_line_bibtex_warning_re = re.compile(
    r"(?m)^Warning--(.+)\n--line (\d+) of file (.+)$"
)
multi_line_bibtex_error_re = re.compile(
    r"^(.*)---line (\d+) of file (.*)\n([\s\S]*?)\nI\'m skipping whatever remains of this entry$",
    re.MULTILINE,
)
bad_cross_ref_bibtex_re = re.compile(
    r'^(A bad cross reference---entry ".+?"\nrefers to entry.+?, which doesn\'t exist)$',
    re.MULTILINE,
)
multi_line_macro_bibtex_error_re = re.compile(
    r"^(.*)\n?---line (\d+) of file (.*)\n([\s\S]*?)\nI\'m skipping whatever remains of this command$",
    re.MULTILINE,
)
error_aux_file_re = re.compile(r"^(.*)---while reading file (.*)$", re.MULTILINE)


# ========================
# BibTeX 日志解析类
# ========================


class BibTeXLogParser:
    def __init__(self, root_file: str = None):
        self.build_log: List[LogEntry] = []
        self.root_file: str = root_file or ""
        self.bib_file_stack: List[str] = [self.root_file]
        self.current_result: Optional[LogEntry] = None
        self._resolved_paths = {}  # 缓存已解析的文件路径

    def parse(self, log: str, root_file: str = None) -> List[LogEntry]:
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            logger.warning(_("根文件未指定，无法继续解析日志"))
            return []

        configuration = {"exclude": []}
        exclude_regexp = configuration["exclude"]

        self.build_log.clear()
        self.reset_state()

        lines = log.split("\n")
        for line in lines:
            self.parse_line(line, exclude_regexp)

        # 如果当前结果存在且非空，则加入日志
        if self.current_result and self.current_result["text"]:
            self.build_log.append(self.current_result)

        logger.info(_("共解析 %(args)s 条日志消息" % {"args": len(self.build_log)}))
        return self.build_log

    def reset_state(self):
        """重置解析状态"""
        self.current_result = {
            "type": LogType.INFO,
            "file": "",
            "line": 1,
            "text": "",
        }

    def parse_line(self, line: str, exclude_regexp: list):
        line = line.strip("\x00")  # 去除多余空字符

        # 单行警告
        match = single_line_bibtex_warning_re.match(line)
        if match:
            key_location = self.find_key_location(match.group(2))
            if key_location:
                self.add_log_entry(
                    LogType.WARNING,
                    key_location.file,
                    key_location.line,
                    match.group(1),
                    exclude_regexp,
                )
            return

        # 多行警告
        match = multi_line_bibtex_warning_re.match(line)
        if match:
            filename = self.resolve_bib_file(match.group(3))
            self.add_log_entry(
                LogType.WARNING,
                filename,
                int(match.group(2)),
                match.group(1),
                exclude_regexp,
            )
            return

        # 多行错误
        match = multi_line_bibtex_error_re.match(line)
        if match:
            filename = self.resolve_bib_file(match.group(3))
            self.add_log_entry(
                LogType.ERROR,
                filename,
                int(match.group(2)),
                match.group(1),
                exclude_regexp,
            )
            return

        # 跨文档引用错误
        match = bad_cross_ref_bibtex_re.match(line)
        if match:
            self.add_log_entry(
                LogType.ERROR, self.root_file, 1, match.group(1), exclude_regexp
            )
            return

        # 宏定义错误
        match = multi_line_macro_bibtex_error_re.match(line)
        if match:
            filename = self.resolve_bib_file(match.group(3))
            self.add_log_entry(
                LogType.ERROR,
                filename,
                int(match.group(2)),
                match.group(1),
                exclude_regexp,
            )
            return

        # 辅助文件读取错误
        match = error_aux_file_re.match(line)
        if match:
            filename = self.resolve_aux_file(match.group(2))
            self.add_log_entry(
                LogType.ERROR, filename, 1, match.group(1), exclude_regexp
            )
            return

        # Biber 警告
        match = biber_warn_re.match(line)
        if match:
            filename = (
                self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            )
            self.add_log_entry(
                LogType.WARNING,
                filename,
                1,
                f"No bib entry found for '{match.group(1)}'",
                exclude_regexp,
            )
            return

    def resolve_bib_file(self, filename: str) -> str:
        """解析相对路径为绝对路径"""
        if not filename:
            return self.root_file

        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / filename).resolve())
        except Exception:
            resolved = filename

        self._resolved_paths[filename] = resolved
        return resolved

    def resolve_aux_file(self, filename: str) -> str:
        """解析 aux 文件对应 tex 文件"""
        filename = filename.replace(".aux", ".tex")
        # 这里应该实现更复杂的查找逻辑
        return filename

    def add_log_entry(
        self,
        log_type: LogType,
        file: str,
        line: int,
        message: str,
        exclude_patterns: list,
    ):
        """添加一条日志条目，若匹配排除规则则忽略"""
        if self._should_exclude(message, exclude_patterns):
            return

        entry = {"type": log_type, "file": file, "line": line, "text": message}
        self.build_log.append(entry)

    def _should_exclude(self, text: str, exclude_patterns: list) -> bool:
        """检查是否应该忽略该日志条目"""
        return any(pattern.search(text) for pattern in exclude_patterns)

    def show_log(self, use_logger=True):
        sorted_logs = sorted(self.build_log, key=lambda x: x["type"])
        errors = [e for e in sorted_logs if e["type"] == LogType.ERROR]
        warnings = [e for e in sorted_logs if e["type"] == LogType.WARNING]

        def format_message(e: dict):
            file_path = Path(e["file"])
            return f"{file_path.name}:{e['line']} --> {e['text']}"

        for entry in errors:
            logger.error(format_message(entry)) if use_logger else print(
                format_message(entry)
            )
        for entry in warnings:
            logger.warning(format_message(entry)) if use_logger else print(
                format_message(entry)
            )

        if not (errors or warnings):
            logger.info(_("未发现错误或警告"))

    def bibtex_logparser_cli(self, auxdir: str, project_name: str):
        """
        命令行接口：解析 BibTeX/Biber 编译日志并输出结果

        :param auxdir: 辅助文件所在目录
        :param project_name: LaTeX 项目的主文件名（不带扩展名）
        """
        # 构建日志文件路径
        log_path = Path(auxdir) / f"{project_name}.blg"

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
        except FileNotFoundError:
            logger.error(_("找不到日志文件: %(args)s") % {"args": str(log_path)})
            return

        self.root_file = project_name + ".tex"
        log_entries = self.parse(log_content)
        self.show_log(use_logger=True)


# ========================
# Biber 日志解析类
# ========================

# Biber 相关正则表达式
biber_info_re = re.compile(r"^INFO - Found BibTeX data source \'(.*)\'$")
biber_error_re = re.compile(r"^ERROR - BibTeX subsystem.*, line (\d+), (.*)$")
biber_missing_entry_re = re.compile(
    r"^WARN - (I didn\'t find a database entry for \'.*?\'.*)$"
)
biber_line_warning_re = re.compile(r"^WARN - (.*? entry `(.+?)\' .*)$")


# TODO 添加一种触发机制，当检测到参考文献相关错误时启动key的检索功能，用来确定位置
class BiberLogParser(BibTeXLogParser):
    def __init__(self, root_file: str = None):
        super().__init__(root_file)
        self.build_log: List[LogEntry] = []
        self.root_file: str = root_file or ""
        self.bib_file_stack: List[str] = [self.root_file]
        self._resolved_paths = {}  # 缓存已解析的文件路径

    def parse(self, log: str, root_file: str = None) -> List[LogEntry]:
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            logger.warning(_("根文件未指定，无法继续解析日志"))
            return []

        configuration = {"exclude": []}
        exclude_regexp = configuration["exclude"]

        self.build_log.clear()
        self.reset_state()

        lines = log.split("\n")
        for line in lines:
            self.parse_line(line, exclude_regexp)

        # 如果当前结果存在且非空，则加入日志
        if self.current_result and self.current_result["text"]:
            self.build_log.append(self.current_result)

        logger.info(_("共解析 %(args)s 条日志消息" % {"args": len(self.build_log)}))
        return self.build_log

    def reset_state(self):
        """重置解析状态"""
        self.current_result = {
            "type": LogType.INFO,
            "file": "",
            "line": 1,
            "text": "",
        }

    def parse_line(self, line: str, exclude_regexp: list):
        line = line.strip("\x00")  # 去除多余空字符

        # 解析 BibTeX 数据源
        info_match = biber_info_re.match(line)
        if info_match:
            filename = info_match.group(1)
            resolved_file = self.resolve_bib_file(filename, self.root_file)
            self.bib_file_stack.append(resolved_file)
            logger.debug(f"找到 BibTeX 文件 {resolved_file}")
            return

        # 解析错误
        error_match = biber_error_re.match(line)
        if error_match:
            line_number = int(error_match.group(1))
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.add_log_entry(
                LogType.ERROR, file, line_number, error_match.group(2), exclude_regexp
            )
            return

        # 解析缺失条目警告
        missing_match = biber_missing_entry_re.match(line)
        if missing_match:
            file = self.bib_file_stack[-1] if self.bib_file_stack else self.root_file
            self.add_log_entry(
                LogType.WARNING, file, 1, missing_match.group(1), exclude_regexp
            )
            return

        # 解析其他警告
        warning_match = biber_line_warning_re.match(line)
        if warning_match:
            key = warning_match.group(2)
            location = self.find_key_location(key)
            if location:
                self.add_log_entry(
                    LogType.WARNING,
                    location["file"],
                    location["line"],
                    warning_match.group(1),
                    exclude_regexp,
                )
            return

    def resolve_bib_file(self, filename: str, root_file: str) -> str:
        """解析相对路径为绝对路径"""
        if not filename:
            return self.root_file

        if filename in self._resolved_paths:
            return self._resolved_paths[filename]

        root_dir = Path(root_file).parent
        try:
            resolved = str((root_dir / filename).resolve())
        except Exception:
            resolved = filename

        self._resolved_paths[filename] = resolved
        return resolved

    def load_citation_cache(self, auxdir):
        """从缓存文件加载引用位置信息"""
        cache_file = Path(auxdir) / "citation_cache.aux"
        if not cache_file.exists():
            return
        with open(cache_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(":", 1)
                if len(parts) == 2:
                    key, location = parts
                    self.citation_cache[key] = location

    def find_key_location(self, key: str) -> Optional[Dict[str, Union[str, int]]]:
        """从缓存中查找引用键的位置"""
        location = self.citation_cache.get(key)
        if location:
            try:
                file_part, line_part = location.rsplit(" line ", 1)
                return {"file": file_part, "line": int(line_part)}
            except ValueError:
                pass
        return None


class CitationCacheManager:
    def __init__(self, project_name: str, auxdir: Union[str, Path]):
        self.main_file_path = Path(f"{project_name}.tex")
        self.auxdir = Path(auxdir)
        self.cache_file = self.auxdir / f"{project_name}.citecache"  # 新的缓存文件后缀
        self.citation_cache = {}

        # 编译正则表达式
        self.input_re = re.compile(r"\\(?:input|include)\{(.+?)\}")
        self.citation_command_re = re.compile(
            r"\\(?:cite|upcite|citet|citep|parencite|textcite|footcite|smartcite|autocite)\{([^}]+)\}",
            re.IGNORECASE,
        )

    def build_cache(self):
        """构建引用缓存并写入 TOML 文件"""
        self.auxdir.mkdir(exist_ok=True)
        self.citation_cache.clear()

        self._parse_tex_file(self.main_file_path, self.citation_cache)

        # 构建 TOML 数据
        toml_data = {
            key: {"file": info["file"], "line": info["line"]}
            for key, info in self.citation_cache.items()
        }

        with open(self.cache_file, "w", encoding="utf-8") as f:
            toml.dump(toml_data, f)
        logger.info(_("引用缓存已生成：%(args)s") % {"args": str(self.cache_file)})

    def _parse_tex_file(self, file_path: Path, citation_cache: dict):
        """
        解析 TeX 文件中的引用命令和子文件。
        支持多 key 引用（如 cite{key1,key2}）和递归解析子文件。
        """
        # 使用当前文件的父目录作为基准目录
        root_dir = file_path.parent
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning(
                _("无法读取文件 %(args)s: %(error)s")
                % {"args": str(file_path), "error": str(e)}
            )
            return

        for i, line in enumerate(lines):
            # 查找所有引用命令
            cites = self.citation_command_re.findall(line)
            for key in cites:
                keys = [k.strip() for k in key.split(",")]
                for k in keys:
                    if k:
                        relative_path = file_path.relative_to(root_dir)
                        citation_cache[k] = {"file": str(relative_path), "line": i + 1}

            # 查找子文件
            match = self.input_re.search(line)
            if match:
                sub_file_name = match.group(1)
                if not sub_file_name.endswith(".tex"):
                    sub_file_name += ".tex"
                sub_file_path = file_path.parent / sub_file_name
                if sub_file_path.exists():
                    self._parse_tex_file(sub_file_path, citation_cache, root_dir)

    def load_cache(self):
        """从 TOML 文件加载引用缓存"""
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                toml_data = toml.load(f)
            self.citation_cache = {
                key: f"{value['file']} line {value['line']}"
                for key, value in toml_data.items()
            }
            logger.info(_("引用缓存已加载：%(args)s") % {"args": str(self.cache_file)})
            return True
        except Exception as e:
            logger.error(_("加载缓存失败：%(args)s") % {"args": str(e)})
            return False

    def get_location(self, key: str) -> Optional[Dict[str, Union[str, int]]]:
        """查找指定 key 的引用位置"""
        location = self.citation_cache.get(key)
        if location:
            try:
                file_part, line_part = location.rsplit(" line ", 1)
                return {"file": file_part, "line": int(line_part)}
            except ValueError:
                pass
        return None


if __name__ == "__main__":
    ccm = CitationCacheManager("biblatex-test", "Auxiliary")
    ccm.build_cache()
    ccm.load_cache()
    print(ccm.get_location("knuth1986texbook"))
