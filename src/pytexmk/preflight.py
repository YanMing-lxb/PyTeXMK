"""编译前静态检查（preflight，3.2）。

目标不是做完整 TeX 语法分析，而是把**每次都会让编译白跑一轮**的低级错误
提前拦下来：

* 主文件不是 UTF-8 / 带 BOM；
* 缺少 ``\\documentclass`` 或 ``\\end{document}``；
* ``\\bibliography{...}`` 指向的 .bib 不存在；
* ``\\input``/``\\include`` 指向的文件不存在；
* ``\\includegraphics`` 指向的图片不存在（含常见扩展名推断）。

检查结果分 ``error``（阻止编译）与 ``warning``（仅提示）。``\\input``/图片
路径按**引擎工作目录**（项目根）解析，和 TeX 的真实查找规则一致；行号来自
实际命中的命令行，便于编辑器直接跳转。
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.tex_source import mask_tex_noncode

_BIB_RE = re.compile(r"\\bibliography\{([^}]*)\}")
_ADD_BIB_RE = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]*)\}")
# 必须要求命令名后不是字母：否则 ``\inputsection{...}`` 会被当成 ``\input section``，
# 把自定义命令的参数误报成缺失文件。
_INPUT_RE = re.compile(r"\\(?:input|include)(?![A-Za-z])\s*(?:\{([^}]*)\}|([^\s{}%]+))")
_GRAPHIC_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}")
# 只定位命令本身，参数体交给花括号匹配解析：``\graphicspath`` 的合法写法不止
# ``{{fig/}{img/}}`` 一种，模板里常见的还有逗号分隔的 ``{{Pictures/},}``（末项
# 为空即当前目录）。用一次性正则要求“若干花括号组后紧跟 ``}``”会把整条声明漏掉。
_GRAPHICS_PATH_CMD_RE = re.compile(r"\\graphicspath(?![A-Za-z])\s*")

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
    #: 命中命令在源文件中的行号（1 起算；结构性检查无法定位时为 1）。
    line: int = 1

    def render(self) -> str:
        return f"[{self.severity}] {self.file}:{self.line}: {self.message}"


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


def _display(path: Path, root: Path) -> str:
    """Issue 里显示项目相对路径（绝对路径对 CI 日志与编辑器都不友好）。"""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _line_of(text: str, index: int) -> int:
    """把字符下标换成 1 起算的行号。"""
    return text.count("\n", 0, max(0, index)) + 1


def _read(path: Path, report: PreflightReport, *, display: str | None = None) -> str | None:
    """读取并检查编码；返回 None 表示这个文件不该继续检查。"""
    name = display or path.name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        report.issues.append(Issue("error", name, f"无法读取: {exc}"))
        return None
    if raw.startswith(b"\xef\xbb\xbf"):
        report.issues.append(Issue("warning", name, "文件带 UTF-8 BOM，部分宏包会把它当正文"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        report.issues.append(
            Issue("error", name, f"不是有效 UTF-8（字节 {exc.start} 处）；请另存为 UTF-8")
        )
        return None
    return text


def _resolve(base: Path, name: str, *, include: bool) -> Path:
    target = base / name
    if include:
        if not name.endswith(".tex"):
            target = base / f"{name}.tex"
    elif not target.suffix:
        tex = base / f"{name}.tex"
        if tex.is_file() or not target.is_file():
            target = tex
    return target


def check_project(project_name: str, root: str | Path = ".") -> PreflightReport:
    """对主文件做一次 preflight；递归检查 ``\\input``。

    所有 ``\\input``/``\\include``/图片路径都按**引擎工作目录**（``root``）解析，
    而不是“被检查文件所在目录”。TeX 本身以后者为输入基准编译，旧实现按
    ``path.parent`` 拼接，嵌套输入 ``chapters/intro.tex`` 里的
    ``\\input{chapters/section}`` 会被错拼成 ``chapters/chapters/section.tex``，
    合法的工程因此被默认预检拦下（假阻断）。
    """
    root = Path(root)
    report = PreflightReport()
    main = root / f"{project_name}.tex"
    if not main.exists():
        report.issues.append(Issue("error", main.name, "主文件不存在"))
        return report

    text = _read(main, report, display=_display(main, root))
    if text is None:
        return report

    # 注释、verbatim、\verb 里的 \input/\includegraphics 不是可执行命令；
    # mask_tex_noncode 等长屏蔽，行号仍按原文计算。
    cleaned = _mask_macro_definitions(mask_tex_noncode(text))
    if "\\documentclass" not in cleaned:
        report.issues.append(Issue("error", _display(main, root), "缺少 \\documentclass"))
    if "\\end{document}" not in cleaned:
        report.issues.append(
            Issue("error", _display(main, root), "缺少 \\end{document}，编译会跑到文件尾报错")
        )

    for match in _BIB_RE.finditer(cleaned):
        for name in (part.strip() for part in match.group(1).split(",")):
            if name and not (root / f"{name}.bib").exists() and not (root / name).exists():
                report.issues.append(
                    Issue(
                        "error",
                        _display(main, root),
                        f"\\bibliography 指向的 {name}.bib 不存在",
                        _line_of(cleaned, match.start()),
                    )
                )

    for match in _ADD_BIB_RE.finditer(cleaned):
        name = match.group(1).strip()
        if name and not (root / name).exists():
            report.issues.append(
                Issue(
                    "error",
                    _display(main, root),
                    f"\\addbibresource 指向的 {name} 不存在",
                    _line_of(cleaned, match.start()),
                )
            )

    graphics_dirs = _graphics_dirs(cleaned, root)
    _check_inputs(main, cleaned, root, report, depth=0, graphics_dirs=graphics_dirs)
    _check_graphics(main, cleaned, root, report, graphics_dirs)
    return report


def _graphics_path_items(content: str) -> list[str]:
    """把 ``\\graphicspath`` 的参数体拆成目录列表。

    每项由花括号包住，条目之间既可相邻（``{{a/}{b/}}``）也可用逗号分隔
    （``{{a/},{b/}}``）；末项为空（``{{a/},}``）等价于当前目录，只当分隔符
    忽略。注释已在上层 ``_clean`` 阶段剥离。
    """
    items: list[str] = []
    index = 0
    while index < len(content):
        char = content[index]
        if char in " \t\r\n,":
            index += 1
            continue
        if char == "{":
            end = _matching_brace(content, index)
            if end < 0:
                break
            items.append(content[index + 1 : end])
            index = end + 1
            continue
        # 容错：未加花括号的 ``\graphicspath{fig/}`` 也按目录处理。
        end = index
        while end < len(content) and content[end] not in ",{} \t\r\n":
            end += 1
        items.append(content[index:end])
        index = end
    return [item.strip() for item in items if item.strip()]


def _graphics_dirs(text: str, root: Path) -> list[Path]:
    """解析 ``\\graphicspath`` 声明，把声明目录纳入图片存在性检查。"""
    dirs: list[Path] = []
    for match in _GRAPHICS_PATH_CMD_RE.finditer(text):
        if match.end() >= len(text) or text[match.end()] != "{":
            continue
        end = _matching_brace(text, match.end())
        if end < 0:
            continue
        for item in _graphics_path_items(text[match.end() + 1 : end]):
            candidate = (root / item.strip().strip('"')).resolve()
            if candidate not in dirs:
                dirs.append(candidate)
    return dirs


def _check_inputs(
    path: Path,
    text: str,
    root: Path,
    report: PreflightReport,
    depth: int,
    graphics_dirs: list[Path] | None = None,
) -> None:
    """递归检查 ``\\input``/``\\include``。

    ``graphics_dirs`` 是**已生效**的 ``\\graphicspath`` 目录：TeX 的该声明是全局
    的，主文件前导区声明的目录对后续所有 ``\\includegraphics`` 有效，子文件不
    需要重复声明。预检只做存在性提示，这里把继承目录与子文件自身新声明的目录
    宽松合并后继续下传，避免把合法图片误报为缺失。
    """
    inherited_dirs = list(graphics_dirs or [])

    for match in _INPUT_RE.finditer(text):
        name = (match.group(1) or match.group(2) or "").strip()
        if not name:
            continue
        line = _line_of(text, match.start())
        if _is_dynamic_path(name):
            report.issues.append(
                Issue(
                    "warning",
                    _display(path, root),
                    f"动态 \\input/\\include 路径，跳过存在性检查: {name}",
                    line,
                )
            )
            continue
        # TeX 以编译工作目录为基准找 \input，不是以当前被包含文件的目录。
        target = _resolve(root, name, include=match.group(0).startswith("\\include"))
        if not target.is_file():
            report.issues.append(
                Issue(
                    "error",
                    _display(path, root),
                    f"\\input/\\include 目标不存在: {_display(target, root)}",
                    line,
                )
            )
            continue
        if depth >= 2:
            continue
        child_text = _read(target, report, display=_display(target, root))
        if child_text is not None:
            child_cleaned = _mask_macro_definitions(mask_tex_noncode(child_text))
            child_dirs = list(inherited_dirs)
            for directory in _graphics_dirs(child_cleaned, root):
                if directory not in child_dirs:
                    child_dirs.append(directory)
            _check_inputs(target, child_cleaned, root, report, depth + 1, child_dirs)
            # 子文件里的图片也要查：只扫主文件会让“图片缺失”在编译阶段才暴露。
            _check_graphics(target, child_cleaned, root, report, child_dirs)


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
        # 图片同样按工作目录解析；同时保留“当前文件目录”作为宽松候选项，
        # 因为不少模板确实把图片放在章节旁边。这里只做存在性提示，不阻断。
        candidates = [(root / name).resolve(), (path.parent / name).resolve()]
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
        report.issues.append(
            Issue(
                "warning",
                _display(path, root),
                f"图片不存在: {name}",
                _line_of(text, match.start()),
            )
        )


def format_report(report: PreflightReport, limit: int = 8) -> list[str]:
    """把报告转成终端可直接打印的行列表。"""
    lines = [issue.render() for issue in (report.errors + report.warnings)[:limit]]
    extra = len(report.errors) + len(report.warnings) - limit
    if extra > 0:
        lines.append(f"… 还有 {extra} 条检查问题")
    return lines
