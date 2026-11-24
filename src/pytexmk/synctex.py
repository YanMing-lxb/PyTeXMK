"""SyncTeX 双向定位校验（3.11，2026-11 修订）。

`.synctex.gz` 存在不等于编辑器能跳转：native 构建（`-output-directory`）会改变
记录在 `.synctex.gz` 里的路径。本模块直接调用 `synctex view` / `synctex edit`：

* 正向：源文件第 N 行 → PDF 页码/坐标（编辑器“跳到 PDF”）
* 反向：PDF 坐标 → 源文件行号（编辑器“跳到源码”）

两者都通过才算 SyncTeX 可用。只依赖 TeX 发行版自带的 `synctex`，不引入第三方库。

取样行策略（修订点）
--------------------
旧实现取“第一个非空、非注释、不含 ``\\documentclass`` 的行”，对真实论文
通常是第 2 行的 ``\\usepackage``：前言行没有版面盒子，``synctex view`` 只能退化成
“第 1 页某个兜底坐标”，``synctex edit`` 又从该坐标反查到 ``\\begin{document}``，
于是“行号偏差过大”的**假失败**必然出现（几十行前言就必踩）。

现在改为：

1. 从 ``\\begin{document}`` 之后开始找**真正会产生版面盒子的行**（正文文字行优先，
   其次带可见内容的命令如 ``\\section{...}``），并准备多个候选；
2. 逐个候选跑正/反向，**任一候选通过即判定可用**，全部失败才报错（报第一个候选
   的错误，便于复现）；
3. 反向结果不再硬要求落在主文件：只要落在**项目源码树内的 .tex** 都算正常（多文件
   论文里取样行映射到 ``\\input`` 的子文件是正确行为），行号只在“回到主文件”时才
   比较，且容差收紧到 5 行（正文取样行的反查本来就是精确的）。
"""

import math
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.runtime_env import child_env

_PAGE_RE = re.compile(r"Page:\s*(\d+)")
#: 坐标必须允许负号与小数：synctex 的 y 轴向下为正，部分版面会给出负值；
#: 旧正则 `[0-9.]+` 既漏掉负坐标，也会把 "." 当合法数字。
_X_RE = re.compile(r"x:\s*([+-]?[0-9]*\.?[0-9]+)")
_Y_RE = re.compile(r"y:\s*([+-]?[0-9]*\.?[0-9]+)")
_INPUT_RE = re.compile(r"Input:\s*(.*)")
_LINE_RE = re.compile(r"Line:\s*(\d+)")

#: 反向回到主文件时允许的行号偏差。正文取样行的反查是精确的，这里只需容纳
#: “同一段落的盒子上沿/下沿落在相邻行”这类正常抖动。
_LINE_TOLERANCE = 5

#: 这些行只有“指令”没有盒子，或会切换输入文件，不适合作为取样行。
_NO_BOX_PREFIXES = (
    "\\input", "\\include", "\\includeonly", "\\label", "\\begin", "\\end",
    "\\thispagestyle", "\\pagestyle", "\\bibliography", "\\printbibliography",
    "\\clearpage", "\\newpage", "\\tableofcontents", "\\maketitle", "\\frontmatter",
    "\\backmatter", "\\appendix",
)

#: 这些行虽然以反斜杠开头，但会产生可见内容，可作为取样行。
_VISIBLE_CMD_PREFIXES = (
    "\\section", "\\subsection", "\\subsubsection", "\\chapter", "\\part",
    "\\paragraph", "\\subparagraph", "\\textbf", "\\textit", "\\emph",
    "\\caption", "\\item", "\\noindent",
)

#: 失败时只回显这些行（其余是 before/offset/middle 之类的噪声）
_TAIL_RE = re.compile(
    r"(Page|Input|Line|x:|y:|result begin|result end|No tag|not found|error)", re.I
)

#: synctex 文件与 PDF 允许的时间差（秒）。正常一次编译里 synctex 比 PDF 略新。
_MTIME_SLACK = 2.0


@dataclass
class SyncTeXReport:
    """一次双向校验的结果。"""

    ok: bool = False
    forward_page: int | None = None
    forward_x: float | None = None
    forward_y: float | None = None
    reverse_file: str | None = None
    reverse_line: int | None = None
    sample_line: int | None = None
    #: 结构化的"缺什么"标记（"pdf" / "synctex" / "tex"），供上层的提示分支使用。
    #: 不能靠匹配 errors 里的本地化文案判分支：LANGUAGE=en 时中文子串永远匹配不上。
    missing_artifact: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_tail: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.ok:
            return "SyncTeX 校验失败: " + "；".join(self.errors)
        coords = (
            f"({self.forward_x:.1f}, {self.forward_y:.1f})"
            if self.forward_x is not None and self.forward_y is not None
            else "(坐标不可用)"
        )
        return (
            f"SyncTeX 正常：正向 第 {self.forward_page} 页 {coords}，"
            f"反向 {Path(self.reverse_file or '').name}:{self.reverse_line}"
        )


