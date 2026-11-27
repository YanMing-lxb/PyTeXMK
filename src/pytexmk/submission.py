"""期刊投稿包生成与 pdflatex 兼容处理（3.9）。

期刊投稿系统通常只接受 **pdflatex**，而现代论文常用 XeLaTeX/LuaLaTeX +
fontspec/unicode-math/ctex，正文里还散落着 α、≤、→、°、µ、“”、— 等 Unicode
字符。直接把这些源文件丢给 pdflatex，会得到 ``Unicode character ... not set up
for use with LaTeX`` 之类的报错。

本模块做三件事：

1. **兼容性体检**：只扫描即将打包的 ``.tex``，报出 pdflatex 处理不了的字符
   与宏包及其 ``文件:行号``；**不自动改写正文**，由用户自己决定怎么改；
2. **导言区净化**：注释掉 fontspec/unicode-math/ctex 等只能 Xe/Lua 的宏包，
   补上 ``fontenc``/``inputenc``/``textcomp``；
3. **打包**：按 ``.fls`` 的 INPUT 记录收集真实依赖（图片、bib、bst、cls…），
   连同源 ``.bib`` 打成 zip（始终不含编译产物 ``.bbl``），并给出 PDF
   页数/体积/编译轮数摘要。
"""

import hashlib
import json
import re
import shutil
import tempfile
import time
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .fls import iter_fls_inputs
from .layout import FLS_IGNORED_SUFFIXES, SUBMISSION_EXCLUDED_DIRS, SUBMISSION_FALLBACK_SUFFIXES
from .tex_source import mask_tex_noncode

#: pdflatex 无法直接使用的宏包/机制（命中即需要在提交副本里处理）
PDFLATEX_INCOMPATIBLE = {
    "fontspec": "pdflatex 不支持 fontspec（只能用 Xe/LuaLaTeX）；注释该宏包后字体回落到 Computer Modern",
    "unicode-math": "pdflatex 不支持 unicode-math；注释该宏包后数学符号需改成 ASCII 写法",
    "ctex": "ctex 依赖 xeCJK/fontspec，只能 XeLaTeX/LuaLaTeX 编译；中文正文无法用 pdflatex 处理",
    "xeCJK": "xeCJK 只能 XeLaTeX 编译；中文正文无法用 pdflatex 处理",
    "luacode": "luacode 只能 LuaLaTeX 编译；相关代码块需手工改写",
    "luatexja": "luatexja 只能 LuaLaTeX 编译；日文正文无法用 pdflatex 处理",
    "polyglossia": "polyglossia 需 XeLaTeX/LuaLaTeX；pdflatex 请用 babel",
    "selnolig": "selnolig 需 LuaLaTeX；已注释",
    "microtype": "",  # 兼容，保留占位便于扩展
}

_PACKAGE_RE = re.compile(r"\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]*)\}")

#: 诊断日志里每个字符最多记录多少处 ``文件:行号``
_MAX_CHAR_LOCATIONS = 10

_PACKAGE_LINE_RE = re.compile(
    r"^\s*\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]*)\}(?P<rest>.*)$"
)

#: 导言区里属于 Xe/Lua 专属字体设置的命令（整行注释）
_FONT_SETUP_REAL_PREFIXES = (
    "\\setmainfont",
    "\\setsansfont",
    "\\setmonofont",
    "\\setmathfont",
    "\\setCJKmainfont",
    "\\setCJKsansfont",
    "\\setCJKmonofont",
    "\\setCJKfamilyfont",
    "\\newfontfamily",
    "\\defaultfontfeatures",
    "\\xeCJKsetup",
    "\\ctexset",
)


@dataclass
class CompatReport:
    """pdflatex 兼容性体检结果：只报问题，不做任何改写。"""

    #: 非 ASCII 字符 → 出现次数（提交副本原样保留，需用户自己改成 ASCII 写法）
    non_ascii_chars: dict[str, int] = field(default_factory=dict)
    incompatible_packages: dict[str, str] = field(default_factory=dict)  # 宏包 → 原因
    tex_files: list[Path] = field(default_factory=list)
    #: 字符 → 前若干处 ``文件:行号``，写进诊断日志供排查
    char_locations: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.non_ascii_chars and not self.incompatible_packages


