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

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from enum import Enum

from pytexmk.language import set_language

logger = logging.getLogger(__name__)
_ = set_language('log_parser')

# ========================
# 日志类型枚举
# ========================

class LogType(Enum):
    ERROR = 'error'
    WARNING = 'warning'
    TYPESET = 'typesetting'
    INFO = 'info'
    FONT = 'font'
    GRAPHIC = 'graphic'
    PAGE = 'page'

    def __lt__(self, other):
        """支持按优先级排序"""
        order = {
            LogType.ERROR: 0,
            LogType.WARNING: 1,
            LogType.TYPESET: 2,
            LogType.FONT: 3,
            LogType.GRAPHIC: 4,
            LogType.PAGE: 5,
            LogType.INFO: 6
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
latex_error_re1 = re.compile(r'^(?:(.*):(\d+):|!)(?: (.+) Error:)? (.+?)$')
latex_error_re2 = re.compile(r'^!(?: (.+) Error:)? (.+?)$')

# 排版警告（Bad Boxes）
overfull_box_re = re.compile(r'^(Overfull \$[vh]box $[^)]+\$) in paragraph at lines (\d+)--(\d+)$')
overfull_box_alt_re = re.compile(r'^(Overfull \$[vh]box $[^)]+\$) detected at line (\d+)$')
overfull_box_output_re = re.compile(r'^(Overfull \$[vh]box $[^)]+\$) has occurred while \\output is active(?: \$(\d+)\$)?$')

underfull_box_re = re.compile(r'^(Underfull \$[vh]box $[^)]+\$) in paragraph at lines (\d+)--(\d+)$')
underfull_box_alt_re = re.compile(r'^(Underfull \$[vh]box $[^)]+\$) detected at line (\d+)$')
underfull_box_output_re = re.compile(r'^(Underfull \$[vh]box $[^)]+\$) has occurred while \\output is active(?: \$(\d+)\$)?$')

# 警告信息
latex_warn_re = re.compile(
    r'^((?:(?:Class|Package|Module) \S)|LaTeX(?: \S*)?|LaTeX3) (Warning|Info):\s+(.*?)(?: on(?: input)? line (\d+))?(\.|\?)?$'
)

# 包警告后续行
package_warning_extra_lines_re = re.compile(r'^$\.$([a-zA-Z]+)\s+(.+?)(?: +on input line (\d+))?$')

# 缺失字符
missing_char_re = re.compile(r'^\s(Missing character:.+?!)$')

# 空参考文献
bib_empty_re = re.compile(r'^Empty `thebibliography\' environment$')

# Biber 警告
biber_warn_re = re.compile(r'^Biber warning:.*WARN - I didn\'t find a database entry for \'([^\']+)\'$')

# 未定义引用
undefined_reference_re = re.compile(
    r'^LaTeX Warning: (Reference|Citation) `(.*?)\' on page \d+ undefined on input line (\d+)\.$'
)

# 消息行（带代码位置）
message_line_re = re.compile(r'^l\.\d+\s(...)?(.*)$')

# 文件栈开始与结束
file_stack_open_re = re.compile(r'$([^$]*)')
file_stack_close_re = re.compile(r'$')


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

        lines = log.split('\n')
        for line in lines:
            self.parse_line(line)

        # 最后一条日志入栈
        if self.current_result and not re.match(bib_empty_re, self.current_result['text']):
            self.build_log.append(self.current_result)

        logger.info(_("共解析 %(args)s 条日志消息" % {"args": len(self.build_log)}))
        return self.build_log

    def reset_state(self):
        self.current_result = {
            "type": "",
            "file": "",
            "line": 1,
            "text": "",
            "error_pos_text": ""
        }
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0

    def parse_line(self, line: str):
        line = line.strip('\x00')  # 去除多余空字符

        # 忽略空行
        if self.search_empty_line:
            if not line or (self.inside_error and line.startswith(' ')):
                self.current_result['text'] += '\n' + line
                self.search_empty_line = False
                self.inside_error = False
                return
            else:
                package_match = package_warning_extra_lines_re.match(line)
                if package_match:
                    self.current_result['text'] += f'\n({package_match.group(1)})\t{package_match.group(2)}'
                    self.current_result['line'] = int(package_match.group(3)) if package_match.group(3) else 1
                else:
                    self.current_result['text'] += '\n' + line
                self.search_empty_line = False
                return

        # 解析错误
        error_match = None
        for pattern in [latex_error_re1, latex_error_re2]:
            error_match = pattern.match(line)
            if error_match:
                break
        if error_match:
            if self.current_result and self.current_result['type']:
                self.build_log.append(self.current_result)
            file = error_match.group(1) or self.get_current_file()
            line_num = int(error_match.group(2)) if error_match.group(2) else 1
            msg = (error_match.group(3) or '') + ': ' + (error_match.group(4) or '')
            self.current_result = {
                "type": LogType.ERROR,
                "file": file,
                "line": line_num,
                "text": msg,
                "error_pos_text": ""
            }
            self.search_empty_line = True
            self.inside_error = True
            return

        # 解析警告
        warn_match = latex_warn_re.match(line)
        if warn_match:
            if self.current_result and self.current_result['type']:
                self.build_log.append(self.current_result)
            category = warn_match.group(1)
            level = warn_match.group(2)
            message = warn_match.group(3) or ''
            line_num = warn_match.group(4)
            suffix = warn_match.group(5) or ''
            full_message = f"{category} {level}: {message}{('.' + suffix) if suffix else ''}"

            log_type = LogType.WARNING if level == "Warning" else LogType.INFO

            self.current_result = {
                "type": log_type,
                "file": self.get_current_file(),
                "line": int(line_num) if line_num else 1,
                "text": full_message
            }
            self.search_empty_line = True
            return

        # 解析未定义引用
        if undefined_reference_re.match(line):
            match = undefined_reference_re.match(line)
            if match:
                ref_type, label, line_num = match.groups()
                if self.current_result and self.current_result['type']:
                    self.build_log.append(self.current_result)
                self.current_result = {
                    "type": LogType.WARNING,
                    "file": self.get_current_file(),
                    "line": int(line_num),
                    "text": f"找不到 {ref_type.lower()} `{label}`",
                    "error_pos_text": label
                }
                self.search_empty_line = False
                return

        # 解析 Bad Box
        if self.parse_bad_box(line):
            return

        # 解析缺失字符
        miss_match = missing_char_re.match(line)
        if miss_match:
            if self.current_result and self.current_result['type']:
                self.build_log.append(self.current_result)
            self.current_result = {
                "type": LogType.WARNING,
                "file": self.get_current_file(),
                "line": 1,
                "text": miss_match.group(1)
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
            overfull_box_re, overfull_box_alt_re, overfull_box_output_re,
            underfull_box_re, underfull_box_alt_re, underfull_box_output_re
        ]
        for pattern in bad_box_patterns:
            match = pattern.match(line)
            if match:
                if self.current_result and self.current_result['type']:
                    self.build_log.append(self.current_result)
                file = self.get_current_file()
                text = match.group(1)
                line_num = int(match.group(2)) if match.groups() >= 3 and match.group(2) else 1
                self.current_result = {
                    "type": LogType.TYPESET,
                    "file": file,
                    "line": line_num,
                    "text": text
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
        errors = [entry for entry in sorted_logs if entry['type'] == LogType.ERROR]
        warnings = [entry for entry in sorted_logs if entry['type'] == LogType.WARNING]
        typesets = [entry for entry in sorted_logs if entry['type'] == LogType.TYPESET]
        fonts = [entry for entry in sorted_logs if entry['type'] == LogType.FONT]
        graphics = [entry for entry in sorted_logs if entry['type'] == LogType.GRAPHIC]
        pages = [entry for entry in sorted_logs if entry['type'] == LogType.PAGE]
        infos = [entry for entry in sorted_logs if entry['type'] == LogType.INFO]

        def format_message(entry: Dict[str, Any]) -> str:
            file_path = Path(entry['file'])
            try:
                rel_path = file_path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                rel_path = file_path.name  # 只显示文件名
            level = entry['type'].value.upper()
            text = entry['text']
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

        if not (errors or warnings or typesets or fonts or graphics or pages or (show_info and infos)):
            success_msg = _("未发现错误或警告")
            logger.info(success_msg) if use_logger else print(success_msg)

    def show_editor_jump_format(self):
        for entry in sorted(self.build_log, key=lambda x: x["type"]):
            file_path = Path(entry['file']).name
            msg = f"{file_path}:{entry['line']}: {entry['text']}"
            logger.info(msg)
    
    def logparser_cli(self, auxdir, project_name):
        # 构建日志文件路径
        log_path = Path(auxdir) / f"{project_name}.log"
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        self.root_file = project_name + ".tex"
        log_entries = self.parse(log_content)
        self.show_log(use_logger=True, show_info=True)
        
        # 可选：显示编辑器可识别的跳转格式
        # self.show_editor_jump_format()
        # print(log_entries)
