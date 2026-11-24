"""期刊投稿包生成与 pdflatex 兼容处理（3.9）。

期刊投稿系统通常只接受 **pdflatex**，而现代论文常用 XeLaTeX/LuaLaTeX +
fontspec/unicode-math/ctex，正文里还散落着 α、≤、→、°、µ、“”、— 等 Unicode
字符。直接把这些源文件丢给 pdflatex，会得到 ``Unicode character ... not set up
for use with LaTeX`` 之类的报错。

本模块做四件事：

1. **兼容性体检**：扫描源码，报出 pdflatex 不认识的宏包与字符；
2. **Unicode → LaTeX 转换副本**：把字符换成 ``\\ensuremath{\\alpha}``、
   ``\\textdegree``、``` `` '' ``` 等纯 ASCII 等价写法；
3. **导言区净化**：注释掉 fontspec/unicode-math/ctex 等只能 Xe/Lua 的宏包，
   补上 ``fontenc``/``inputenc``/``textcomp``，让转换副本能真的被 pdflatex 吃下；
4. **打包**：按 ``.fls`` 的 INPUT 记录收集真实依赖（图片、bib、bst、cls…），
   连同源 ``.bib`` 打成 zip（``include_bbl`` 时再附 ``.bbl``），并给出 PDF
   页数/体积/编译轮数摘要。
"""

import hashlib
import json
import re
import shutil
import tempfile
import time
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .fls import iter_fls_inputs
from .layout import FLS_IGNORED_SUFFIXES, SUBMISSION_EXCLUDED_DIRS, SUBMISSION_FALLBACK_SUFFIXES
from .tex_source import first_comment_index, mask_tex_noncode

#: pdflatex 无法直接使用的宏包/机制（命中即需要在提交副本里处理）
PDFLATEX_INCOMPATIBLE = {
    "fontspec": "pdflatex 不支持 fontspec；已注释该宏包并补上 fontenc/inputenc，字体回落到 Computer Modern",
    "unicode-math": "pdflatex 不支持 unicode-math；已注释该宏包，数学符号转为 \\ensuremath",
    "ctex": "ctex 依赖 xeCJK/fontspec，只能 XeLaTeX/LuaLaTeX 编译；中文正文无法用 pdflatex 处理",
    "xeCJK": "xeCJK 只能 XeLaTeX 编译；中文正文无法用 pdflatex 处理",
    "luacode": "luacode 只能 LuaLaTeX 编译；相关代码块需手工改写",
    "luatexja": "luatexja 只能 LuaLaTeX 编译；日文正文无法用 pdflatex 处理",
    "polyglossia": "polyglossia 需 XeLaTeX/LuaLaTeX；pdflatex 请用 babel",
    "selnolig": "selnolig 需 LuaLaTeX；已注释",
    "microtype": "",  # 兼容，保留占位便于扩展
}

_PACKAGE_RE = re.compile(r"\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]*)\}")

#: 投稿说明里"首次出现位置"最多列 40 条，避免清单本身变成垃圾
_MAX_LOCATION_SAMPLES = 40

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

