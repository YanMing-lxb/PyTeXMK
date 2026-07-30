"""LaTeX 引擎 .log 日志解析器实现。"""
from __future__ import annotations

"""LaTeX 引擎 .log 日志解析器实现。"""
import re
from pathlib import Path
from typing import Any

from .base import BaseLogParser, LogEntry, LogLevel, ParsedLog

__all__ = [
    "LatexLogParser",
    "LATEX_LOG_HINTS",
    "bib_empty_re",
    "biber_warn_re",
    "class_warning_info_re",
    "file_stack_close_re",
    "file_stack_open_re",
    "font_warning_re",
    "hyphenation_warning_re",
    "latex_error_re1",
    "latex_error_re2",
    "latex_warn_re",
    "makeindex_warning_re",
    "marginpar_warning_re",
    "message_line_re",
    "missing_char_re",
    "nag_package_sense_re",
    "overfull_box_alt_re",
    "overfull_box_output_re",
    "overfull_box_re",
    "package_warning_extra_lines_re",
    "package_warning_info_re",
    "pages_output_re",
    "rerun_get_cross_references_re",
    "rerun_to_get_citations_re",
    "undefined_label_multi_re",
    "undefined_reference_re",
    "underfull_box_alt_re",
    "underfull_box_output_re",
    "underfull_box_re",
]


LATEX_LOG_HINTS: dict[str, str] = {
    "Undefined control sequence":
        "检查 \\ 命令名拼写，或确认是否已 \\usepackage 对应宏包。",
    "Undefined reference":
        "LaTeX 标签尚未被记录：通常需要再编译一到两次（或检查 \\label / \\ref 名）。",
    "Undefined citation":
        "参考文献键未找到：检查 .bib 文件中的 @xxx{key, 是否与 \\cite{key} 一致，并确认已跑过 bibtex/biber。",
    "Overfull \\\\hbox":
        "行/盒子过宽超过页面边距：手动断行、放宽 \\sloppy、或调整图文尺寸。",
    "Underfull \\\\hbox":
        "行/盒子文字不足导致间距拉伸：可接受，或在相应段落补充内容/使用 \\\\linebreak。",
    "Missing character":
        "当前字体不含该字形：更换支持该字符的字体，或用 \\usepackage[T1]{fontenc} 等。",
    "Rerun to get cross-references right":
        "提示再跑一轮 pdflatex：跨引用页码/链接在 .aux 中更新后需要二次编译。",
    "Rerun to get citations correct":
        "提示先跑 bibtex/biber，再跑 pdflatex 一到两次以同步参考文献引用。",
}

latex_error_re1 = re.compile(r"^(?:(.*):(\d+):|!)(?: (.+) Error:)? (.+?)$")
latex_error_re2 = re.compile(r"^!(?: (.+) Error:)? (.+?)$")

overfull_box_re = re.compile(
    r"^(Overfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$"
)
overfull_box_alt_re = re.compile(
    r"^(Overfull \\[vh]box \([^)]+\)) detected at line (\d+)$"
)
overfull_box_output_re = re.compile(
    r"^(Overfull \\[vh]box \([^)]+\)) has occurred while \\output is active(?: \((\d+)\))?$"
)

underfull_box_re = re.compile(
    r"^(Underfull \\[vh]box \([^)]+\)) in paragraph at lines (\d+)--(\d+)$"
)
underfull_box_alt_re = re.compile(
    r"^(Underfull \\[vh]box \([^)]+\)) detected at line (\d+)$"
)
underfull_box_output_re = re.compile(
    r"^(Underfull \\[vh]box \([^)]+\)) has occurred while \\output is active(?: \((\d+)\))?$"
)

latex_warn_re = re.compile(
    r"^((?:(?:Class|Package|Module) \S+)|LaTeX(?: \S*)?|LaTeX3) (Warning|Info):\s+(.*?)(?: on(?: input)? line (\d+))?(\.|\?)?$"
)

package_warning_extra_lines_re = re.compile(
    r"^\(.\)([a-zA-Z]+)\s+(.+?)(?: +on input line (\d+))?$"
)

missing_char_re = re.compile(r"^\s*(Missing character:.+?[?!])$")

bib_empty_re = re.compile(r"^Empty `thebibliography' environment$")

biber_warn_re = re.compile(
    r"^Biber warning:.*WARN - I didn't find a database entry for '([^']+)'$"
)

