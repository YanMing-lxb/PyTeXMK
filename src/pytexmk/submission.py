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
   连同转换后的 ``.bbl`` 打成 zip，并给出 PDF 页数/体积/编译轮数摘要。
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("submission")

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
    #: 在临时目录里跑 pdflatex 的验证结果
    verify_ok: bool | None = None
    verify_tail: list[str] = field(default_factory=list)


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
    match = re.search(r"(?<!\\)%", line)
    return line[: match.start()] if match else line


def _package_names(text: str) -> set[str]:
    """取出文档加载的所有宏包名（支持一行多个、``\\RequirePackage``）。"""
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
        for name in _package_names(text):
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
                for name in bad:
                    notes.append(f"注释不兼容宏包 \\usepackage{{{name}}}")
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
        if doc:
            preamble = preamble[: doc.end()] + "\n" + block + preamble[doc.end():]
        else:
            preamble = block + preamble

    return preamble + body, notes


def _fls_files(root: Path, fls: Path) -> list[Path]:
    """从 .fls 的 INPUT 行收集依赖（只保留项目内、且非辅助产物）。"""
    files: list[Path] = []
    seen: set[str] = set()
    try:
        lines = fls.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return files
    volatile = {".aux", ".log", ".out", ".toc", ".fls", ".xdv", ".synctex.gz", ".bbl",
                ".nlo", ".nls", ".glo", ".gls", ".ilg", ".ind", ".idx"}
    for line in lines:
        if not line.startswith("INPUT "):
            continue
        raw = line[len("INPUT "):].strip()
        path = Path(raw)
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if relative.parts and relative.parts[0] in {"Build", "Auxiliary", "Submission", ".git"}:
            continue
        key = relative.as_posix()
        if key in seen or resolved.suffix.lower() in volatile:
            continue
        seen.add(key)
        if resolved.is_file():
            files.append(resolved)
    return files