#: Unicode → LaTeX 映射（覆盖论文里高频的希腊字母、数学符号、单位、标点）
UNICODE_MAP: dict[str, str] = {
    # 希腊字母（小写）
    "α": r"\ensuremath{\alpha}", "β": r"\ensuremath{\beta}", "γ": r"\ensuremath{\gamma}",
    "δ": r"\ensuremath{\delta}", "ε": r"\ensuremath{\epsilon}", "ζ": r"\ensuremath{\zeta}",
    "η": r"\ensuremath{\eta}", "θ": r"\ensuremath{\theta}", "ι": r"\ensuremath{\iota}",
    "κ": r"\ensuremath{\kappa}", "λ": r"\ensuremath{\lambda}", "μ": r"\ensuremath{\mu}",
    "ν": r"\ensuremath{\nu}", "ξ": r"\ensuremath{\xi}", "ο": "o",
    "π": r"\ensuremath{\pi}", "ρ": r"\ensuremath{\rho}", "ς": r"\ensuremath{\varsigma}",
    "σ": r"\ensuremath{\sigma}", "τ": r"\ensuremath{\tau}", "υ": r"\ensuremath{\upsilon}",
    "φ": r"\ensuremath{\phi}", "χ": r"\ensuremath{\chi}", "ψ": r"\ensuremath{\psi}",
    "ω": r"\ensuremath{\omega}", "ϑ": r"\ensuremath{\vartheta}", "ϕ": r"\ensuremath{\varphi}",
    # 希腊字母（大写）
    "Α": "A", "Β": "B", "Γ": r"\ensuremath{\Gamma}", "Δ": r"\ensuremath{\Delta}",
    "Ε": "E", "Ζ": "Z", "Η": "H", "Θ": r"\ensuremath{\Theta}", "Ι": "I",
    "Κ": "K", "Λ": r"\ensuremath{\Lambda}", "Μ": "M", "Ν": "N",
    "Ξ": r"\ensuremath{\Xi}", "Ο": "O", "Π": r"\ensuremath{\Pi}", "Ρ": "P",
    "Σ": r"\ensuremath{\Sigma}", "Τ": "T", "Υ": r"\ensuremath{\Upsilon}",
    "Φ": r"\ensuremath{\Phi}", "Χ": "X", "Ψ": r"\ensuremath{\Psi}",
    "Ω": r"\ensuremath{\Omega}",
    # 比较 / 集合 / 逻辑
    "≤": r"\ensuremath{\leq}", "≥": r"\ensuremath{\geq}", "≠": r"\ensuremath{\neq}",
    "≈": r"\ensuremath{\approx}", "≡": r"\ensuremath{\equiv}", "≃": r"\ensuremath{\simeq}",
    "≅": r"\ensuremath{\cong}", "∝": r"\ensuremath{\propto}", "≪": r"\ensuremath{\ll}",
    "≫": r"\ensuremath{\gg}", "∈": r"\ensuremath{\in}", "∉": r"\ensuremath{\notin}",
    "⊂": r"\ensuremath{\subset}", "⊃": r"\ensuremath{\supset}",
    "⊆": r"\ensuremath{\subseteq}", "⊇": r"\ensuremath{\supseteq}",
    "∪": r"\ensuremath{\cup}", "∩": r"\ensuremath{\cap}",
    "∖": r"\ensuremath{\setminus}", "∅": r"\ensuremath{\emptyset}",
    "∀": r"\ensuremath{\forall}", "∃": r"\ensuremath{\exists}",
    "∧": r"\ensuremath{\wedge}", "∨": r"\ensuremath{\vee}",
    "¬": r"\ensuremath{\neg}", "⊢": r"\ensuremath{\vdash}",
    "⊨": r"\ensuremath{\models}", "⊥": r"\ensuremath{\perp}",
    "∥": r"\ensuremath{\parallel}", "∼": r"\ensuremath{\sim}",
    # 运算
    "±": r"\ensuremath{\pm}", "∓": r"\ensuremath{\mp}", "×": r"\ensuremath{\times}",
    "÷": r"\ensuremath{\div}", "·": r"\ensuremath{\cdot}", "⋅": r"\ensuremath{\cdot}",
    "∘": r"\ensuremath{\circ}", "⊕": r"\ensuremath{\oplus}", "⊗": r"\ensuremath{\otimes}",
    "⊙": r"\ensuremath{\odot}", "∞": r"\ensuremath{\infty}",
    "∑": r"\ensuremath{\sum}", "∏": r"\ensuremath{\prod}", "∫": r"\ensuremath{\int}",
    "∬": r"\ensuremath{\iint}", "∮": r"\ensuremath{\oint}",
    "∂": r"\ensuremath{\partial}", "∇": r"\ensuremath{\nabla}",
    "√": r"\ensuremath{\sqrt{\ }}", "ℓ": r"\ensuremath{\ell}", "ℏ": r"\ensuremath{\hbar}",
    "ℜ": r"\ensuremath{\Re}", "ℑ": r"\ensuremath{\Im}",
    # 箭头
    "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
    "↑": r"\ensuremath{\uparrow}", "↓": r"\ensuremath{\downarrow}",
    "⇒": r"\ensuremath{\Rightarrow}", "⇐": r"\ensuremath{\Leftarrow}",
    "⇔": r"\ensuremath{\Leftrightarrow}", "↔": r"\ensuremath{\leftrightarrow}",
    "↦": r"\ensuremath{\mapsto}", "↗": r"\ensuremath{\nearrow}",
    "↘": r"\ensuremath{\searrow}", "⟶": r"\ensuremath{\longrightarrow}",
    # 单位 / 特殊符号（尽量用 LaTeX 内核就有、不依赖 textcomp 的写法）
    "°": r"\textdegree{}", "℃": r"\textdegree{}C",
    "µ": r"\ensuremath{\mu}", "‰": r"\textperthousand{}", "§": r"\S{}",
    "©": r"\copyright{}", "®": r"\textregistered{}", "™": r"\texttrademark{}",
    "€": r"\texteuro{}", "£": r"\pounds{}", "¥": r"\textyen{}",
    "Å": r"\AA{}", "Å": r"\AA{}", "•": r"\textbullet{}",
    # 标点 / 排版
    "–": "--", "—": "---", "‐": "-", "‑": "-", "…": r"\ldots{}",
    "‘": "`", "’": "'", "“": "``", "”": "''",
    "′": r"\ensuremath{'}", "″": r"\ensuremath{''}",
    "«": r"\guillemotleft{}", "»": r"\guillemotright{}",
    "，": ",", "。": ".", "；": ";", "：": ":", "？": "?", "！": "!",
    "（": "(", "）": ")", "【": "[", "】": "]", "、": ",", "《": r"\guillemotleft{}",
    "》": r"\guillemotright{}", "「": "`", "」": "'", "『": "``", "』": "''",
    # 分数 / 上标 / 下标
    "½": r"\ensuremath{\frac{1}{2}}", "¼": r"\ensuremath{\frac{1}{4}}",
    "¾": r"\ensuremath{\frac{3}{4}}",
    "²": r"\ensuremath{^{2}}", "³": r"\ensuremath{^{3}}", "¹": r"\ensuremath{^{1}}",
    "⁰": r"\ensuremath{^{0}}", "⁴": r"\ensuremath{^{4}}", "⁵": r"\ensuremath{^{5}}",
    "⁶": r"\ensuremath{^{6}}", "⁷": r"\ensuremath{^{7}}", "⁸": r"\ensuremath{^{8}}",
    "⁹": r"\ensuremath{^{9}}", "⁺": r"\ensuremath{^{+}}", "⁻": r"\ensuremath{^{-}}",
    "₀": r"\ensuremath{_{0}}", "₁": r"\ensuremath{_{1}}", "₂": r"\ensuremath{_{2}}",
    "₃": r"\ensuremath{_{3}}", "₄": r"\ensuremath{_{4}}", "₅": r"\ensuremath{_{5}}",
    "₆": r"\ensuremath{_{6}}", "₇": r"\ensuremath{_{7}}", "₈": r"\ensuremath{_{8}}",
    "₉": r"\ensuremath{_{9}}", "₊": r"\ensuremath{_{+}}", "₋": r"\ensuremath{_{-}}",
    # 连字（NFKD 不会拆）
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    # 不可见字符
    "\u00a0": "~", "\u2009": r"\,", "\u202f": r"\,", "\u200b": "", "\ufeff": "",
    "\u2002": r"\enspace{}", "\u2003": r"\quad{}",
}