def _run(command: list[str], cwd: Path) -> tuple[int, str]:
    """调用 synctex 命令行；与其它外部程序一样走净化后的环境变量。"""
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
            env=child_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def synctex_file(pdf_path: str | Path) -> Path:
    """按 PDF 路径推断同名的 synctex 文件（``.synctex.gz`` 优先）。"""
    pdf = Path(pdf_path)
    compressed = pdf.parent / f"{pdf.stem}.synctex.gz"
    if compressed.exists():
        return compressed
    plain = pdf.parent / f"{pdf.stem}.synctex"
    return plain if plain.exists() else compressed


def _body_start(lines: list[str]) -> int:
    """返回正文首行下标（``\\begin{document}`` 之后）；找不到就按 0 处理。"""
    for index, raw in enumerate(lines):
        if "\\begin{document}" in raw:
            return index + 1
    return 0


def _is_sample_candidate(text: str) -> bool:
    """该行是否可能产生版面盒子。"""
    stripped = text.strip()
    if not stripped or stripped.startswith("%"):
        return False
    if stripped.startswith(_NO_BOX_PREFIXES):
        return False
    if stripped.startswith("\\"):
        return stripped.startswith(_VISIBLE_CMD_PREFIXES)
    # 普通正文行：至少要有一个字母或数字
    return any(ch.isalnum() for ch in stripped)