@dataclass
class PackResult:
    """投稿包生成结果。"""

    zip_path: Path
    files: list[str]
    compat: CompatReport
    pdf_pages: int | None = None
    pdf_bytes: int | None = None
    sha256: str = ""
    rounds: int | None = None
    #: 本次是否对导言区做净化（决定“不兼容宏包”算已处理还是需手改）
    sanitize: bool = False
    #: 导言区被注释/补丁的命令
    sanitized: list[str] = field(default_factory=list)
    #: 应存在的 ``.fls`` 路径（``used_fls=False`` 时用来点名缺失的那份）
    fls_path: Path | None = None
    #: 依赖是否来自 ``.fls``；False 表示按后缀白名单兜底，包内可能混入未引用文件
    used_fls: bool = True
    #: 比 PDF 新的入包源文件（相对项目根）；空表示 PDF 不旧于源码
    stale_sources: list[str] = field(default_factory=list)
    #: 详细信息日志（与 zip 同目录，不进包）
    log_path: Path | None = None


def _package_names(text: str) -> set[str]:
    """取出文档加载的所有宏包名（支持一行多个、``\\RequirePackage``）。

    调用方必须传入已经屏蔽注释/verbatim 的文本；``% \\usepackage{fontspec}``
    只是说明文字，不是真实依赖。
    """
    names: set[str] = set()
    for match in _PACKAGE_RE.finditer(text):
        for name in match.group(1).split(","):
            name = name.strip()
            if name:
                names.add(name)
    return names


def scan_compat(root: Path, sources: Iterable[Path]) -> CompatReport:
    """扫描**即将打包**的 ``.tex``：只报告 pdflatex 处理不了的内容，不改写任何字符。

    调用方（``build_pack``）传入实际 staged 的文件；没有“扫整个项目”的模式，
    否则没进包的稿件（如另一语种版本）会把无关字符算进告警。
    """
    root = Path(root)
    report = CompatReport()
    for tex in sources:
        if tex.suffix.lower() != ".tex" or not tex.is_file():
            continue
        report.tex_files.append(tex)
        try:
            text = tex.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            relative = tex.relative_to(root).as_posix()
        except ValueError:
            relative = tex.name
        # 注释里的 \usepackage 是说明，不是加载；verbatim/comment 里的内容也只是示例。
        masked = mask_tex_noncode(text)
        for name in _package_names(masked):
            if PDFLATEX_INCOMPATIBLE.get(name):
                report.incompatible_packages[name] = PDFLATEX_INCOMPATIBLE[name]
        for line_no, line in enumerate(masked.splitlines(), 1):
            for char in line:
                if ord(char) <= 127:
                    continue
                report.non_ascii_chars[char] = report.non_ascii_chars.get(char, 0) + 1
                slots = report.char_locations.setdefault(char, [])
                if len(slots) < _MAX_CHAR_LOCATIONS:
                    slots.append(f"{relative}:{line_no}")
    return report