_COMBINING_ACCENTS = {
    "\u0301": "'", "\u0300": "`", "\u0302": "^", "\u0303": "~", "\u0308": '"',
    "\u030a": "r", "\u030c": "v", "\u0327": "c", "\u0306": "u", "\u0304": "=",
    "\u0307": ".", "\u030b": "H", "\u0328": "k", "\u0331": "b",
}

_VERBATIM_ENVS = ("verbatim", "Verbatim", "lstlisting", "minted", "alltt", "filecontents")
_VERB_RE = re.compile(r"\\(verb\*?)([^\s])(.*?)\2")
_PLACEHOLDER = "\x00PYTEXMK{}\x00"


@dataclass
class ConversionRecord:
    """一条 Unicode → LaTeX 转换记录（写进清单）。"""

    file: str
    line: int
    char: str
    codepoint: str
    replacement: str


@dataclass
class CompatReport:
    """pdflatex 兼容性体检结果。"""

    unsupported_chars: dict[str, int] = field(default_factory=dict)  # 字符 → 出现次数
    incompatible_packages: dict[str, str] = field(default_factory=dict)  # 宏包 → 原因
    tex_files: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unsupported_chars and not self.incompatible_packages


@dataclass
class PackResult:
    """投稿包生成结果。"""

    zip_path: Path
    files: list[str]
    conversions: list[ConversionRecord]
    compat: CompatReport
    pdf_pages: int | None = None
    pdf_bytes: int | None = None
    sha256: str = ""
    rounds: int | None = None
    #: 转换后仍残留的非 ASCII 字符（pdflatex 必炸）
    remaining_chars: dict[str, int] = field(default_factory=dict)
    #: 残留字符位置，最多记录前 20 条
    remaining_locations: list[str] = field(default_factory=list)
    #: 导言区被注释/补丁的命令
    sanitized: list[str] = field(default_factory=list)


