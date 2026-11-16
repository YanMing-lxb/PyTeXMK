"""编译前静态检查（preflight，3.2）。

目标不是做完整 TeX 语法分析，而是把**每次都会让编译白跑一轮**的低级错误
提前拦下来：

* 主文件不是 UTF-8 / 带 BOM；
* 缺少 ``\\documentclass`` 或 ``\\end{document}``；
* ``\\bibliography{...}`` 指向的 .bib 不存在；
* ``\\input``/``\\include`` 指向的文件不存在；
* ``\\includegraphics`` 指向的图片不存在（含常见扩展名推断）。

检查结果分 ``error``（阻止编译）与 ``warning``（仅提示）。所有路径问题都按
**被检查文件所在目录**解析，而不是笼统的 cwd。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("preflight")

_BIB_RE = re.compile(r"\\bibliography\{([^}]*)\}")
_ADD_BIB_RE = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]*)\}")
# 必须要求命令名后不是字母：否则 ``\inputsection{...}`` 会被当成 ``\input section``，
# 把自定义命令的参数误报成缺失文件。
_INPUT_RE = re.compile(r"\\(?:input|include)(?![A-Za-z])\s*(?:\{([^}]*)\}|([^\s{}%]+))")
_GRAPHIC_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}")
_GRAPHICS_PATH_RE = re.compile(r"\\graphicspath\s*\{((?:\{[^{}]*\})+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")

# 宏定义命令：这些命令的参数体是“模板”，里面的 \input 不能按字面路径检查。
_DEF_COMMAND_RE = re.compile(
    r"\\(?:"
    r"newcommand|renewcommand|providecommand|DeclareRobustCommand|"
    r"newenvironment|renewenvironment|"
    r"def|edef|gdef|xdef"
    r")(?![A-Za-z])"
)
_DEF_NEWCOMMAND_RE = re.compile(r"\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand)")
_DEF_ENV_RE = re.compile(r"\\(?:newenvironment|renewenvironment)")

GRAPHIC_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".PDF", ".PNG", ".JPG")


def _matching_brace(text: str, open_index: int) -> int:
    """返回与 ``{`` 匹配的 ``}`` 下标；找不到返回 -1。"""
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2  # 跳过转义字符/控制序列的第一个字符
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _brace_groups_after(text: str, start: int, limit: int) -> list[tuple[int, int]]:
    """收集命令之后的花括号组，最多 ``limit`` 个。"""
    groups: list[tuple[int, int]] = []
    index = start
    while index < len(text) and len(groups) < limit:
        char = text[index]
        if char == "{":
            end = _matching_brace(text, index)
            if end < 0:
                break
            groups.append((index, end + 1))
            index = end + 1
            continue
        if char == "[":
            end = text.find("]", index + 1)
            index = len(text) if end < 0 else end + 1
            continue
        index += 1
    return groups


def _mask_macro_definitions(text: str) -> str:
    """把宏定义体替换成空格，避免把模板里的 ``\\input`` 当真实输入。

    TeX 的宏展开在静态检查阶段不可判定；例如
    ``\\newcommand{\\foo}{\\input{section}}`` 只有在 ``\\foo`` 被调用时
    才需要检查 ``section.tex``。这里只屏蔽定义体，不屏蔽顶层调用。
    """
    chars = list(text)
    cursor = 0
    for match in _DEF_COMMAND_RE.finditer(text):
        if match.start() < cursor:
            continue
        command = match.group(0)
        if _DEF_ENV_RE.match(command):
            limit = 3  # name + begin + end
        elif _DEF_NEWCOMMAND_RE.match(command):
            # \newcommand{\foo}{...} 或 \newcommand\foo{...}
            first = _brace_groups_after(text, match.end(), 1)
            if not first:
                continue
            prefix = text[match.end() : first[0][0]]
            limit = 1 if "\\" in prefix else 2
        else:
            limit = 1  # \def\foo#1{...}
        groups = _brace_groups_after(text, match.end(), limit)
        if not groups:
            continue
        end = groups[-1][1]
        for index in range(match.start(), end):
            if chars[index] not in "\r\n":
                chars[index] = " "
        cursor = end
    return "".join(chars)


@dataclass
class Issue:
    """一条 preflight 问题。"""

    severity: str  # error | warning
    file: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.file}: {self.message}"


@dataclass
class PreflightReport:
    """preflight 汇总。"""

    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_dynamic_path(name: str) -> bool:
    """路径含宏参数 ``#1`` 或宏调用 ``\\langdir`` 时，静态检查无法求值。"""
    return "#" in name or "\\" in name


def _clean(text: str) -> str:
    return "\n".join(_COMMENT_RE.sub("", line) for line in text.splitlines())