def sanitize_preamble(text: str) -> tuple[str, list[str]]:
    """把导言区改成 pdflatex 能吃的版本。

    只处理导言区（``\\begin{document}`` 之前）：

    * 注释 fontspec / unicode-math / ctex / xeCJK / luacode / luatexja /
      polyglossia / selnolig（以及伴随的 ``\\setmainfont`` 等字体设置）；
    * 补 ``fontenc``/``inputenc``/``textcomp``（缺什么补什么）；
    * 一行加载多个宏包时，只摘掉不兼容的那个，保留同行的兼容宏包。
    """
    marker = "\\begin{document}"
    index = text.find(marker)
    if index < 0:
        return text, []
    preamble, body = text[:index], text[index:]
    notes: list[str] = []
    masked = mask_tex_noncode(text)
    masked_preamble, masked_body = masked[:index], masked[index:]

    def rewrite_line(line: str, masked: str) -> str:
        ending = line[len(line.rstrip("\r\n")):]
        stripped = line.lstrip()
        if stripped.startswith("%"):
            return line
        start = len(line) - len(stripped)
        if start < len(masked) and masked[start] != line[start]:
            # 行首命令落在被屏蔽的区块（verbatim/comment 环境）内，不是真实加载。
            return line
        match = _PACKAGE_LINE_RE.match(stripped)
        if match:
            names = [n.strip() for n in match.group(1).split(",") if n.strip()]
            bad = [n for n in names if PDFLATEX_INCOMPATIBLE.get(n)]
            if bad:
                good = [n for n in names if n not in bad]
                notes.extend(
                    f"注释不兼容宏包 \\usepackage{{{name}}}" for name in bad
                )
                if good:
                    rest = match.group("rest").rstrip("\r\n")
                    return f"\\usepackage{{{','.join(good)}}}{rest}" + ending
                return f"% [pytexmk] {stripped.rstrip()}" + ending
            return line
        if any(stripped.startswith(prefix) for prefix in _FONT_SETUP_REAL_PREFIXES):
            notes.append(f"注释字体设置 {stripped.split('{')[0].strip()}")
            return f"% [pytexmk] {stripped.rstrip()}" + ending
        return line

    line_pairs = zip(
        preamble.splitlines(keepends=True),
        masked_preamble.splitlines(keepends=True),
        strict=True,
    )
    preamble = "".join(rewrite_line(line, masked) for line, masked in line_pairs)

    # 「已存在」的判断只看真实加载/真实用法，注释里提到的宏包或命令不算。
    additions: list[str] = []
    if "fontenc" not in masked_preamble:
        additions.append("\\usepackage[T1]{fontenc}")
        notes.append("补 \\usepackage[T1]{fontenc}")
    if "inputenc" not in masked_preamble:
        additions.append("\\usepackage[utf8]{inputenc}")
        notes.append("补 \\usepackage[utf8]{inputenc}")
    if "textcomp" not in masked_preamble and any(
        cmd in masked_preamble + masked_body
        for cmd in (
            "\\textregistered", "\\texttrademark", "\\textperthousand",
            "\\texteuro", "\\textyen", "\\textdegree", "\\textmu", "\\textbullet",
        )
    ):
        additions.append("\\usepackage{textcomp}")
        notes.append("补 \\usepackage{textcomp}")

    if additions:
        newline = "\r\n" if "\r\n" in text else "\n"
        block = (
            "% [pytexmk] pdflatex compatibility patch" + newline
            + newline.join(additions) + newline
        )
        doc = re.search(r"\\documentclass(?:\[[^\]]*\])?\{[^}]*\}", preamble)
        preamble = (
            preamble[: doc.end()] + newline + block + preamble[doc.end():]
            if doc
            else block + preamble
        )

    return preamble + body, notes


def _is_excluded_submission_path(relative: Path) -> bool:
    """投稿包收集时的目录排除规则（两种来源共用同一套语义）。"""
    return any(
        part.startswith(".") or part in SUBMISSION_EXCLUDED_DIRS
        for part in relative.parts[:-1]
    )


def _fls_files(root: Path, fls: Path) -> list[Path]:
    """从 .fls 的 INPUT 行收集依赖（只保留项目内、且非辅助产物）。"""
    files: list[Path] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for raw in iter_fls_inputs(fls):
        path = Path(raw)
        if not path.is_absolute():
            # ``.fls`` 里的相对路径本来就相对 PWD（即项目根），不能依赖调用方的
            # 工作目录：从别处调用 CLI 时 CWD 不是项目根，会整批解析失败。
            path = root_resolved / path
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root_resolved)
        except OSError, ValueError:
            continue
        if _is_excluded_submission_path(relative):
            continue
        key = relative.as_posix()
        if key in seen or resolved.suffix.lower() in FLS_IGNORED_SUFFIXES:
            continue
        seen.add(key)
        if resolved.is_file():
            files.append(resolved)
    return files


def _fallback_files(root: Path) -> list[Path]:
    """没有 .fls 时的兜底：按常见后缀收集项目文件。"""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUBMISSION_FALLBACK_SUFFIXES:
            continue
        rel = path.relative_to(root)
        if _is_excluded_submission_path(rel):
            continue
        files.append(path)
    return files


def _pdf_summary(pdf: Path | None) -> tuple[int | None, int | None]:
    if pdf is None or not pdf.exists():
        return None, None
    size = pdf.stat().st_size
    pages: int | None = None
    try:
        from pypdf import PdfReader

        pages = len(PdfReader(str(pdf)).pages)
    except Exception:
        pages = None
    return pages, size



def _read_rounds(auxdir: Path) -> int | None:
    """从共享状态文件读上一次构建的轮数；缺失/损坏时返回 None。"""
    try:
        state = json.loads((auxdir / ".pytexmk_refcache.json").read_text(encoding="utf-8"))
        return (state.get("pytexmk") or {}).get("build", {}).get("round")
    except Exception:
        return None