def _fallback_files(root: Path) -> list[Path]:
    """没有 .fls 时的兜底：按常见后缀收集项目文件。"""
    suffixes = {".tex", ".bib", ".bst", ".cls", ".sty", ".def", ".clo", ".cfg", ".ist",
                ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".tikz", ".bbx", ".cbx"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        rel = path.relative_to(root)
        if any(p.startswith(".") or p in {"Build", "Auxiliary", "Submission"} for p in rel.parts[:-1]):
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
    except Exception:  # noqa: BLE001
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
    """复制/转换单个文本文件，返回（转换记录、最终文本、残留字符计数、残留位置）。"""
    text = source.read_text(encoding="utf-8", errors="replace")
    records: list[ConversionRecord] = []
    notes: list[str] = []
    if do_convert:
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
        notes.append(relative)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    counts, locations = _scan_remaining(text, relative)
    return records, text, counts, locations


def _verify_pdflatex(staging: Path, project_name: str, timeout: int = 240) -> tuple[bool | None, list[str]]:
    """在 staging 里真跑一次 pdflatex；引擎不存在时返回 (None, [])。"""
    engine = shutil.which("pdflatex")
    if not engine:
        return None, ["未找到 pdflatex，跳过编译验证"]
    try:
        proc = subprocess.run(  # noqa: S603 - 固定命令，无用户可控 shell
            [engine, "-interaction=nonstopmode", "-halt-on-error", f"{project_name}.tex"],
            cwd=staging,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, [f"pdflatex 运行失败: {exc}"]
    output = (proc.stdout or "") + (proc.stderr or "")
    tail = [line for line in output.splitlines() if line.strip()][-12:]
    return proc.returncode == 0, tail


def build_pack(
    root: str | Path,
    project_name: str,
    outdir: str | Path,
    auxdir: str | Path,
    *,
    pdf_name: str | None = None,
    submit_dir: str | Path = "./Submission",
    convert_unicode: bool = True,
    include_bbl: bool = True,
    include_bib: bool = False,
    sanitize: bool = True,
    verify: bool = False,
    reproducible: bool = True,
) -> PackResult:
    """生成投稿 zip；``convert_unicode`` 时输出 pdflatex 可编译的转换副本。"""
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
    conversions: list[ConversionRecord] = []
    staged: list[str] = []
    sanitized: list[str] = []
    remaining_chars: dict[str, int] = {}
    remaining_locations: list[str] = []

    try:
        for source in sorted(set(candidates)):
            try:
                relative = source.relative_to(root)
            except ValueError:
                continue
            target = staging / relative
            suffix = source.suffix.lower()
            if suffix == ".bib" and not include_bib:
                continue
            if suffix == ".tex":
                records, text, counts, locations = _convert_staged_file(
                    source, target, relative.as_posix(), do_convert=convert_unicode
                )
                if sanitize and convert_unicode:
                    cleaned, notes = sanitize_preamble(text)
                    if notes:
                        sanitized.extend(f"{relative.as_posix()}: {note}" for note in notes)
                        target.write_text(cleaned, encoding="utf-8")
                        text = cleaned
                        counts, locations = _scan_remaining(text, relative.as_posix())
                conversions.extend(records)
            elif suffix == ".bbl" and convert_unicode:
                records, text, counts, locations = _convert_staged_file(
                    source, target, relative.as_posix(), do_convert=True
                )
                conversions.extend(records)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                counts, locations = {}, []
            if suffix in {".tex", ".bbl"}:
                for char, count in counts.items():
                    remaining_chars[char] = remaining_chars.get(char, 0) + count
                for item in locations:
                    if item not in remaining_locations and len(remaining_locations) < 40:
                        remaining_locations.append(item)
            staged.append(relative.as_posix())

        if include_bbl:
            bbl = auxdir / f"{build_name}.bbl"
            # 投稿系统会用 main.tex 重新编译，bbl 必须落成 <源主文件>.bbl，
            # 不能沿用 --jobname 的输出名，否则 journal 端会提示缺少 .bbl。
            bbl_target_name = f"{project_name}.bbl"
            if bbl.exists() and bbl_target_name not in {Path(n).name for n in staged}:
                target = staging / bbl_target_name
                if convert_unicode:
                    records, _text, counts, locations = _convert_staged_file(
                        bbl, target, bbl_target_name, do_convert=True
                    )
                    conversions.extend(records)
                    for char, count in counts.items():
                        remaining_chars[char] = remaining_chars.get(char, 0) + count
                    for item in locations:
                        if item not in remaining_locations and len(remaining_locations) < 40:
                            remaining_locations.append(item)
                else:
                    shutil.copy2(bbl, target)
                staged.append(bbl_target_name)

        if include_bib:
            bib = root / f"{project_name}.bib"
            if bib.exists():
                target = staging / f"{project_name}.bib"
                shutil.copy2(bib, target)
                staged.append(f"{project_name}.bib")

        verify_ok: bool | None = None
        verify_tail: list[str] = []
        if verify and convert_unicode:
            verify_ok, verify_tail = _verify_pdflatex(staging, project_name)

        manifest_lines = [
            "# PyTeXMK 投稿包说明",
            f"# 项目: {project_name}",
            f"# 转换 Unicode: {'是' if convert_unicode else '否'}",
            f"# 导言区净化: {'是' if sanitize and convert_unicode else '否'}",
            "",
        ]

        if conversions:
            manifest_lines.append("## Unicode → LaTeX 转换清单")
            per_file: dict[str, int] = {}
            for record in conversions:
                per_file[record.file] = per_file.get(record.file, 0) + 1
            for name, count in sorted(per_file.items()):
                manifest_lines.append(f"- {name}: {count} 处")
            manifest_lines.append("")
            for record in conversions:
                manifest_lines.append(
                    f"{record.file}:{record.line}  {record.char} ({record.codepoint}) -> {record.replacement}"
                )
            manifest_lines.append("")

        if sanitized:
            manifest_lines.append("## 导言区净化")
            for note in sanitized:
                manifest_lines.append(f"- {note}")
            manifest_lines.append("")

        if remaining_chars:
            manifest_lines.append("## ⚠ 仍无法用 pdflatex 处理的字符（必须手工处理）")
            for char, count in sorted(remaining_chars.items(), key=lambda kv: -kv[1]):
                manifest_lines.append(f"- {char} (U+{ord(char):04X}) × {count}")
            manifest_lines.append("")
            manifest_lines.append("首次出现位置：")
            manifest_lines.extend(f"- {item}" for item in remaining_locations)
            manifest_lines.append("")
            manifest_lines.append("中文/日文/俄文等非拉丁正文需要 ctex/xeCJK/babel 等方案；")
            manifest_lines.append("期刊只收 pdflatex 时需改为英文稿或与编辑确认。")
            manifest_lines.append("")

        if not compat.ok:
            manifest_lines.append("## pdflatex 兼容性警告")
            for char, count in sorted(compat.unsupported_chars.items(), key=lambda kv: -kv[1]):
                manifest_lines.append(f"- 未转换字符 {char} (U+{ord(char):04X}) × {count}")
            for package, reason in compat.incompatible_packages.items():
                manifest_lines.append(f"- 不兼容宏包 {package}: {reason}")
            manifest_lines.append("")

        if verify and convert_unicode:
            manifest_lines.append("## pdflatex 编译验证")
            if verify_ok is None:
                manifest_lines.append("- 未找到 pdflatex，未验证")
            elif verify_ok:
                manifest_lines.append("- 通过：pytexmk 在临时目录用 pdflatex 编译成功")
            else:
                manifest_lines.append("- 失败：请按下面的日志尾部修复（常见原因是缺宏包/缺字体/中文正文）")
                manifest_lines.extend(f"  {line}" for line in verify_tail)
            manifest_lines.append("")

        manifest_lines.append("## 提交前检查清单")
        manifest_lines.append("- [ ] 在期刊系统允许的 pdflatex 版本上完整编译一次")
        manifest_lines.append("- [ ] 确认图片路径/文件名大小写与包内一致")
        manifest_lines.append("- [ ] 若包内含 .bbl，不要删除或重命名；参考文献以 .bbl 为准")
        manifest_lines.append("- [ ] 检查版权/基金信息是否随投稿系统要求单独填写")
        manifest_lines.append("")

        manifest = "\n".join(manifest_lines) + "\n"
        (staging / "pytexmk-submission-notes.txt").write_text(manifest, encoding="utf-8")
        staged.append("pytexmk-submission-notes.txt")

        pdf_path = Path(outdir) / f"{build_name}.pdf"
        pages, pdf_bytes = _pdf_summary(pdf_path)

        submit = Path(submit_dir)
        if not submit.is_absolute():
            submit = root / submit
        submit.mkdir(parents=True, exist_ok=True)
        zip_path = submit / f"{project_name}-submission.zip"
        tmp_zip = zip_path.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name in sorted(set(staged)):
                    path = staging / name
                    info = zipfile.ZipInfo(name)
                    if reproducible:
                        info.date_time = (1980, 1, 1, 0, 0, 0)  # 固定时间戳，便于复现
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    zf.writestr(info, path.read_bytes())
            tmp_zip.replace(zip_path)
        finally:
            tmp_zip.unlink(missing_ok=True)

        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        rounds = None
        try:
            import json

            state = json.loads((auxdir / ".pytexmk_refcache.json").read_text(encoding="utf-8"))
            rounds = (state.get("pytexmk") or {}).get("build", {}).get("round")
        except Exception:  # noqa: BLE001
            rounds = None

        return PackResult(
            zip_path=zip_path,
            files=sorted(set(staged)),
            conversions=conversions,
            compat=compat,
            pdf_pages=pages,
            pdf_bytes=pdf_bytes,
            sha256=digest,
            rounds=rounds,
            remaining_chars=remaining_chars,
            remaining_locations=remaining_locations,
            sanitized=sanitized,
            verify_ok=verify_ok,
            verify_tail=verify_tail,
        )
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