def _iter_tex_sources(root: Path, project_name: str) -> list[Path]:
    """项目内的 .tex（跳过产物目录与隐藏目录）。"""
    result: list[Path] = []
    for path in root.rglob("*.tex"):
        parts = path.relative_to(root).parts[:-1]
        if any(p.startswith(".") or p in {"Build", "Auxiliary", "Submission"} for p in parts):
            continue
        if (path.parent / ".pytexmkrc").exists() and path.parent != root:
            continue
        result.append(path)
    main = root / f"{project_name}.tex"
    if main.exists() and main not in result:
        result.insert(0, main)
    return result


def _strip_comments(line: str) -> str:
    """去掉行内注释（不做完整 TeX 词法，只为兼容性扫描降噪）。"""
    return line[: first_comment_index(line)]


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


def scan_compat(root: Path, project_name: str) -> CompatReport:
    """扫描项目，报告 pdflatex 不兼容的字符与宏包。"""
    root = Path(root)
    report = CompatReport()
    for tex in _iter_tex_sources(root, project_name):
        report.tex_files.append(tex)
        try:
            text = tex.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # 注释里的 \usepackage 是说明，不是加载；verbatim 里的内容也只是示例。
        for name in _package_names(mask_tex_noncode(text)):
            if PDFLATEX_INCOMPATIBLE.get(name):
                report.incompatible_packages[name] = PDFLATEX_INCOMPATIBLE[name]
        for line in text.splitlines():
            code = _strip_comments(line)
            for char in code:
                if ord(char) > 127 and not _convert_char(char):
                    report.unsupported_chars[char] = report.unsupported_chars.get(char, 0) + 1
    return report


def _decompose(char: str) -> str | None:
    """把带音符的拉丁字母分解成 ``\\'{e}`` 形式；失败返回 None。"""
    decomposed = unicodedata.normalize("NFKD", char)
    if len(decomposed) < 2:
        return None
    base = decomposed[0]
    accents = decomposed[1:]
    if not base.isascii() or not base.isalpha():
        return None
    if len(accents) != 1:
        return None
    command = _COMBINING_ACCENTS.get(accents[0])
    if command is None:
        return None
    return f"\\{command}{{{base}}}"


def _nfkd_ascii(char: str) -> str | None:
    """全角/兼容字符的兜底：NFKD 后全部落在 ASCII 就直接用。"""
    decomposed = unicodedata.normalize("NFKD", char)
    if decomposed == char or not decomposed:
        return None
    if all(ord(item) < 128 for item in decomposed):
        return decomposed
    # ``℃`` NFKD 成 ``°C``：继续递归转换，直到收敛
    result = []
    for item in decomposed:
        converted = UNICODE_MAP.get(item) or _decompose(item) or _nfkd_ascii(item)
        if converted is None:
            return None
        result.append(converted)
    return "".join(result)


def _convert_char(char: str) -> str | None:
    """单个字符 → LaTeX 替换串；无法转换返回 None。"""
    if ord(char) < 128:
        return char
    if char in UNICODE_MAP:
        return UNICODE_MAP[char]
    accent = _decompose(char)
    if accent is not None:
        return accent
    return _nfkd_ascii(char)