def _stale_sources(pdf: Path, sources: Iterable[Path], root: Path) -> list[str]:
    """返回比 ``pdf`` 新的源文件（相对项目根的 POSIX 路径）。

    源比 PDF 新意味着用户核对过的 PDF 与包内源码不是同一版；留 1 秒容差，
    避免同一秒内编译写入的时间戳抖动造成误报。
    """
    try:
        pdf_mtime = pdf.stat().st_mtime
    except OSError:
        return []
    stale: list[str] = []
    for source in sources:
        try:
            if Path(source).stat().st_mtime > pdf_mtime + 1.0:
                stale.append(Path(source).relative_to(root).as_posix())
        except (OSError, ValueError):
            continue
    return sorted(set(stale))


def _build_manifest(
    *,
    project_name: str,
    sanitize: bool,
    sanitized: list[str],
    compat: CompatReport,
) -> str:
    """生成包内 ``pytexmk-submission-notes.txt`` 的全文。"""
    lines = _manifest_header(project_name, sanitize)
    if sanitized:
        lines.extend(_sanitize_manifest_lines(sanitized))
    if not compat.ok:
        lines.extend(_compat_manifest_lines(compat, sanitize))
    lines.extend(_manifest_checklist())
    return "\n".join(lines) + "\n"


def _manifest_header(project_name: str, sanitize: bool) -> list[str]:
    """说明文件的表头。"""
    return [
        "# PyTeXMK 投稿包说明",
        f"# 项目: {project_name}",
        "# 字符处理: 仅报告，未自动转换（正文保持原样）",
        f"# 导言区净化: {'是' if sanitize else '否'}",
        "",
    ]


def _sanitize_manifest_lines(sanitized: list[str]) -> list[str]:
    """导言区净化记录。"""
    return ["## 导言区净化", *(f"- {note}" for note in sanitized), ""]


def _compat_manifest_lines(compat: CompatReport, sanitize: bool) -> list[str]:
    """pdflatex 兼容性警告：非 ASCII 字符与不兼容宏包（包内不附逐处位置，位置在本地日志）。

    ``sanitize=True`` 时宏包已由导言区净化注释，只需说明、不需手改。
    """
    lines = ["## pdflatex 兼容性警告"]
    if compat.non_ascii_chars:
        lines.append("- 以下非 ASCII 字符在提交副本里保持原样，pdflatex 无法处理，需手工改：")
        for char, count in sorted(compat.non_ascii_chars.items(), key=lambda kv: -kv[1]):
            lines.append(f"- 非 ASCII 字符 {char} (U+{ord(char):04X}) × {count}")
    if compat.incompatible_packages:
        if sanitize:
            lines.append("- 以下不兼容宏包已在提交副本中注释，无需手工处理：")
        else:
            lines.append("- 以下不兼容宏包仍留在提交副本里，pdflatex 无法编译，需手工处理：")
        for package, reason in compat.incompatible_packages.items():
            lines.append(f"- 不兼容宏包 {package}: {reason}")
    lines.append("")
    return lines


def _manifest_checklist() -> list[str]:
    """提交前检查清单；投稿包不附 ``.bbl``，参考文献由期刊端编译。"""
    return [
        "## 提交前检查清单",
        "- [ ] 在期刊系统允许的 pdflatex 版本上完整编译一次",
        "- [ ] 确认图片路径/文件名大小写与包内一致",
        "- [ ] 包内未附 .bbl：期刊端需运行 bibtex/biber 后重新编译参考文献",
        "- [ ] 检查版权/基金信息是否随投稿系统要求单独填写",
        "",
    ]