undefined_reference_re = re.compile(
    r"^LaTeX Warning: (Reference|Citation) `(.*?)' on page \d+ undefined on input line (\d+)\.$"
)

message_line_re = re.compile(r"^l\.\d+\s(...)?(.*)$")

# 仅在 ( 前是行首/空白 且紧随内容含路径分隔符(//\)或 LaTeX 扩展名时才入文件栈（避免匹配 Overfull \hbox (...) 等括号）
_LATEX_EXT = r"tex|sty|cls|aux|fd|cfg|def|ldf|clo|bbl|blg|idx|ind|gls|glo|acr|nls|nlo|toc|lof|lot|out|log|ist|alg|slg|dvi|pdf|ps|eps"
file_stack_open_re = re.compile(
    rf"(?<![^\s])\((\S*(?:[\\/]\S*|\.(?:{_LATEX_EXT})\b))"
)
file_stack_close_re = re.compile(r"\)")

pages_output_re = re.compile(r"Output written on .*\((\d+) page")

class_warning_info_re = re.compile(
    r"^Class (\S+) Warning:\s+(.*?)(?: +on input line (\d+))?\.?$"
)
package_warning_info_re = re.compile(
    r"^Package (\S+) Warning:\s+(.*?)(?: +on input line (\d+))?\.?$"
)
font_warning_re = re.compile(
    r"^LaTeX Font Warning:\s+(.*?)(?: +on input line (\d+))?\.?$"
)
nag_package_sense_re = re.compile(
    r"^Package nag Warning:\s+(.*?)(?: +on input line (\d+))?\.?$"
)
marginpar_warning_re = re.compile(
    r"^LaTeX Warning:\s+Marginpar on page \w+ moved\.?$"
)
hyphenation_warning_re = re.compile(
    r"^Underfull \\hbox \(badness (\d+)\) has occurred while \\hyphenation is active"
)
makeindex_warning_re = re.compile(r"^## Warning \(input\) = (.+)$")
undefined_label_multi_re = re.compile(
    r"^LaTeX Warning: (?:There were (?P<n>\d+) undefined references\.?|There were multiply-defined labels\.?)$"
)
rerun_get_cross_references_re = re.compile(
    r"^LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\.?$"
)
rerun_to_get_citations_re = re.compile(
    r"^(?:Package (\S+) Warning: Please \(re\)run Biber to get citations right\.?|LaTeX Warning: Citation\(s\) may have changed\. Rerun to get citations correct\.?)$"
)


class _TempEntry(dict):
    pass