def _read(path: Path, report: PreflightReport) -> str | None:
    """读取并检查编码；返回 None 表示这个文件不该继续检查。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        report.issues.append(Issue("error", path.name, f"无法读取: {exc}"))
        return None
    if raw.startswith(b"\xef\xbb\xbf"):
        report.issues.append(Issue("warning", path.name, "文件带 UTF-8 BOM，部分宏包会把它当正文"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        report.issues.append(
            Issue("error", path.name, f"不是有效 UTF-8（字节 {exc.start} 处）；请另存为 UTF-8")
        )
        return None
    return text


def _resolve(base: Path, name: str) -> Path:
    name = name.strip()
    if not name.lower().endswith(".tex"):
        name += ".tex"
    return (base / name).resolve()


def check_project(project_name: str, root: str | Path = ".") -> PreflightReport:
    """对主文件做一次 preflight；递归检查一层 ``\\input``。"""
    root = Path(root)
    report = PreflightReport()
    main = root / f"{project_name}.tex"
    if not main.exists():
        report.issues.append(Issue("error", main.name, "主文件不存在"))
        return report

    text = _read(main, report)
    if text is None:
        return report

    cleaned = _clean(text)
    cleaned = _mask_macro_definitions(cleaned)
    if "\\documentclass" not in cleaned:
        report.issues.append(Issue("error", main.name, "缺少 \\documentclass"))
    if "\\end{document}" not in cleaned:
        report.issues.append(Issue("error", main.name, "缺少 \\end{document}，编译会跑到文件尾报错"))

    for match in _BIB_RE.finditer(cleaned):
        for name in (part.strip() for part in match.group(1).split(",")):
            if name and not (root / f"{name}.bib").exists() and not (root / name).exists():
                report.issues.append(Issue("error", main.name, f"\\bibliography 指向的 {name}.bib 不存在"))

    for match in _ADD_BIB_RE.finditer(cleaned):
        name = match.group(1).strip()
        if name and not (root / name).exists():
            report.issues.append(Issue("error", main.name, f"\\addbibresource 指向的 {name} 不存在"))

    _check_inputs(main, cleaned, root, report, depth=0)
    _check_graphics(main, cleaned, root, report, _graphics_dirs(cleaned, root))
    return report


def _graphics_dirs(text: str, root: Path) -> list[Path]:
    """解析 ``\\graphicspath{{fig/}{img/}}``，把声明目录纳入图片存在性检查。"""
    dirs: list[Path] = []
    for match in _GRAPHICS_PATH_RE.finditer(text):
        for part in re.findall(r"\{([^{}]*)\}", match.group(1)):
            candidate = (root / part.strip()).resolve()
            if candidate not in dirs:
                dirs.append(candidate)
    return dirs


def _check_inputs(path: Path, text: str, root: Path, report: PreflightReport, depth: int) -> None:
    for match in _INPUT_RE.finditer(text):
        name = (match.group(1) or match.group(2) or "").strip()
        if not name:
            continue
        if _is_dynamic_path(name):
            report.issues.append(
                Issue("warning", path.name, f"动态 \\input/\\include 路径，跳过存在性检查: {name}")
            )
            continue
        target = _resolve(path.parent, name)
        if not target.exists():
            report.issues.append(Issue("error", path.name, f"\\input/\\include 目标不存在: {name}.tex"))
            continue
        if depth >= 2:
            continue
        child_text = _read(target, report)
        if child_text is not None:
            _check_inputs(target, _clean(child_text), root, report, depth + 1)


def _check_graphics(
    path: Path,
    text: str,
    root: Path,
    report: PreflightReport,
    graphics_dirs: list[Path] | None = None,
) -> None:
    for match in _GRAPHIC_RE.finditer(text):
        name = match.group(1).strip()
        if not name or _is_dynamic_path(name):
            continue
        candidates = [(path.parent / name).resolve()]
        candidates.extend((directory / name).resolve() for directory in graphics_dirs or [])
        if any(
            candidate.exists()
            or (
                not candidate.suffix
                and any(candidate.with_suffix(ext).exists() for ext in GRAPHIC_EXTS)
            )
            for candidate in candidates
        ):
            continue
        report.issues.append(Issue("warning", path.name, f"图片不存在: {name}"))


def format_report(report: PreflightReport, limit: int = 8) -> list[str]:
    """把报告转成终端可直接打印的行列表。"""
    lines: list[str] = []
    for issue in (report.errors + report.warnings)[:limit]:
        lines.append(issue.render())
    extra = len(report.errors) + len(report.warnings) - limit
    if extra > 0:
        lines.append(f"… 还有 {extra} 条检查问题")
    return lines