def _compat_log_lines(compat: CompatReport, sanitize: bool) -> list[str]:
    """日志用的兼容性明细：宏包原因 + 每个字符的计数与出现位置。

    ``sanitize=True`` 时宏包已被净化注释，标注为“无需手改”，与正文字符分开写。
    """
    if not compat.incompatible_packages and not compat.non_ascii_chars:
        return []
    lines = ["## pdflatex 兼容性（正文仅报告；导言区按需净化；注释已跳过）", ""]
    if compat.incompatible_packages:
        state = "提交副本已注释，无需手改" if sanitize else "未自动处理，需手改"
        lines.append(
            f"### 不兼容宏包（{len(compat.incompatible_packages)} 个，{state}）"
        )
        lines.extend(f"- {package}: {reason}" for package, reason in compat.incompatible_packages.items())
        lines.append("")
    if compat.non_ascii_chars:
        total = sum(compat.non_ascii_chars.values())
        lines.append(f"### 非 ASCII 字符（{len(compat.non_ascii_chars)} 种，共 {total} 次）")
        for char, count in sorted(compat.non_ascii_chars.items(), key=lambda kv: (-kv[1], kv[0])):
            spots = compat.char_locations.get(char, [])
            where = f"：{', '.join(spots)}" if spots else ""
            lines.append(f"- {char} (U+{ord(char):04X}) × {count}{where}")
        lines.append("")
        lines.append(f"每个字符最多列 {_MAX_CHAR_LOCATIONS} 处位置；完整计数见上。")
        lines.append(
            "说明：注释（行首/行尾）、verbatim/comment 环境、\\url/\\lstinline 参数里的"
            "字符不参与统计；条件块（\\iffalse）内的内容按正文统计。"
        )
        lines.append("")
        lines.append("这些字符在提交副本里保持原样，需手工改成 ASCII 写法或删除；")
        lines.append("中文/日文/俄文等非拉丁正文需要 ctex/xeCJK/babel 等方案，pdflatex 无法处理。")
        lines.append("")
    return lines


def _diagnostic_log_text(result: PackResult) -> str:
    """汇总投稿包的全部诊断信息；终端只提示日志位置。"""
    try:
        zip_bytes = result.zip_path.stat().st_size
    except OSError:
        zip_bytes = 0
    lines = [
        "# PyTeXMK 投稿包诊断日志",
        f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"# 包文件: {result.zip_path}",
        f"# 包内文件: {len(result.files)} 个",
        f"# 体积: {zip_bytes} 字节（{zip_bytes / 1024 / 1024:.2f} MB）",
        f"# PDF 页数: {result.pdf_pages if result.pdf_pages is not None else '未知'}",
        f"# 编译轮数: {result.rounds if result.rounds is not None else '未知'}",
        f"# SHA-256: {result.sha256}",
        "",
        "## 结论",
    ]
    if result.compat.ok:
        lines.append("- 未发现 pdflatex 处理不了的非 ASCII 字符或不兼容宏包。")
    else:
        if result.compat.incompatible_packages:
            count = len(result.compat.incompatible_packages)
            if result.sanitize:
                lines.append(
                    f"- 不兼容宏包 {count} 个，已在提交副本中注释，无需手工处理。"
                )
            else:
                lines.append(
                    f"- 不兼容宏包 {count} 个，仍留在提交副本里（keep_preamble 保留了导言区），需手工处理。"
                )
        if result.compat.non_ascii_chars:
            lines.append(
                f"- 非 ASCII 字符 {len(result.compat.non_ascii_chars)} 种，"
                f"共 {sum(result.compat.non_ascii_chars.values())} 次，提交副本未做转换。"
            )
            lines.append("- 若期刊只接受 pdflatex：把这些字符改成 ASCII 写法或删除，再重新打包。")
    lines.extend(["", "## 产物检查"])
    if result.used_fls:
        where = result.fls_path.as_posix() if result.fls_path is not None else ".fls"
        lines.append(f"- 依赖清单来自 {where}。")
    else:
        where = result.fls_path.as_posix() if result.fls_path is not None else ".fls"
        lines.append(
            f"- 未用上 {where}：依赖按后缀白名单兜底收集，包内可能混入未被引用的文件；"
            "建议先编译一次再打包。"
        )
    if result.pdf_bytes is None:
        lines.append("- 未找到构建 PDF，页数未知，无法判断源码与 PDF 是否同版。")
    elif result.stale_sources:
        names = "、".join(result.stale_sources[:3])
        more = f" 等 {len(result.stale_sources)} 个" if len(result.stale_sources) > 3 else ""
        lines.append(f"- PDF 早于 {names}{more}：建议重新编译后再提交。")
    else:
        lines.append("- PDF 不旧于任何入包源文件。")
    lines.extend(["", "## 包内文件", *(f"- {name}" for name in result.files), ""])
    if result.sanitized:
        lines.extend(_sanitize_manifest_lines(result.sanitized))
    lines.extend(_compat_log_lines(result.compat, result.sanitize))
    lines.extend(_manifest_checklist())
    return "\n".join(lines) + "\n"