def _protect_verbatim(text: str) -> tuple[str, list[str]]:
    """把 ``\\verb`` 与 verbatim 环境替换成占位符，避免把代码里的字符也转换。"""
    stored: list[str] = []

    def keep(payload: str) -> str:
        stored.append(payload)
        return _PLACEHOLDER.format(len(stored) - 1)

    # 环境（跨行）先整体保护
    for env in _VERBATIM_ENVS:
        pattern = re.compile(
            rf"(\\begin\{{{env}\}}.*?\\end\{{{env}\}})", re.DOTALL
        )
        text = pattern.sub(lambda m: keep(m.group(1)), text)

    # 行内 \verb|...|（分隔符可以是任意非空白字符）
    text = _VERB_RE.sub(lambda m: keep(m.group(0)), text)
    return text, stored


def _restore_verbatim(text: str, stored: list[str]) -> str:
    """还原被 :func:`_protect_verbatim` 保护的内容。"""
    for index, payload in enumerate(stored):
        text = text.replace(_PLACEHOLDER.format(index), payload)
    return text


def convert_text(text: str) -> tuple[str, list[tuple[str, str]]]:
    """把文本中的非 ASCII 字符转成 LaTeX 等价写法。

    返回 ``(转换后文本, [(原字符, 替换串), ...])``；无法转换的字符原样保留，
    由 :func:`scan_compat` 报告给用户手工处理。``\\verb``/verbatim 环境内
    的内容不转换。
    """
    protected, stored = _protect_verbatim(text)
    converted: list[str] = []
    replacements: list[tuple[str, str]] = []
    for char in protected:
        replacement = _convert_char(char)
        if replacement is None:
            converted.append(char)
            continue
        if replacement != char:
            replacements.append((char, replacement))
        converted.append(replacement)
    return _restore_verbatim("".join(converted), stored), replacements


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

    def rewrite_line(line: str) -> str:
        stripped = line.lstrip()
        if stripped.startswith("%"):
            return line
        match = _PACKAGE_LINE_RE.match(line)
        if match:
            names = [n.strip() for n in match.group(1).split(",") if n.strip()]
            bad = [n for n in names if PDFLATEX_INCOMPATIBLE.get(n)]
            if bad:
                good = [n for n in names if n not in bad]
                notes.extend(
                    f"注释不兼容宏包 \\usepackage{{{name}}}" for name in bad
                )
                if good:
                    return f"\\usepackage{{{','.join(good)}}}{match.group('rest')}"
                return f"% [pytexmk] {line.lstrip().rstrip()}\n"
            return line
        if any(stripped.startswith(prefix) for prefix in _FONT_SETUP_REAL_PREFIXES):
            notes.append(f"注释字体设置 {stripped.split('{')[0].strip()}")
            return f"% [pytexmk] {line.lstrip().rstrip()}\n"
        return line

    preamble = "".join(rewrite_line(line) for line in preamble.splitlines(keepends=True))

    additions: list[str] = []
    if "fontenc" not in preamble:
        additions.append("\\usepackage[T1]{fontenc}")
        notes.append("补 \\usepackage[T1]{fontenc}")
    if "inputenc" not in preamble:
        additions.append("\\usepackage[utf8]{inputenc}")
        notes.append("补 \\usepackage[utf8]{inputenc}")
    if "textcomp" not in preamble and any(
        cmd in preamble + body for cmd in ("\\textregistered", "\\texttrademark", "\\textperthousand", "\\texteuro", "\\textyen", "\\textdegree", "\\textmu", "\\textbullet")
    ):
        additions.append("\\usepackage{textcomp}")
        notes.append("补 \\usepackage{textcomp}")

    if additions:
        block = "% [pytexmk] pdflatex compatibility patch\n" + "\n".join(additions) + "\n"
        doc = re.search(r"\\documentclass(?:\[[^\]]*\])?\{[^}]*\}", preamble)
        preamble = (
            preamble[: doc.end()] + "\n" + block + preamble[doc.end():]
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


def _scan_remaining(text: str, relative: str) -> tuple[dict[str, int], list[str]]:
    """统计文本中残留的非 ASCII 字符及其首次出现位置。"""
    counts: dict[str, int] = {}
    locations: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        code = _strip_comments(line)  # 注释里的 Unicode 不会让 pdflatex 报错
        for char in code:
            if ord(char) <= 127:
                continue
            counts[char] = counts.get(char, 0) + 1
            if len(locations) < 60 and not any(
                item.startswith(f"{relative}:{line_no}  {char} ") for item in locations
            ):
                locations.append(f"{relative}:{line_no}  {char} (U+{ord(char):04X})")
    return counts, locations


def _convert_staged_file(
    source: Path, target: Path, relative: str, *, do_convert: bool,
) -> tuple[list[ConversionRecord], str, dict[str, int], list[str]]:
    """复制/转换单个文本文件，返回（转换记录、最终文本、残留字符计数、残留位置）。

    ``do_convert=False``（用户要求原样打包）必须**按字节复制**：用
    ``read_text`` + ``write_text`` 会走 Python 的换行解码，把 CRLF 归一成 LF，
    即使没做任何 Unicode 转换也会改变源文件哈希。
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if not do_convert:
        target.write_bytes(source.read_bytes())
        text = source.read_text(encoding="utf-8", errors="replace")
        counts, locations = _scan_remaining(text, relative)
        return [], text, counts, locations

    text = source.read_text(encoding="utf-8", errors="replace")
    records: list[ConversionRecord] = []
    in_verbatim = False
    converted_lines: list[str] = []
    seen: set[tuple[int, str]] = set()
    for line_no, line in enumerate(text.splitlines(keepends=True), start=1):
        if any(f"\\begin{{{env}}}" in line for env in _VERBATIM_ENVS):
            in_verbatim = True
        if in_verbatim:
            converted_lines.append(line)
            if any(f"\\end{{{env}}}" in line for env in _VERBATIM_ENVS):
                in_verbatim = False
            continue
        new_line, repl = convert_text(line)
        for char, replacement in repl:
            if (line_no, char) in seen:
                continue
            seen.add((line_no, char))
            records.append(
                ConversionRecord(
                    file=relative, line=line_no, char=char,
                    codepoint=f"U+{ord(char):04X}", replacement=replacement,
                )
            )
        converted_lines.append(new_line)
    text = "".join(converted_lines)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    counts, locations = _scan_remaining(text, relative)
    return records, text, counts, locations


def _accumulate_remaining(
    counts: dict[str, int],
    locations: list[str],
    acc_chars: dict[str, int],
    acc_locations: list[str],
) -> None:
    """把单个文件的"未转换字符/首现位置"并入总账（去重，位置上限 40）。"""
    for char, count in counts.items():
        acc_chars[char] = acc_chars.get(char, 0) + count
    for item in locations:
        if item not in acc_locations and len(acc_locations) < _MAX_LOCATION_SAMPLES:
            acc_locations.append(item)


def _read_rounds(auxdir: Path) -> int | None:
    """从共享状态文件读上一次构建的轮数；缺失/损坏时返回 None。"""
    try:
        state = json.loads((auxdir / ".pytexmk_refcache.json").read_text(encoding="utf-8"))
        return (state.get("pytexmk") or {}).get("build", {}).get("round")
    except Exception:
        return None


def _build_manifest(
    *,
    project_name: str,
    convert_unicode: bool,
    sanitize: bool,
    conversions: list[ConversionRecord],
    sanitized: list[str],
    remaining_chars: dict[str, int],
    remaining_locations: list[str],
    compat: CompatReport,
    include_bbl: bool,
) -> str:
    """生成包内 ``pytexmk-submission-notes.txt`` 的全文。"""
    lines = _manifest_header(project_name, convert_unicode, sanitize)
    if conversions:
        lines.extend(_conversion_manifest_lines(conversions))
    if sanitized:
        lines.extend(_sanitize_manifest_lines(sanitized))
    if remaining_chars:
        lines.extend(_remaining_manifest_lines(remaining_chars, remaining_locations))
    if not compat.ok:
        lines.extend(_compat_manifest_lines(compat))
    lines.extend(_manifest_checklist(include_bbl))
    return "\n".join(lines) + "\n"


def _manifest_header(
    project_name: str, convert_unicode: bool, sanitize: bool
) -> list[str]:
    """说明文件的前 4 行与空行。"""
    return [
        "# PyTeXMK 投稿包说明",
        f"# 项目: {project_name}",
        f"# 转换 Unicode: {'是' if convert_unicode else '否'}",
        f"# 导言区净化: {'是' if sanitize and convert_unicode else '否'}",
        "",
    ]


def _conversion_manifest_lines(conversions: list[ConversionRecord]) -> list[str]:
    """Unicode → LaTeX 转换清单：先按文件计数，再列逐处记录。"""
    lines = ["## Unicode → LaTeX 转换清单"]
    per_file: dict[str, int] = {}
    for record in conversions:
        per_file[record.file] = per_file.get(record.file, 0) + 1
    for name, count in sorted(per_file.items()):
        lines.append(f"- {name}: {count} 处")
    lines.append("")
    lines.extend(
        f"{record.file}:{record.line}  {record.char} ({record.codepoint}) -> {record.replacement}"
        for record in conversions
    )
    lines.append("")
    return lines


def _sanitize_manifest_lines(sanitized: list[str]) -> list[str]:
    """导言区净化记录。"""
    return ["## 导言区净化", *(f"- {note}" for note in sanitized), ""]


def _remaining_manifest_lines(
    remaining_chars: dict[str, int], remaining_locations: list[str]
) -> list[str]:
    """pdflatex 仍无法处理字符的警告与首次出现位置。"""
    lines = ["## ⚠ 仍无法用 pdflatex 处理的字符（必须手工处理）"]
    for char, count in sorted(remaining_chars.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {char} (U+{ord(char):04X}) × {count}")
    lines.extend(
        [
            "",
            "首次出现位置：",
            *(f"- {item}" for item in remaining_locations),
            "",
            "中文/日文/俄文等非拉丁正文需要 ctex/xeCJK/babel 等方案；",
            "期刊只收 pdflatex 时需改为英文稿或与编辑确认。",
            "",
        ]
    )
    return lines


def _compat_manifest_lines(compat: CompatReport) -> list[str]:
    """pdflatex 兼容性警告：未转换字符与不兼容宏包。"""
    lines = ["## pdflatex 兼容性警告"]
    for char, count in sorted(compat.unsupported_chars.items(), key=lambda kv: -kv[1]):
        lines.append(f"- 未转换字符 {char} (U+{ord(char):04X}) × {count}")
    for package, reason in compat.incompatible_packages.items():
        lines.append(f"- 不兼容宏包 {package}: {reason}")
    lines.append("")
    return lines


def _manifest_checklist(include_bbl: bool) -> list[str]:
    """提交前检查清单；是否附 ``.bbl`` 决定参考文献由谁编译。"""
    reference_line = (
        "- [ ] 若包内含 .bbl，不要删除或重命名；参考文献以 .bbl 为准"
        if include_bbl
        else "- [ ] 包内未附 .bbl：期刊端需运行 bibtex/biber 后重新编译参考文献"
    )
    return [
        "## 提交前检查清单",
        "- [ ] 在期刊系统允许的 pdflatex 版本上完整编译一次",
        "- [ ] 确认图片路径/文件名大小写与包内一致",
        reference_line,
        "- [ ] 检查版权/基金信息是否随投稿系统要求单独填写",
        "",
    ]


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
    """把候选文件转换并写入 staging，同时累计说明文件所需的统计。

    原先这些状态散落在 ``build_pack`` 的局部变量里，导致函数同时负责候选过滤、
    Unicode 转换、导言区净化和 .bbl/.bib 补充；拆出来后每个分支只做一件事。
    """

    root: Path
    staging: Path
    convert_unicode: bool
    sanitize: bool
    conversions: list[ConversionRecord] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    sanitized: list[str] = field(default_factory=list)
    remaining_chars: dict[str, int] = field(default_factory=dict)
    remaining_locations: list[str] = field(default_factory=list)

    def stage_candidate(self, source: Path) -> None:
        """按后缀处理一个 ``.fls``/fallback 候选。"""
        try:
            relative = source.relative_to(self.root)
        except ValueError:
            return
        suffix = source.suffix.lower()

        target = self.staging / relative
        counts: dict[str, int] = {}
        locations: list[str] = []
        if suffix == ".tex":
            counts, locations = self._stage_tex(source, target, relative.as_posix())
        elif suffix == ".bbl" and self.convert_unicode:
            counts, locations = self._stage_text(source, target, relative.as_posix())
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.copy(target, preserve_metadata=True)
        if suffix in {".tex", ".bbl"}:
            _accumulate_remaining(counts, locations, self.remaining_chars, self.remaining_locations)
        self.staged.append(relative.as_posix())

    def _stage_tex(self, source: Path, target: Path, relative: str) -> tuple[dict[str, int], list[str]]:
        """转换 TeX 文件，并按需净化导言区。"""
        records, text, counts, locations = _convert_staged_file(
            source, target, relative, do_convert=self.convert_unicode
        )
        self.conversions.extend(records)
        if not (self.sanitize and self.convert_unicode):
            return counts, locations

        cleaned, notes = sanitize_preamble(text)
        if not notes:
            return counts, locations
        self.sanitized.extend(f"{relative}: {note}" for note in notes)
        target.write_text(cleaned, encoding="utf-8")
        return _scan_remaining(cleaned, relative)

    def _stage_text(self, source: Path, target: Path, relative: str) -> tuple[dict[str, int], list[str]]:
        """转换 .bbl 等纯文本文件，并记录转换清单。"""
        records, _text, counts, locations = _convert_staged_file(
            source, target, relative, do_convert=True
        )
        self.conversions.extend(records)
        return counts, locations

    def stage_bbl(self, auxdir: Path, build_name: str, project_name: str) -> None:
        """补入与源主文件同名的 .bbl；已有同名文件时不重复。"""
        bbl = auxdir / f"{build_name}.bbl"
        target_name = Path(f"{project_name}.bbl").as_posix()
        if not bbl.exists() or target_name in {Path(n).as_posix() for n in self.staged}:
            return

        target = self.staging / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.convert_unicode:
            counts, locations = self._stage_text(bbl, target, target_name)
            _accumulate_remaining(counts, locations, self.remaining_chars, self.remaining_locations)
        else:
            bbl.copy(target, preserve_metadata=True)
        self.staged.append(target_name)

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
    convert_unicode: bool = True,
    include_bbl: bool = False,
    sanitize: bool = True,
    reproducible: bool = True,
) -> PackResult:
    """生成投稿 zip；``convert_unicode`` 时输出 pdflatex 可编译的转换副本。

    ``include_bbl=False``（默认）只带源 ``.bib``；期刊明确要求预编译好的
    ``.bbl`` 时由配置层打开。
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
    candidates = _fls_files(root, fls) if fls.exists() else _fallback_files(root)
    if not candidates:
        candidates = _fallback_files(root)

    compat = scan_compat(root, project_name)
    stager = _SubmissionStager(
        root=root,
        staging=staging,
        convert_unicode=convert_unicode,
        sanitize=sanitize,
    )

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
        if include_bbl:
            stager.stage_bbl(auxdir, build_name, project_name)
        stager.stage_bib(project_name)

        manifest = _build_manifest(
            project_name=project_name,
            convert_unicode=convert_unicode,
            sanitize=sanitize,
            conversions=stager.conversions,
            sanitized=stager.sanitized,
            remaining_chars=stager.remaining_chars,
            remaining_locations=stager.remaining_locations,
            compat=compat,
            include_bbl=include_bbl,
        )
        (staging / "pytexmk-submission-notes.txt").write_text(manifest, encoding="utf-8")
        stager.staged.append("pytexmk-submission-notes.txt")

        pdf_path = outdir / f"{build_name}.pdf"
        pages, pdf_bytes = _pdf_summary(pdf_path)

        submit = Path(submit_dir)
        if not submit.is_absolute():
            submit = root / submit
        submit.mkdir(parents=True, exist_ok=True)
        zip_path = submit / f"{project_name}-submission.zip"
        _write_zip(staging, stager.staged, zip_path, reproducible=reproducible)

        with zip_path.open("rb") as fh:
            digest = hashlib.file_digest(fh, "sha256").hexdigest()
        rounds = _read_rounds(auxdir)

        return PackResult(
            zip_path=zip_path,
            files=sorted(set(stager.staged)),
            conversions=stager.conversions,
            compat=compat,
            pdf_pages=pages,
            pdf_bytes=pdf_bytes,
            sha256=digest,
            rounds=rounds,
            remaining_chars=stager.remaining_chars,
            remaining_locations=stager.remaining_locations,
            sanitized=stager.sanitized,
        )
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