def candidate_lines(source_text: str) -> list[int]:
    """给出用于正向搜索的候选行号（1 起算），正文优先、多个兜底。

    多候选的意义：单行取样碰到跨页段落、只含浮动体的段落、或被宏包重排的行时，
    反查结果本来就会有抖动；多试几行即可区分“SyncTeX 真的坏了”和“这一行不适合
    当样本”。
    """
    lines = source_text.splitlines()
    start = _body_start(lines)
    picked: list[int] = []

    def add(number: int) -> None:
        if number >= 1 and number not in picked:
            picked.append(number)

    # 1) 正文首个“有盒子”的行
    for index in range(start, len(lines)):
        if _is_sample_candidate(lines[index]):
            add(index + 1)
            break

    body = [i for i in range(start, len(lines)) if _is_sample_candidate(lines[i])]
    # 2) 正文中段的另一个候选
    if len(body) > 2:
        add(body[len(body) // 2] + 1)
    # 3) 正文最后一行可见内容
    if body:
        add(body[-1] + 1)

    # 4) 全文兜底（正文为空或整篇都是纯命令时）
    if not picked:
        for index, raw in enumerate(lines):
            stripped = raw.strip()
            if stripped and not stripped.startswith("%") and "\\documentclass" not in stripped:
                add(index + 1)
                break
    if not picked:
        add(1)
    return picked


def _resolve_reverse_path(raw: str, root: Path) -> Path:
    """把 synctex 报出的 Input 路径还原成绝对路径。

    TeX Live 记录的往往是相对路径（相对**编译时的工作目录**，也就是项目根目录），
    MiKTeX 记录绝对路径；两种都要能落到同一位置。个别发行版会把含空格的路径加引号。
    """
    path = Path(raw.strip().strip('"'))
    if not path.is_absolute():
        path = root / path
    try:
        return path.resolve()
    except OSError:
        return path


def _other_project_tex(path: Path, root: Path) -> bool:
    """反向落点是否是“项目源码树内的另一个 .tex”（多文件论文的正常情况）。"""
    if path.suffix.lower() != ".tex":
        return False
    try:
        return path.is_file() and path.is_relative_to(root)
    except OSError, ValueError:
        return False


def _check_one(
    binary: str,
    pdf: Path,
    tex: Path,
    line: int,
    root: Path,
    report: SyncTeXReport,
) -> SyncTeXReport:
    """对单个取样行跑一次正向 + 反向，返回带结论的 report（原地填充）。"""
    report.sample_line = line

    # 正向：必须用绝对路径，否则 synctex 会报 "No tag for xxx"
    code, output = _run(
        [binary, "view", "-i", f"{line}:1:{tex}", "-o", str(pdf)],
        root,
    )
    report.raw_tail = [
        ln for ln in output.splitlines() if ln.strip() and _TAIL_RE.search(ln)
    ][-10:]
    page_match = _PAGE_RE.search(output)
    x_match = _X_RE.search(output)
    y_match = _Y_RE.search(output)
    if code != 0 or not page_match:
        report.errors.append(f"正向搜索失败：synctex view 没有返回 Page（第 {line} 行）")
        return report

    report.forward_page = int(page_match.group(1))
    if not x_match or not y_match:
        # 只有 Page 没有坐标：synctex 返回了半份结果，旧实现随后在
        # ``summary()`` 里格式化 None 直接崩掉。
        report.errors.append(
            f"正向搜索缺少坐标：synctex view 只返回 Page（第 {line} 行）"
        )
        return report
    try:
        x = float(x_match.group(1))
        y = float(y_match.group(1))
    except ValueError:
        report.errors.append(f"正向搜索坐标不是数字（第 {line} 行）")
        return report
    if not (math.isfinite(x) and math.isfinite(y)):
        report.errors.append(f"正向搜索坐标不是有限值（第 {line} 行）")
        return report
    report.forward_x = x
    report.forward_y = y

    # 反向：page:x:y:pdf
    code, output = _run(
        [binary, "edit", "-o", f"{report.forward_page}:{x}:{y}:{pdf}"],
        root,
    )
    input_match = _INPUT_RE.search(output)
    line_match = _LINE_RE.search(output)
    if code != 0 or not input_match or not line_match:
        report.errors.append(
            f"反向搜索失败：synctex edit 没有返回 Input/Line（第 {line} 行）"
        )
        return report

    report.reverse_file = input_match.group(1).strip()
    report.reverse_line = int(line_match.group(1))
    reverse_path = _resolve_reverse_path(report.reverse_file, root)

    if reverse_path == tex:
        # 行号允许小偏差：SyncTeX 按版面盒子反查，段落上下沿本来就可能落在相邻行
        if abs(report.reverse_line - line) > _LINE_TOLERANCE:
            report.errors.append(
                f"反向搜索行号偏差过大：期望 {line}，实际 {report.reverse_line}"
            )
        report.ok = not report.errors
        return report

    if _other_project_tex(reverse_path, root):
        # 多文件论文：取样行落在 \input 的子文件里，编辑器跳过去同样正确
        report.warnings.append(
            f"取样行 {line} 的反向定位落在子文件 "
            f"{reverse_path.relative_to(root).as_posix()}，属正常多文件行为"
        )
        report.ok = True
        return report

    report.errors.append(
        f"反向搜索定位到项目外的文件: {report.reverse_file}（期望 {tex}）"
    )
    report.ok = False
    return report


def check(
    pdf_path: str | Path,
    tex_path: str | Path,
    *,
    line: int | None = None,
    root: str | Path = ".",
) -> SyncTeXReport:
    """跑一次正向 + 反向校验；``line`` 缺省按正文取样（多候选，任一通过即可）。"""
    pdf = Path(pdf_path).resolve()
    tex = Path(tex_path).resolve()
    root_path = Path(root).resolve()
    report = SyncTeXReport()

    if not pdf.exists():
        report.errors.append(f"PDF 不存在: {pdf}")
        report.missing_artifact = "pdf"
        return report
    if not tex.exists():
        report.errors.append(f"源文件不存在: {tex}")
        report.missing_artifact = "tex"
        return report

    sync_file = synctex_file(pdf)
    if not sync_file.exists():
        report.errors.append(f"SyncTeX 文件不存在: {sync_file}（需要重新编译生成）")
        report.missing_artifact = "synctex"
        return report
    try:
        gap = pdf.stat().st_mtime - sync_file.stat().st_mtime
    except OSError:
        gap = 0.0
    if gap > _MTIME_SLACK:
        report.warnings.append(
            f"{sync_file.name} 比 PDF 旧 {gap:.1f} 秒，可能是上次归档失败留下的旧文件"
        )

    binary = shutil.which("synctex")
    if not binary:
        report.errors.append("未找到 synctex 命令（MiKTeX/TeX Live 通常自带）")
        return report

    if line is not None:
        candidates = [line]
    else:
        try:
            source = tex.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            report.errors.append(f"源文件读取失败: {exc}")
            return report
        candidates = candidate_lines(source)

    primary: SyncTeXReport | None = None
    for candidate in candidates:
        attempt = SyncTeXReport()
        _check_one(binary, pdf, tex, candidate, root_path, attempt)
        attempt.warnings = list(report.warnings) + attempt.warnings
        if attempt.ok:
            return attempt
        if primary is None:
            primary = attempt

    if primary is None:
        # ``candidate_lines()`` 至少会返回第 1 行，但直接传入空候选列表的调用方
        # 仍可能走到这里；给可读错误，别让 ``-O`` 把 assert 剥掉后返回 None。
        report.errors.append("没有可用的 SyncTeX 样本行")
        return report
    return primary