def _write_diagnostic_log(result: PackResult, path: Path) -> Path:
    """把诊断日志写到 ``<包名>.log``（与 zip 同目录，不进包）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_diagnostic_log_text(result), encoding="utf-8")
    return path


def _write_zip(staging: Path, staged: list[str], zip_path: Path, *, reproducible: bool) -> None:
    """把暂存目录打成 zip（先写 ``.zip.tmp`` 再原子替换）。

    ``reproducible=False`` 时使用源文件的修改时间。旧实现两个分支都落回
    ``ZipInfo`` 的默认 1980-01-01，开关等于没生效；现在关闭可复现才真的写入
    时间戳，开启时仍固定时间并按名称排序，保证同一内容两次打包哈希一致。
    """
    tmp_zip = zip_path.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(set(staged)):
                info = zipfile.ZipInfo(name)
                if reproducible:
                    info.date_time = (1980, 1, 1, 0, 0, 0)  # 固定时间戳，便于复现
                else:
                    info.date_time = _zip_date_time(staging / name)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with zf.open(info, "w") as dest, (staging / name).open("rb") as src:
                    shutil.copyfileobj(src, dest)
        tmp_zip.replace(zip_path)
    finally:
        tmp_zip.unlink(missing_ok=True)


def _zip_date_time(path: Path) -> tuple[int, int, int, int, int, int]:
    """文件的本地修改时间 → ZIP 可接受的时间戳（1980–2107，偶数秒）。"""
    try:
        stamp = time.localtime(path.stat().st_mtime)[:6]
    except OSError:
        return (1980, 1, 1, 0, 0, 0)
    year, month, day, hour, minute, second = stamp
    if year < 1980:
        return (1980, 1, 1, 0, 0, 0)
    if year > 2107:
        return (2107, 12, 31, 23, 59, 58)
    # ZIP 的 DOS 时间字段只保存 2 秒精度；先截断，读回时才不会出现 1 秒偏差。
    return (year, month, day, hour, minute, second - second % 2)


@dataclass
class _SubmissionStager:
    """把候选文件写入 staging，并按配置净化导言区。

    字符一律原样复制：``-sp`` 只负责报告 pdflatex 处理不了的内容，
    不再自动改写正文。
    """

    root: Path
    staging: Path
    sanitize: bool
    staged: list[str] = field(default_factory=list)
    sanitized: list[str] = field(default_factory=list)

    def stage_candidate(self, source: Path) -> None:
        """按后缀处理一个 ``.fls``/fallback 候选；``.bbl`` 是编译产物，一律不打包。"""
        try:
            relative = source.relative_to(self.root)
        except ValueError:
            return
        suffix = source.suffix.lower()
        if suffix == ".bbl":
            return

        target = self.staging / relative
        if suffix == ".tex" and self.sanitize:
            self._stage_tex(source, target, relative.as_posix())
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.copy(target, preserve_metadata=True)
        self.staged.append(relative.as_posix())

    def _stage_tex(self, source: Path, target: Path, relative: str) -> None:
        """按需净化导言区；没有改动就按字节复制，避免 CRLF/编码被顺手改掉。"""
        text = source.read_text(encoding="utf-8", errors="replace")
        cleaned, notes = sanitize_preamble(text)
        if not notes:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.copy(target, preserve_metadata=True)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(cleaned, encoding="utf-8")
        self.sanitized.extend(f"{relative}: {note}" for note in notes)

    def stage_bib(self, project_name: str) -> None:
        """补入项目内**所有** .bib（不依赖 ``--include-bib``，始终执行）。

        期刊常要求把 ``\\bibliography{a,b}`` 的所有数据库一起上传；旧实现只
        补 ``<project_name>.bib``，多库项目会缺文件。已在候选阶段收过的
        （.fls 记录）按 ``staged`` 去重。
        """
        seen = set(self.staged)
        for bib in sorted(self.root.rglob("*.bib")):
            try:
                relative = bib.relative_to(self.root)
            except ValueError:
                continue
            if _is_excluded_submission_path(relative):
                continue
            name = relative.as_posix()
            if name in seen:
                continue
            target = self.staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            bib.copy(target, preserve_metadata=True)
            self.staged.append(name)
            seen.add(name)


def build_pack(
    root: str | Path,
    project_name: str,
    outdir: str | Path,
    auxdir: str | Path,
    *,
    pdf_name: str | None = None,
    submit_dir: str | Path = "./Submission",
    sanitize: bool = True,
    reproducible: bool = True,
) -> PackResult:
    """生成投稿 zip：正文原样复制，只做导言区净化与兼容性报告。

    包内只带源 ``.bib``，始终不附编译产物 ``.bbl``：参考文献由期刊端
    运行 bibtex/biber 后重新编译。
    """
    root = Path(root).resolve()
    outdir = Path(outdir)
    auxdir = Path(auxdir)
    # build_name 是 TeX 的 jobname（--jobname 后的输出名）；源 .tex 仍按 project_name。
    build_name = pdf_name or project_name
    staging_parent = Path(tempfile.mkdtemp(prefix="pytexmk_submission_"))
    staging = staging_parent / project_name
    staging.mkdir(parents=True)

    fls = auxdir / f"{build_name}.fls"
    used_fls = fls.exists()
    candidates = _fls_files(root, fls) if used_fls else _fallback_files(root)
    if not candidates:
        candidates = _fallback_files(root)
        # .fls 里没有一条项目内 INPUT 时同样只能兜底，按“未用上”报出来。
        used_fls = False

    stager = _SubmissionStager(root=root, staging=staging, sanitize=sanitize)

    try:
        for source in sorted(set(candidates)):
            stager.stage_candidate(source)
        # 投稿系统要求包内存在可编译的主入口：.fls 漏记主文件（或候选被过滤器
        # 排除）时，必须显式补进 <project_name>.tex，否则包里有 PDF 没有入口。
        main_source = root / f"{project_name}.tex"
        if not main_source.exists():
            raise FileNotFoundError(f"主文件不存在，无法生成投稿包: {main_source}")
        # zip 内的名字统一用 POSIX 分隔符；Windows 的 `project_name` 可能带 `\`。
        main_entry = Path(f"{project_name}.tex").as_posix()
        if main_entry not in {Path(name).as_posix() for name in stager.staged}:
            stager.stage_candidate(main_source)
        stager.stage_bib(project_name)

        # 只体检真正进包的 .tex：没被这次编译引用、也没打进去的稿件（如另一语种
        # 版本）不该出现在报告里，否则告警数量会被无关文件稀释。
        packed_tex = sorted(
            root / Path(name) for name in stager.staged if name.lower().endswith(".tex")
        )
        compat = scan_compat(root, packed_tex)

        manifest = _build_manifest(
            project_name=project_name,
            sanitize=sanitize,
            sanitized=stager.sanitized,
            compat=compat,
        )
        (staging / "pytexmk-submission-notes.txt").write_text(manifest, encoding="utf-8")
        stager.staged.append("pytexmk-submission-notes.txt")

        pdf_path = outdir / f"{build_name}.pdf"
        pages, pdf_bytes = _pdf_summary(pdf_path)
        # 入包源文件比 PDF 新 → 用户核对的 PDF 与包内源码不是同一版。
        stale = _stale_sources(pdf_path, packed_tex, root)

        submit = Path(submit_dir)
        if not submit.is_absolute():
            submit = root / submit
        submit.mkdir(parents=True, exist_ok=True)
        zip_path = submit / f"{project_name}-submission.zip"
        _write_zip(staging, stager.staged, zip_path, reproducible=reproducible)

        with zip_path.open("rb") as fh:
            digest = hashlib.file_digest(fh, "sha256").hexdigest()
        rounds = _read_rounds(auxdir)
        try:
            fls_display: Path = fls.resolve().relative_to(root)
        except (OSError, ValueError):
            fls_display = fls

        result = PackResult(
            zip_path=zip_path,
            files=sorted(set(stager.staged)),
            compat=compat,
            pdf_pages=pages,
            pdf_bytes=pdf_bytes,
            sha256=digest,
            rounds=rounds,
            sanitize=sanitize,
            sanitized=stager.sanitized,
            fls_path=fls_display,
            used_fls=used_fls,
            stale_sources=stale,
        )
        # 与 zip 同目录的 <包名>.log：终端只提示路径，明细全部落盘。
        result.log_path = _write_diagnostic_log(result, zip_path.with_suffix(".log"))
        return result
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