class LatexLogParser(BaseLogParser):
    """LaTeX .log 日志解析器（兼容旧 API）。"""
    def __init__(self, root_file: str | None = None, quiet: bool = False) -> None:
        """初始化 LatexLogParser（新）：调用父类并设置 latex 默认工具元数据。"""
        super().__init__(root_file)
        self.quiet = quiet
        self.build_log: list[LogEntry] = []
        self.current_result: _TempEntry | None = None
        self.file_stack: list[str] = []
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0
        self._resolved_paths: dict[str, str] = {}
        self._undefined_refs = 0
        self._undefined_cites = 0
        self._overfull_boxes = 0
        self._underfull_boxes = 0

    def parse_lines(self, lines: list[str], root_file: str | None = None) -> ParsedLog:
        """兼容旧 API：接收行列表，委托给 parse。"""
        return self.parse("\n".join(lines), root_file=root_file)

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 LaTeX .log 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.file_stack = []
        self.build_log.clear()
        self._resolved_paths.clear()
        self._undefined_refs = 0
        self._undefined_cites = 0
        self._overfull_boxes = 0
        self._underfull_boxes = 0
        self._reset_state()

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        if self.current_result and not re.match(
            bib_empty_re, str(self.current_result.get("text", ""))
        ):
            self._flush_current()

        pages_output = 0
        m = pages_output_re.search(log_text)
        if m:
            pages_output = int(m.group(1))

        stats: dict[str, Any] = {
            "errors_count": sum(1 for e in self.build_log if e.level == LogLevel.ERROR),
            "warnings_count": sum(1 for e in self.build_log if e.level == LogLevel.WARNING),
            "undefined_refs": self._undefined_refs,
            "undefined_cites": self._undefined_cites,
            "overfull_boxes": self._overfull_boxes,
            "underfull_boxes": self._underfull_boxes,
            "pages_output": pages_output,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="latex",
            category="compile",
            importance="high",
            stats=stats,
        )

    def _reset_state(self) -> None:
        self.current_result = _TempEntry(
            type=None,
            file="",
            line=1,
            text="",
            error_pos_text="",
        )
        self.search_empty_line = False
        self.inside_box_warn = False
        self.inside_error = False
        self.nested = 0

    def _flush_current(self) -> None:
        if self.current_result is None:
            return
        t = self.current_result.get("type")
        if t is None:
            return
        entry = LogEntry(
            level=t,
            file=str(self.current_result.get("file", "")),
            line=int(self.current_result.get("line", 1) or 1),
            text=str(self.current_result.get("text", "")),
            error_pos_text=str(self.current_result.get("error_pos_text", "")),
        )
        self.build_log.append(entry)

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00\r")

        if self.search_empty_line:
            if not line or (self.inside_error and line.startswith(" ")):
                self.current_result["text"] = str(self.current_result.get("text", "")) + "\n" + line
                self.search_empty_line = False
                self.inside_error = False
                return
            is_new_entry_start = False
            for pat in [
                latex_error_re1, latex_error_re2, undefined_reference_re,
                latex_warn_re, missing_char_re,
                class_warning_info_re, package_warning_info_re,
                font_warning_re, nag_package_sense_re,
                marginpar_warning_re, hyphenation_warning_re,
                makeindex_warning_re, undefined_label_multi_re,
                rerun_get_cross_references_re, rerun_to_get_citations_re,
            ]:
                if pat.match(line):
                    is_new_entry_start = True
                    break
            if not is_new_entry_start and overfull_box_re.match(line) is None \
                    and overfull_box_alt_re.match(line) is None \
                    and overfull_box_output_re.match(line) is None \
                    and underfull_box_re.match(line) is None \
                    and underfull_box_alt_re.match(line) is None \
                    and underfull_box_output_re.match(line) is None:
                package_match = package_warning_extra_lines_re.match(line)
                if package_match:
                    self.current_result["text"] = (
                        str(self.current_result.get("text", ""))
                        + f"\n({package_match.group(1)})\t{package_match.group(2)}"
                    )
                    if package_match.group(3):
                        self.current_result["line"] = int(package_match.group(3))
                else:
                    self.current_result["text"] = str(self.current_result.get("text", "")) + "\n" + line
                self.search_empty_line = False
                return
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.search_empty_line = False
            self.inside_error = False

        error_match = None
        for pattern in [latex_error_re1, latex_error_re2]:
            error_match = pattern.match(line)
            if error_match:
                break
        if error_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            file = error_match.group(1) or self._get_current_file()
            line_num = int(error_match.group(2)) if error_match.group(2) else 1
            msg = (error_match.group(3) or "") + ": " + (error_match.group(4) or "")
            self.current_result = _TempEntry(
                type=LogLevel.ERROR,
                file=file,
                line=line_num,
                text=msg,
                error_pos_text="",
            )
            self.search_empty_line = True
            self.inside_error = True
            return

        undef_match = undefined_reference_re.match(line)
        if undef_match:
            ref_type, label, line_num = undef_match.groups()
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            if ref_type == "Reference":
                self._undefined_refs += 1
            else:
                self._undefined_cites += 1
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num),
                text=f"找不到 {ref_type.lower()} `{label}`",
                error_pos_text=label,
            )
            self.search_empty_line = False
            return

        warn_match = latex_warn_re.match(line)
        if warn_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            category = warn_match.group(1)
            level = warn_match.group(2)
            message = warn_match.group(3) or ""
            line_num = warn_match.group(4)
            suffix = warn_match.group(5) or ""
            full_message = (
                f"{category} {level}: {message}{('.' + suffix) if suffix else ''}"
            )
            log_type = LogLevel.WARNING if level == "Warning" else LogLevel.INFO
            self.current_result = _TempEntry(
                type=log_type,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=full_message,
                error_pos_text="",
            )
            self.search_empty_line = True
            return

        if self._parse_bad_box(line):
            return

        miss_match = missing_char_re.match(line)
        if miss_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=miss_match.group(1),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        if self.inside_error:
            match = message_line_re.match(line)
            if match:
                sub_line = match.group(2) or ""
                self.current_result["error_pos_text"] = sub_line
                self.search_empty_line = False
                self.inside_error = False
                return

        extra_match = None

        extra_match = class_warning_info_re.match(line)
        if extra_match:
            cls_name, msg, line_num = extra_match.groups()
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=f"Class {cls_name} Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = package_warning_info_re.match(line)
        if extra_match:
            pkg_name, msg, line_num = extra_match.groups()
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=f"Package {pkg_name} Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = font_warning_re.match(line)
        if extra_match:
            msg, line_num = extra_match.groups()
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=f"LaTeX Font Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = nag_package_sense_re.match(line)
        if extra_match:
            msg, line_num = extra_match.groups()
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=int(line_num) if line_num else 1,
                text=f"Package nag Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = marginpar_warning_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=extra_match.group(0),
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = hyphenation_warning_re.match(line)
        if extra_match:
            badness = extra_match.group(1)
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"Underfull \\hbox (badness {badness}) has occurred while \\hyphenation is active",
                error_pos_text="",
            )
            self.search_empty_line = False
            self._underfull_boxes += 1
            return

        extra_match = makeindex_warning_re.match(line)
        if extra_match:
            msg = extra_match.group(1)
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"MakeIndex Warning: {msg}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = undefined_label_multi_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            n = extra_match.group("n")
            if n:
                text = f"There were {n} undefined references."
            else:
                text = "There were multiply-defined labels."
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=f"LaTeX Warning: {text}",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = rerun_get_cross_references_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text="LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.",
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        extra_match = rerun_to_get_citations_re.match(line)
        if extra_match:
            if self.current_result and self.current_result.get("type") is not None:
                self._flush_current()
            pkg = extra_match.group(1)
            if pkg:
                text = f"Package {pkg} Warning: Please (re)run Biber to get citations right."
            else:
                text = "LaTeX Warning: Citation(s) may have changed. Rerun to get citations correct."
            self.current_result = _TempEntry(
                type=LogLevel.WARNING,
                file=self._get_current_file(),
                line=1,
                text=text,
                error_pos_text="",
            )
            self.search_empty_line = False
            return

        self._parse_file_stack(line)

    def _parse_bad_box(self, line: str) -> bool:
        bad_box_patterns = [
            (overfull_box_re, True, False),
            (overfull_box_alt_re, True, False),
            (overfull_box_output_re, True, True),
            (underfull_box_re, False, False),
            (underfull_box_alt_re, False, False),
            (underfull_box_output_re, False, True),
        ]
        for pattern, is_overfull, is_output in bad_box_patterns:
            match = pattern.match(line)
            if match:
                if self.current_result and self.current_result.get("type") is not None:
                    self._flush_current()
                file = self._get_current_file()
                text = match.group(1)
                line_num = int(match.group(2)) if match.group(2) else 1
                if is_overfull:
                    self._overfull_boxes += 1
                else:
                    self._underfull_boxes += 1
                self.current_result = _TempEntry(
                    type=LogLevel.TYPESET,
                    file=file,
                    line=line_num,
                    text=text,
                    error_pos_text="",
                )
                self.inside_box_warn = True
                self.search_empty_line = False
                return True
        return False

    def _parse_file_stack(self, line: str) -> None:
        # 逐字符扫描：'(' 时尝试匹配 TeX 路径，命中则入栈；')' 时出栈
        # 避免同一条消息中的括号 (如 Overfull \hbox (15.0pt ...)) 被当作文件栈操作
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch == "(":
                # 要求 ( 前是空白 / 行首，且紧随 TeX 路径样式
                if i == 0 or line[i - 1].isspace():
                    m = file_stack_open_re.match(line, i)
                    if m:
                        path_part = m.group(1).strip()
                        if path_part:
                            self.file_stack.append(path_part)
                        else:
                            self.nested += 1
                        i = m.end()
                        continue
                i += 1
            elif ch == ")":
                if self.nested > 0:
                    self.nested -= 1
                elif self.file_stack:
                    self.file_stack.pop()
                i += 1
            else:
                i += 1

    def _get_current_file(self) -> str:
        current_path = self.file_stack[-1] if self.file_stack else self.root_file
        if current_path in self._resolved_paths:
            return self._resolved_paths[current_path]

        root_dir = Path(self.root_file).parent
        try:
            resolved = str((root_dir / current_path).resolve())
        except Exception:  # noqa: BLE001
            resolved = current_path

        self._resolved_paths[current_path] = resolved
        return resolved
