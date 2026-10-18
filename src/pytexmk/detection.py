"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-29 15:43:26 +0800
LastEditTime : 2025-05-15 18:37:17 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/detection.py
Description  :
 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【6 维编译状态检测的布尔/次数计算 + 辅助文件快照读取】。
  具体职责：
    1. 6 维编译状态检测的布尔/次数计算：bib / idx / toc / aux / out / log。
    2. 辅助文件快照读取 prepare_LaTeX_output_files / prepare_aux_out_snapshots。
  调用依赖关系拓扑：
    compile.CompileLaTeX 实例化 CompilationDetector 持有引用；
    compile_engine.RUN 通过 compile_model.detector.* 调用检测方法。
  下游依赖：
    file_ops / logger / timing / Path / language。
"""

import hashlib
import locale
import logging
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from pytexmk.language import set_language

_ = set_language("detection")


class DetectionResult(NamedTuple):
    """run_full_detection 的一站式返回值。

    原先返回 6 元组，调用方靠位置解包，新增一个维度就要同步改所有解包点；
    这里改用具名元组：仍是真 tuple（可解包、可与 tuple 比较、零额外开销），
    但调用方可以按名字取值，IDE 与类型检查也能给出提示。
    """

    dims: dict  # 6 维检测位的取值
    latex_compilation_times: int  # 后续还需编译 LaTeX 的次数
    bib_engine: str | None  # 需要运行的参考文献引擎
    index_run_cmds: list  # 需要运行的索引命令
    latex_compilation_times_bib: int  # 参考文献后还需编译的次数
    log_signature: tuple[str, ...]  # 日志签名（用于停滞检测）


class BibEngine(StrEnum):
    """参考文献引擎名。

    过去 bib_engine 在双处用裸字符串 "biber" / "bibtex" 赋值，拼错只能等运行时
    静默走到错误分支；改成 StrEnum 后拼写错误在导入期即报错，且因为继承 str，
    日志输出、`==` 比较、把值传给命令行（argv 列表）时仍与旧字符串完全等价。
    """

    BIBER = "biber"
    BIBTEX = "bibtex"


@dataclass(frozen=True, slots=True)
class IndexRule:
    """索引系统注册表的一条规则（glossaries / nomencl / makeidx）。

    原先用 dict 存放三个 callable，取值靠 `rule["trigger"](...)` 这类字符串下标，
    键名拼错、少写一个键都只有在运行到那条分支时才会暴露；改成不可变 dataclass 后
    键名由属性访问约束，IDE / 类型检查可直接跳转，且 slots 让实例更省内存。
    `discover` 返回 list[IndexSpec]，`cmd_builder` 返回 [显示名, shell 命令]。
    """

    name: str
    trigger: Callable[[str, str], bool]
    discover: Callable[[str, str, str], list[IndexSpec]]
    cmd_builder: Callable[[str, str, str, object], list[str]]


@dataclass(frozen=True, slots=True)
class IndexSpec:
    """索引系统的一套「输入扩展名 / 输出扩展名 / 透传上下文」。"""

    ext_in: str
    ext_out: str
    ctx: object = None


BIBER_PATTERN = re.compile(r"\\abx@aux@refcontext")
BIBTEX_PATTERN = re.compile(r"\\bibdata")

BIBER_BIB_PATTERN = re.compile(r"<bcf:datasource[^>]*>\s*(.*?)\s*</bcf:datasource>")
BIBTEX_BIB_PATTERN = re.compile(r"\\bibdata\{(.*)\}")

# ── bib2gls (glossaries-extra) 检测 ──────────────────────────────
# bib2gls 是 glossaries-extra 的后端，必须配合 biber 使用。
# 它在 .aux 中写 \glsxtr@record 标记、在 .bcf 中写 bcf:glossary 元素。
# 检测到这些标记时，bib 维度的 biber 分支行为不变（都是 times_bib=2），
# 但 idx 维度的快照需纳入 .glg/.gls2 等 bib2gls 输出文件。
BIB2GLS_AUX_PATTERN = re.compile(r"\\glsxtr@record")
BIB2GLS_BCF_PATTERN = re.compile(r"<bcf:glossary", re.IGNORECASE)

# 三种引用命令：Biber / BibTeX / thebibliography
_CITE_PATTERNS = (
    re.compile(r"\\abx@aux@cite{.*?}\{(.*)\}"),  # Biber
    re.compile(r"\\citation\{(.*)\}"),  # BibTeX
    re.compile(r"\\bibcite\{(.*?)\}"),  # thebibliography
)

# ── LaTeX log 中触发额外编译的警告模式 ──────────────────────────────
# 每条为 (包名, 正则)：
#   包名 = None  → 通用警告（LaTeX 核心引擎产生，任何项目都可能出现，始终检查）
#   包名 = str   → 包专属警告（仅当 log 中出现该包时才检查，避免无用扫描）
# 正则按警告出现频率排序，高频通用模式靠前可提前短路返回 True。
RERUN_LOG_PATTERNS: list[tuple[str | None, re.Pattern[str]]] = [
    # ── 通用模式（LaTeX 核心引擎，始终检查）─────────────────────────
    (None, re.compile(r"LaTeX Warning: There were undefined references\.")),
    (None, re.compile(r"LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\.")),
    (None, re.compile(r"LaTeX Warning: Citation .* undefined")),
    (None, re.compile(r"LaTeX Warning: There were multiply-defined labels\.")),
    (None, re.compile(r"Package lastpage Warning: Rerun to get the references right")),
    (None, re.compile(r"Package rerunfilecheck Warning: .* Rerun")),
    # ── 参考文献相关包 ─────────────────────────────────────────────
    ("biblatex", re.compile(r"Package biblatex Warning: Please .* rerun LaTeX", re.IGNORECASE)),
    ("biblatex", re.compile(r"Package biblatex Warning: Please \(re\)run Biber", re.IGNORECASE)),
    # ── 索引与术语表相关包 ──────────────────────────────────────────
    ("glossaries", re.compile(r"Package glossaries Warning: .* rerun", re.IGNORECASE)),
    ("glossaries", re.compile(r"Glossary entries? have changed\.? .* rerun LaTeX", re.IGNORECASE)),
    ("glossaries", re.compile(r"Acronyms entries have changed", re.IGNORECASE)),
    ("nomencl", re.compile(r"Please \(re\)run LaTeX to get the nomenclature entries right", re.IGNORECASE)),
    ("makeidx", re.compile(r"Please \(re\)run LaTeX to get the index entries right", re.IGNORECASE)),
    # 独立 acro / acronym 包（它们不使用 glossaries，各自有 rerun 提示）
    ("acro", re.compile(r"Package acro Warning: .* rerun", re.IGNORECASE)),
    ("acro", re.compile(r"Package acro Warning: .* entries? (have )?changed", re.IGNORECASE)),
    ("acronym", re.compile(r"Package acronym Warning: .* rerun", re.IGNORECASE)),
    # ── 目录与书签相关包 ─────────────────────────────────────────────
    ("hyperref", re.compile(r"Package hyperref Warning: .* rerun", re.IGNORECASE)),
    ("tocloft", re.compile(r"Package tocloft Warning: .* rerun", re.IGNORECASE)),
    ("titlesec", re.compile(r"Package titlesec Warning: .* rerun", re.IGNORECASE)),
    ("fancyhdr", re.compile(r"Package fancyhdr Warning: .* rerun", re.IGNORECASE)),
    # ── 其他常见需要 rerun 的包 ─────────────────────────────────────
    ("cleveref", re.compile(r"Package cleveref Warning: .* rerun", re.IGNORECASE)),
    ("enumitem", re.compile(r"Package enumitem Warning: .* rerun", re.IGNORECASE)),
    ("float", re.compile(r"Package float Warning: .* rerun", re.IGNORECASE)),
    ("tablefootnote", re.compile(r"Package tablefootnote Warning: .* rerun", re.IGNORECASE)),
]

# 具体未定义引用/引用的条目，用于日志签名差分：
# 签名不仅记录“命中了哪类警告”，还记录“具体是哪个引用键未解析”，
# 使跨轮差分能识别警告集合的实质变化，而不是仅凭“存在与否”判断。
_UNDEFINED_REF_PATTERN = re.compile(r"LaTeX Warning: (?:Reference|Citation) `([^']+)'")

# ── 永久性信号分类 ──────────────────────────────────────────────────────
# 只取决于源文件、再编译也消不掉的信号。它们只能靠改源码解决，绝不能拿来
# 当作"还需要再编一轮"的理由 —— 否则一个写错的 \cref 就能让收敛循环空转到
# 安全上限。这是省掉"确认轮"的关键依据（见 classify_signals）。
_PERMANENT_SIGNAL_PATTERNS = frozenset(
    {
        r"LaTeX Warning: There were undefined references\.",
        r"LaTeX Warning: Citation .* undefined",
        r"LaTeX Warning: There were multiply-defined labels\.",
    }
)

#: 由上面的正则文本直接推导出的签名 token 集合（``pat{idx}`` 形式）。
#: 用推导而不是手写下标，避免 RERUN_LOG_PATTERNS 顺序调整时分类错位。
_PERMANENT_PATTERN_TOKENS: frozenset[str] = frozenset(
    f"pat{idx}"
    for idx, (_pkg, _pattern) in enumerate(RERUN_LOG_PATTERNS)
    if _pattern.pattern in _PERMANENT_SIGNAL_PATTERNS
)

# ── 索引系统注册表（数据驱动） ──────────────────────────────────────────
# 三条使用方（_index_aux_content_get / index_judgment / run_full_detection）
# 统一遍历注册表，不包含任何 "if rule['name'] == ..." 特殊分支。
#
# 每条规则必须提供三个 callable（无可选字段，见下方 IndexRule / IndexSpec）：
#   trigger(proj, aux_content) -> bool
#     决定该索引系统是否参与本项目的编译流程。
#     基于文件扩展名（nomencl/makeidx）或 .aux 内容（glossaries）都可以。
#
#   discover(proj, aux_content, log_content) -> list[IndexSpec]
#     返回该索引系统要处理的每一套 (输入扩展名, 输出扩展名, 命令生成上下文)。
#     glossaries 因为一个项目可能有多个 glossary 类型（main/acronym/symbols/自定义），
#     所以 discover 返回多个 IndexSpec；其余系统固定返回 1 个。
#     ctx 是传递给 cmd_builder 的透传参数，类型由各规则自己定义。
#
#   cmd_builder(proj, ext_o, ext_i, ctx) -> list
#     返回两条元素：[display_name, shell_command_string]。
#
# 新增一种索引系统时，只需在 _INDEX_REGISTRY 里追加一条 IndexRule，
# 三个 callable 都在 registry 内部完成行为封装，使用方零修改。
#   这样所有 glossary 类型（含自定义）都能自动发现。

# glossaries 的 \\@newglossary 行有两种格式：
#   带可选方括号参数：\\@newglossary[alg2]{grafik}{acr2}{acn2}{Grafikpakete}
#   不带方括号参数：  \\@newglossary{main}{gls}{glo}{Glossary}
# 方括号内常写 .alg（glossary log）的扩展名，同时也可以携带 backend 标记（xindy）。
# 使用命名分组：discover 里按语义取值（match.group("glo")），
# 而不是记住「第 5 个组是 glo、第 4 个组是 gls」这类位置约定。
_NGLOSSARY_PATTERN = re.compile(
    r"\\@newglossary(?:\[(?P<opts>[^\]]*)\])?"
    r"\{(?P<name>[^{}]+)\}\{(?P<glg>[^{}]+)\}\{(?P<gls>[^{}]+)\}\{(?P<glo>[^{}]+)\}"
)

# xindy 后端的 .xdy 文件标记：当 \\@newglossary 方括号参数中含 "xindy" 字样、
# 或 .aux 中出现 \\xindyLoadHyphFile / \\XindySetup 等宏时，说明 glossaries 使用 xindy 后端。
_XINDY_IN_BRACKET = re.compile(r"xindy", re.IGNORECASE)
_XINDY_AUX_MACRO = re.compile(r"\\xindy|\\Xindy", re.IGNORECASE)


def _detect_xindy_language(log_content: str) -> str:
    """从 LaTeX .log 推断 xindy 语言参数，默认 english。

    推断优先级：
      1. .log 中 polyglossia 包加载行 → 语言名
      2. .log 中 babel 包最后一次加载行 → 语言名
      3. 都没有 → "english"
    """
    # polyglossia: "Package polyglossia Info: ... Setting default language to English."
    m = re.search(
        r"Setting default language to ([A-Za-z]+(?: [A-Za-z]+)*)\.",
        log_content,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).split()[0].lower()

    # babel: "Package babel Info: Using the language definitions for `english'."
    matches = list(
        re.finditer(
            r"for `([A-Za-z]+)'",
            log_content,
        )
    )
    if matches:
        # babel 可能加载多语言，取最后一次（通常是主语言）
        return matches[-1].group(1).lower()

    return "english"


def _resolve_glossaries_backend(
    proj: str, bracket_arg: str | None, aux_content: str, log_content: str
) -> dict[str, str]:
    """为单个 glossary 类型判断后端（makeindex vs xindy）并返回参数。

    返回 dict 含：
      backend : "makeindex" | "xindy"
      lang    : （仅 xindy）语言参数
    判断条件（任一命中即 xindy）：
      1. .xdy 文件存在
      2. \\@newglossary 方括号参数含 "xindy"
      3. .aux 中有 xindy 专属宏
    """
    is_xindy = Path(f"{proj}.xdy").exists()
    if not is_xindy and bracket_arg and _XINDY_IN_BRACKET.search(bracket_arg):
        is_xindy = True
    if not is_xindy and _XINDY_AUX_MACRO.search(aux_content):
        is_xindy = True

    if is_xindy:
        return {"backend": "xindy", "lang": _detect_xindy_language(log_content)}
    return {"backend": "makeindex", "lang": "english"}


# ── Registry 辅助函数（各规则的 trigger / discover / cmd_builder 工厂） ────


def _glossaries_trigger(proj: str, aux_content: str) -> bool:
    """glossaries 触发条件：.aux 中存在 \\@newglossary 行。"""
    return bool(_NGLOSSARY_PATTERN.search(aux_content))


def _glossaries_discover(proj: str, aux_content: str, log_content: str) -> list[IndexSpec]:
    """发现 .aux 中所有 glossary 类型（可能多套：main / acronym / 自定义 ...）。

    glossaries v4+ 的 \\@newglossary 行格式：
        \\@newglossary[alg2]{grafik}{acr2}{acn2}
                      ↑opt bracket  ↑name  ↑glg  ↑gls  ↑glo
                      (可选)       类型名 log  输出  输入

    返回 list[IndexSpec]，ext_in = glo_ext，ext_out = gls_ext。
    ctx 是 cmd_builder 所需的 backend dict + 类型名称。
    """
    results: list[IndexSpec] = []
    for match in _NGLOSSARY_PATTERN.finditer(aux_content):
        bracket_arg = match.group("opts")
        name = match.group("name")
        glg = match.group("glg")
        backend = _resolve_glossaries_backend(proj, bracket_arg, aux_content, log_content)
        results.append(
            IndexSpec(
                ext_in=match.group("glo"),
                ext_out=match.group("gls"),
                ctx={
                    "backend": backend,
                    "name": name,
                    "glg": glg,  # cmd_builder 可能需要（xindy 的 .xdy 等）
                },
            )
        )
    return results


def _index_glossaries_cmd_builder_v2(proj: str, ext_o: str, ext_i: str, ctx: dict) -> list[str]:
    """glossaries v2：ctx 里携带 backend + glossary 名称 + glg。

    参数语义（统一）：
        ext_o = gls_out  (输出扩展名：gls / acr / 自定义)
        ext_i = glo_in   (输入扩展名：glo / acn / 自定义)
        ctx["glg"]       = log 扩展名  (glg / alg / 自定义)
    """
    backend = ctx["backend"]
    _name = ctx["name"]
    _glg = ctx.get("glg", "")
    if backend["backend"] == "xindy":
        return [
            f"glossaries ({_name}, xindy)",
            (f"xindy -L {backend['lang']} -I xindy -M {proj}.xdy -t {proj}.{_glg} -o {proj}.{ext_o} {proj}.{ext_i}"),
        ]
    # makeindex 后端：
    #   -s proj.ist （glossaries 自动生成的样式文件）
    #   -t proj.glg  （glossary log，有助于调试）
    #   -o proj.gls  （输出）
    #   proj.glo     （输入，注意：makeindex 不写 -i 直接接文件名）
    return [
        f"glossaries {_name}",
        f"makeindex -s {proj}.ist -t {proj}.{_glg} -o {proj}.{ext_o} {proj}.{ext_i}",
    ]


def _make_extension_trigger(extensions: list[str]):
    """工厂：基于文件扩展名存在性的 trigger。用于 nomencl / makeidx。"""

    def trigger(proj: str, _aux_content: str) -> bool:
        return any(Path(f"{proj}{ext}").exists() for ext in extensions)

    return trigger


def _make_fixed_discover(ext_i: str, ext_o: str):
    """工厂：固定 ext_i / ext_o 的 discover。nomencl / makeidx 各只有一套。"""

    def discover(_proj: str, _aux_content: str, _log_content: str) -> list[IndexSpec]:
        return [IndexSpec(ext_in=ext_i, ext_out=ext_o)]

    return discover


def _make_fixed_cmd_builder(display: str, cmd_template: str):
    """工厂：固定模板的 cmd_builder。忽略 ctx。"""

    def cmd_builder(proj: str, _ext_o: str, _ext_i: str, _ctx: object) -> list[str]:
        return [display, cmd_template.format(proj=proj)]

    return cmd_builder


# ── 索引系统注册表（数据驱动） ─────────────────────────────────────────

_INDEX_REGISTRY: tuple[IndexRule, ...] = (
    IndexRule(
        name="glossaries",
        trigger=_glossaries_trigger,
        discover=_glossaries_discover,
        cmd_builder=_index_glossaries_cmd_builder_v2,
    ),
    IndexRule(
        name="nomencl",
        trigger=_make_extension_trigger([".nlo"]),
        discover=_make_fixed_discover("nlo", "nls"),
        cmd_builder=_make_fixed_cmd_builder("nomencl", "makeindex -s nomencl.ist -o {proj}.nls {proj}.nlo"),
    ),
    IndexRule(
        name="makeidx",
        trigger=_make_extension_trigger([".idx"]),
        discover=_make_fixed_discover("idx", "ind"),
        cmd_builder=_make_fixed_cmd_builder("makeidx", "makeindex {proj}.idx"),
    ),
)


def _read_file_content(path: str | Path) -> str:
    """容错读取 LaTeX 辅助文件内容，避免因编码不同导致编译检测崩溃。

    中文字典类文档（如 CTeX/cct 的 GBK 方案）生成的 .aux/.toc/.out 等
    辅助文件常为本地编码（Windows 中文环境为 cp936），并非 UTF-8。此处
    优先严格按 UTF-8 解码，失败则退回本地编码，最后再以 errors="replace"
    兜底，保证检测阶段的快照与重读永不因解码异常中断。

    本地编码取自 3.15 新增的标准库函数 ``locale.getencoding()``（取代
    ``locale.getpreferredencoding(False)``）：后者属于新的软弃用模块 locale，
    而 getencoding() 只回答「本地编码是什么」这一件事，不经过 GUI 首选项探测，
    也不会在 3.15 下触发 DeprecationWarning。
    """
    data = Path(path).read_bytes()
    local_encoding = locale.getencoding()
    # 本地编码就是 UTF-8（POSIX 默认 / UTF-8 模式）时无需重复尝试
    for enc in dict.fromkeys(("utf-8", local_encoding)):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _stable_digest(content: str) -> bytes:
    """把辅助文件内容压成固定长度摘要，供 state_fingerprint 比较。

    直接拼接全文会让指纹长度随项目规模增长，且比较时仍需逐字节扫描；
    这里只取 SHA-256，既保证跨轮比较准确，也把指纹长度固定下来。
    """
    return hashlib.sha256(content.encode("utf-8", errors="replace")).digest()


def _count_citations(file_name):
    counter = defaultdict(int)

    aux_content = _read_file_content(file_name)
    for pattern in _CITE_PATTERNS:
        for match in pattern.finditer(aux_content):
            counter[match.group(1)] += 1
    return counter


_PACKAGE_MATCHER = re.compile(r"Package ([a-zA-Z][a-zA-Z0-9-]*)", re.IGNORECASE)


def _extract_loaded_packages(log_content: str) -> set[str]:
    """从 LaTeX .log 中提取实际加载过的包名集合（小写归一化）。

    原理：LaTeX 在加载每个包时都会输出形如
      "Loading package glossaries on input line 42."
    的日志行，而包专属警告也以 "Package <名> Warning:" 开头。
    这里用宽松正则扫描所有出现过的包名片段，然后小写归一化做集合判断。
    """
    return {m.group(1).lower() for m in _PACKAGE_MATCHER.finditer(log_content)}


class CompilationDetector:
    def __init__(
        self,
        project_name,
        compiled_program,
        out_files,
        aux_files,
        outdir,
        auxdir,
        non_quiet,
        MRO,
    ):
        self.logger = logging.getLogger(__name__)

        self.project_name = project_name
        self.compiled_program = compiled_program
        self.out_files = out_files
        self.aux_files = aux_files
        self.auxdir = auxdir
        self.outdir = outdir
        self.non_quiet = non_quiet
        self.MRO = MRO

        self.bib_file = ""
        self.bib_files: list[Path] = []
        self.bib2gls_mode = False  # bib2gls (glossaries-extra) 标记，由 bib_judgment 刷新

    def prepare_LaTeX_output_files(self):
        aux_file_path = Path(f"{self.project_name}.aux")
        if aux_file_path.exists():
            cite_counter = self._generate_citation_counter()
            index_aux_content_dict_old = self._index_aux_content_get()
        else:
            cite_counter = {f"{self.project_name}.aux": defaultdict(int)}
            index_aux_content_dict_old = {}
        toc_file_path = Path(f"{self.project_name}.toc")
        if toc_file_path.exists():
            toc_file = _read_file_content(toc_file_path)
        else:
            toc_file = ""

        return cite_counter, toc_file, index_aux_content_dict_old

    def _generate_citation_counter(self):
        cite_counter = {}
        file_name = f"{self.project_name}.aux"
        main_aux_content = _read_file_content(file_name)
        cite_counter[file_name] = _count_citations(file_name)

        for match in re.finditer(r"\\@input\{(.*.aux)\}", main_aux_content):
            file_name = match.groups()[0]
            try:
                counter = _count_citations(file_name)
            except OSError:
                self.logger.info(_("文件不存在或无法读取,跳过文件: %(args)s") % {"args": file_name})
            else:
                cite_counter[file_name] = counter

        return cite_counter

    def _index_aux_content_get(self):
        """快照阶段：扫描三种索引系统，为命中的系统记录 ext_i（输入文件）旧内容。

        统一语义：快照存 ext_i，检测也比较 ext_i。
        原先 glossaries 分支误读 ext_o（输出文件）已在此修正。
        nomencl/makeidx 原先要求 ext_i 和 ext_o 两文件都存在才快照，
        现在统一改为任一触发扩展名存在即快照（与检测阶段对齐）。
        """
        index_aux_content_dict_old: dict[str, str] = {}

        aux_path = Path(f"{self.project_name}.aux")
        if not aux_path.exists():
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")
            return index_aux_content_dict_old
        main_aux = _read_file_content(aux_path)
        # glossaries 可能需要 .log（xindy language 推断）
        log_content = self._read_aux_like(".log")

        for rule in _INDEX_REGISTRY:
            # bib2gls 下 glossaries 不写 .glo/.xdy，跳过快照采集
            if self.bib2gls_mode and rule.name == "glossaries":
                continue
            if not rule.trigger(self.project_name, main_aux):
                continue
            for spec in rule.discover(self.project_name, main_aux, log_content):
                # 快照只关心 ext_in（输入文件）的旧内容
                infile_path = Path(f"{self.project_name}.{spec.ext_in}")
                if infile_path.exists():
                    index_aux_content_dict_old[infile_path.name] = _read_file_content(infile_path)

        return index_aux_content_dict_old

    def toc_changed_judgment(self, toc_file):
        file_name = Path(self.project_name).with_suffix(".toc")
        return file_name.exists() and _read_file_content(file_name) != toc_file

    def _resolve_bib_files(self, raw: str) -> list[Path]:
        """把 .aux/.bcf 里声明的文献数据名解析成真实存在的 .bib 文件。

        ``\\bibdata{References}`` 只给出不带扩展名的名字（还可能用逗号分隔多个），
        直接 ``Path("References").exists()`` 永远是 False，这正是历史上
        "文献检测一直要求重编译、编译次数冲到上限" 的根因。这里按
        ``<name>.bib`` → ``<name>`` 的顺序逐个探测。
        """
        resolved: list[Path] = []
        for name in str(raw).split(","):
            name = name.strip()
            if not name:
                continue
            for candidate in (Path(f"{name}.bib"), Path(name)):
                if candidate.is_file():
                    resolved.append(candidate)
                    break
        return resolved

    def _bib_output_path(self) -> Path | None:
        """返回当前已存在的 .bbl（先项目根目录，再 auxdir）。"""
        for candidate in self._candidate_paths(".bbl"):
            if candidate.is_file():
                return candidate
        return None

    def _bib_needs_refresh(self) -> bool:
        """.bbl 缺失或比任一 .bib 旧时，说明文献需要重新生成。"""
        bbl_path = self._bib_output_path()
        if bbl_path is None:
            return True
        try:
            bbl_mtime = bbl_path.stat().st_mtime
        except OSError:
            return True
        for bib_path in self.bib_files:
            try:
                if bib_path.stat().st_mtime > bbl_mtime:
                    return True
            except OSError:
                continue
        return False

    def bib_judgment(self, old_cite_counter):
        """判断文献维度需要多少次额外编译。

        返回 ``(bib_engine, latex_compilation_times, target_name_bib)``。
        判断顺序（任何一步判定"已稳定"都会立刻归零，避免无休止重编译）：

            1. 没有文献引擎 → 交给 ``\\bibcite`` 计数比较
            2. 找不到任何 .bib 数据文件 → 归零并告警（bibtex 无法产出 .bbl，
               继续重跑只会把编译次数推到上限）
            3. 引用计数稳定 且 .bbl 存在 且 日志无 "No file *.bbl" /
               "Citation undefined" 且 .bbl 不比 .bib 旧 → 归零
            4. 其余情况 → 需要 2 次（跑一次 bibtex/biber + 重新编译）
        """
        bib_engine = None
        target_name_bib = None
        latex_compilation_times = 0
        self.bib2gls_mode = False  # bib2gls (glossaries-extra) 检测标记
        self.bib_files = []

        aux_file_path = Path(f"{self.project_name}.aux")
        if not aux_file_path.exists():
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")
            return bib_engine, latex_compilation_times, target_name_bib

        aux_content = _read_file_content(aux_file_path)
        match_biber = BIBER_PATTERN.search(aux_content)
        match_bibtex = BIBTEX_PATTERN.search(aux_content)

        if match_biber:
            bcf_file_path = Path(f"{self.project_name}.bcf")
            bcf_content = ""
            if bcf_file_path.exists():
                bcf_content = _read_file_content(bcf_file_path)
                datasources = [
                    item.strip() for item in BIBER_BIB_PATTERN.findall(bcf_content) if item.strip()
                ]
                if datasources:
                    self.bib_file = ",".join(datasources)
                    bib_engine = BibEngine.BIBER

            # bib2gls (glossaries-extra) 检测：
            # .aux 里有 \glsxtr@record 或 .bcf 里有 <bcf:glossary
            # bib2gls 必须配合 biber 使用，所以只在 biber 分支检测。
            # bib2gls 不额外增加 LaTeX 次数（和普通 biber 相同），
            # 它的处理完全由 biber 在同一个 subprocess 里完成。
            if bib_engine is BibEngine.BIBER:
                if BIB2GLS_AUX_PATTERN.search(aux_content):
                    self.bib2gls_mode = True
                elif BIB2GLS_BCF_PATTERN.search(bcf_content):
                    self.bib2gls_mode = True

        elif match_bibtex:
            match_bibtex_bib = BIBTEX_BIB_PATTERN.search(aux_content)
            if match_bibtex_bib:
                self.bib_file = match_bibtex_bib.group(1)
                bib_engine = BibEngine.BIBTEX

        if bib_engine is None:
            # thebibliography 环境：只用 \bibcite 计数判断是否需要再编译一次
            if re.search(r"\\bibcite", aux_content):
                new_cite_counter = self._generate_citation_counter()
                latex_compilation_times = 0 if old_cite_counter == new_cite_counter else 1
            return bib_engine, latex_compilation_times, target_name_bib

        target_name_bib = bib_engine
        self.bib_files = self._resolve_bib_files(self.bib_file)

        new_cite_counter = self._generate_citation_counter()
        citations_stable = old_cite_counter == new_cite_counter
        log_content = self._read_log_content()
        bbl_missing = bool(re.search(rf"No file {re.escape(self.project_name)}\.bbl", log_content))
        cite_undefined = bool(re.search(r"LaTeX Warning: Citation .* undefined", log_content))

        if not self.bib_files:
            # 声明了文献引擎却找不到任何 .bib 数据文件：bibtex/biber 无法产出 .bbl。
            # 此时继续要求额外编译只会把次数推到安全上限，因此归零并由最终报告提示。
            self.logger.warning(
                _("未找到参考文献数据文件(.bib): %(args)s，已跳过 %(engine)s 调用")
                % {"args": self.bib_file or "?", "engine": bib_engine}
            )
            latex_compilation_times = 0
        elif citations_stable and not bbl_missing and not cite_undefined and not self._bib_needs_refresh():
            latex_compilation_times = 0
        else:
            latex_compilation_times = 2

        return bib_engine, latex_compilation_times, target_name_bib

    def _index_changed_judgment(self, index_aux_content_dict_old, index_aux_infile, index_aux_outfile):
        """判断单次索引是否需要重跑。

        规则（顺序很重要）：
            1. 输入文件（.nlo/.glo/.idx）不存在 → 没有可索引内容，返回 False
            2. 输出文件（.nls/.gls/.ind）不存在 → 索引从未生成，需要重跑
            3. 输入内容与快照不同 → 需要重跑
            4. 其余 → 无需重跑

        历史实现把"输出文件缺失"和"输入文件缺失"合并处理，导致输入文件
        尚未生成时也返回 True，使 idx 维度长期非零、循环无法收敛。
        """
        infile_path = Path(index_aux_infile)
        if not infile_path.exists():
            return False
        if not Path(index_aux_outfile).exists():
            return True
        file_content = _read_file_content(infile_path)
        # 用 .get() 而非 dict[key]，避免快照/检测触发条件不一致导致 KeyError
        return index_aux_content_dict_old.get(index_aux_infile, "") != file_content

    def index_judgment(self, index_aux_content_dict_old):
        """检测阶段：统一遍历注册表，为命中的系统决定是否需要重跑索引。"""
        run_index_list_cmd: list[list[str]] = []

        # 一次性读 .aux + .log，供所有规则的 trigger / discover 复用
        main_aux = ""
        aux_path = Path(f"{self.project_name}.aux")
        if aux_path.exists():
            main_aux = _read_file_content(aux_path)
        log_content = ""
        for lp in (
            Path(f"{self.project_name}.log"),
            Path(self.auxdir) / f"{self.project_name}.log",
        ):
            if lp.exists():
                log_content = _read_file_content(lp)
                break

        for rule in _INDEX_REGISTRY:
            # bib2gls 下 glossaries 的条目由 biber 处理，跳过 makeindex/xindy 调用
            if self.bib2gls_mode and rule.name == "glossaries":
                continue
            if not rule.trigger(self.project_name, main_aux):
                continue
            for spec in rule.discover(self.project_name, main_aux, log_content):
                make_index = self._index_changed_judgment(
                    index_aux_content_dict_old,
                    f"{self.project_name}.{spec.ext_in}",
                    f"{self.project_name}.{spec.ext_out}",
                )
                if make_index:
                    run_index_list_cmd.append(
                        rule.cmd_builder(self.project_name, spec.ext_out, spec.ext_in, spec.ctx)
                    )

        return run_index_list_cmd

    def _candidate_paths(self, suffix: str) -> tuple[Path, Path]:
        """辅助文件的候选路径：先当前目录，再 auxdir（LaTeX 的 auxdir/outdir 双写习惯）。"""
        name = f"{self.project_name}{suffix}"
        return Path(name), Path(self.auxdir) / name

    def _read_aux_like(self, suffix: str) -> str:
        """读取 .aux / .out / .log 等辅助文件；全部候选缺失或不可读时返回空串。"""
        for candidate in self._candidate_paths(suffix):
            try:
                if candidate.exists():
                    return _read_file_content(candidate)
            except (OSError, UnicodeDecodeError):
                return ""
        return ""

    def prepare_aux_out_snapshots(self):
        return self._read_aux_like(".aux"), self._read_aux_like(".out")

    @staticmethod
    def _normalize_aux_like(content: str) -> str:
        if not content:
            return ""
        stripped_lines: list[str] = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("%"):
                continue
            comment_idx = -1
            for i, ch in enumerate(line):
                if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                    comment_idx = i
                    break
            if comment_idx >= 0:
                line = line[:comment_idx].strip()
                if not line:
                    continue
            if line in (r"\relax", "\\relax", "\\relax{}"):
                continue
            if re.fullmatch(r"\\bookmarksetup\{.*\}", line):
                continue
            if re.fullmatch(r"\\@outlinefile\s*\{.*\}", line):
                continue
            if re.fullmatch(r"\\gdef\s*\\@abspage@last\{.*\}", line) or re.fullmatch(
                r"\\xdef\s*\\@abspage@last\{.*\}", line
            ):
                continue
            if re.fullmatch(r"\\global\\\@namedef\{ver@.*\}\{.*\}", line):
                continue
            stripped_lines.append(line)
        return "\n".join(stripped_lines)

    def aux_changed_judgment(self, aux_content_old):
        current = self._read_aux_like(".aux")
        return self._normalize_aux_like(current) != self._normalize_aux_like(aux_content_old)

    def out_changed_judgment(self, out_content_old):
        current = self._read_aux_like(".out")
        return self._normalize_aux_like(current) != self._normalize_aux_like(out_content_old)

    def _read_log_content(self, log_path=None) -> str:
        """读取 .log 内容；文件缺失或读取异常时返回空串。"""
        if log_path is None:
            return self._read_aux_like(".log")
        try:
            return _read_file_content(Path(log_path))
        except (OSError, UnicodeDecodeError):
            return ""

    def log_rerun_signature(self, log_path=None) -> tuple[str, ...]:
        """返回本轮 .log 命中的重编译警告签名（去重排序的元组）。

        签名供 compile_engine 跨轮差分：签名相同表示警告集合未发生变化，
        签名不同表示出现了新的 / 消失的警告。仅记录“命中了哪类警告”不足以
        识别实质变化，因此额外纳入具体的未定义引用 / 引用键。

        仅检查两类模式：
          1. 通用模式（包名=None）—— LaTeX 核心引擎产生，任何项目都可能出现
          2. 包专属模式（包名=str）—— 先确认 log 中出现过该包名再匹配正则，
             避免对未加载包做无用扫描
        .log 文件不存在时返回空元组（视作 log 维度未启用，调用方应标 -1）。
        """
        log_content = self._read_log_content(log_path)
        if not log_content:
            return ()

        loaded_pkgs = _extract_loaded_packages(log_content)

        matched: set[str] = set()
        for idx, (pkg_name, pattern) in enumerate(RERUN_LOG_PATTERNS):
            if pkg_name is not None and pkg_name not in loaded_pkgs:
                continue
            if pattern.search(log_content):
                matched.add(f"pat{idx}")
        for match in _UNDEFINED_REF_PATTERN.finditer(log_content):
            matched.add(f"undef:{match.group(1)}")

        return tuple(sorted(matched))

    def log_has_rerun_warnings(self, log_path=None) -> bool:
        """扫描 .log 是否含需要重编译的警告。"""
        return bool(self.log_rerun_signature(log_path))

    def classify_signals(self, log_path=None) -> dict[str, list[str]]:
        """把日志信号分成 ``permanent``（再编译也消不掉）与 ``transient``（有望消除）。

        区分依据是"这条警告是否只取决于源文件本身"：

        * ``permanent`` —— 未定义引用 / 未定义文献引用 / 重复标签 / ``Citation
          ... undefined``。只要源文件不改写，LaTeX 每轮都会原样警告，重编译
          纯粹空转。这类信号**不得**参与"还需再编译几次"的决策。
        * ``transient`` —— 跨轮次引用类警告（``Label(s) may have changed``、
          ``Rerun to get cross-references right``、上一次运行留下的未解析引用
          等）。它们会随 .aux 轮次推进而消失，是"还该不该再编一轮"的正当依据。

        这个分类是省掉"确认轮"的关键：只有当所有变更维度归零、且剩下的是
        permanent 信号时，才能断定"再编译无意义"，而不必真编一轮去看。
        """
        signature = self.log_rerun_signature(log_path)
        if not signature:
            return {"permanent": [], "transient": []}

        permanent: list[str] = []
        transient: list[str] = []
        for token in signature:
            if token.startswith("undef:"):
                permanent.append(token)
                continue
            if token in _PERMANENT_PATTERN_TOKENS:
                permanent.append(token)
            else:
                transient.append(token)
        return {"permanent": sorted(permanent), "transient": sorted(transient)}

    @property
    def has_permanent_signals(self, log_path=None) -> bool:
        """日志中是否存在"再编译也消不掉"的信号。"""
        return bool(self.classify_signals(log_path)["permanent"])

    def residual_warnings(self) -> list[str]:
        """返回当前 .log 中"再编译也无法消除"的警告摘要，供最终报告展示。

        未定义引用 / 未定义文献这类警告只要源文件不改就永远存在，
        它们不是编译流程的问题，但用户需要知道成品 PDF 里可能有 [?]。
        """
        log_content = self._read_log_content()
        if not log_content:
            return []

        messages: list[str] = []
        undefined_refs = sorted({m.group(1) for m in _UNDEFINED_REF_PATTERN.finditer(log_content)})
        if undefined_refs:
            preview = ", ".join(undefined_refs[:5])
            if len(undefined_refs) > 5:
                preview += ", ..."
            messages.append(
                _("未定义的交叉引用 %(count)s 个: %(keys)s")
                % {"count": str(len(undefined_refs)), "keys": preview}
            )
        if re.search(r"LaTeX Warning: Citation .* undefined", log_content):
            messages.append(_("存在未定义的文献引用（.bib 中缺少对应条目）"))
        if re.search(r"LaTeX Warning: There were multiply-defined labels", log_content):
            messages.append(_("存在重复定义的标签"))
        return messages

    def aux_signature(self) -> str:
        """当前 .aux 内容摘要，用于避免同一状态下重复调用 bibtex/biber。

        bibtex/biber 的输入就是 .aux（biber 还看 .bcf），只要 .aux 没变，
        再跑一次得到的 .bbl 完全相同，因此可以直接跳过。
        """
        digest = hashlib.sha256()
        for suffix in (".aux", ".bcf"):
            for candidate in self._candidate_paths(suffix):
                if candidate.is_file():
                    digest.update(suffix.encode("utf-8"))
                    digest.update(_stable_digest(_read_file_content(candidate)))
                    break
        return digest.hexdigest()

    def index_signature(self) -> str:
        """当前索引输入文件的内容摘要，用于避免重复执行 makeindex/xindy。"""
        digest = hashlib.sha256()
        for name, content in sorted(self._index_aux_content_get().items()):
            digest.update(name.encode("utf-8"))
            digest.update(_stable_digest(content))
        return digest.hexdigest()

    def state_fingerprint(self) -> str:
        """计算"本轮可推进状态"指纹，用于判断再编译一次是否可能改变任何东西。

        只纳入真正会驱动重编译的产物：.aux/.out/.toc 的归一化内容、
        各索引系统的输入文件、.log 警告签名、.bbl 的存在性与时间戳。
        两轮指纹相同 ⇒ 再跑一次 LaTeX 也不会产生任何差异，循环应当收敛。

        与逐维 dims 判断相比，指纹是"整体是否原地踏步"的最终裁判：
        即使某个维度因为特殊宏包 churn 一直非零，只要所有产物都不再变化，
        继续编译也只是浪费时间。
        """
        digest = hashlib.sha256()
        for suffix in (".aux", ".out", ".toc"):
            digest.update(suffix.encode("utf-8"))
            digest.update(_stable_digest(self._normalize_aux_like(self._read_aux_like(suffix))))
        for name, content in sorted(self._index_aux_content_get().items()):
            digest.update(name.encode("utf-8"))
            digest.update(_stable_digest(content))
        for item in self.log_rerun_signature():
            digest.update(item.encode("utf-8"))
        bbl_path = self._bib_output_path()
        if bbl_path is not None:
            try:
                digest.update(f"bbl:{bbl_path.stat().st_size}".encode())
            except OSError:
                digest.update(b"bbl:?")
        return digest.hexdigest()


    def run_full_detection(
        self, *, cite_counter_old, toc_file_old, index_aux_content_old, aux_content_old, out_content_old
    ):
        """六维状态检测聚合接口（FR-A5 Task 2.3）。一次性返回 (dims, next_extra, bib_engine, index_run_cmds, times_bib, log_signature)。

        返回：
            dims: dict[str, int]
                每个维度取值语义：
                  -1 = 未启用（项目未使用该功能模块，跳过检测报告）
                   0 = 启用且状态稳定
                  1+ = 启用且需要额外编译的次数
                键集合：bib / idx / toc / aux / out / log
            next_extra: int
                max(启用维度) 的仍需额外 LaTeX 编译次数，供 compile_engine while 收敛判断。
                仅计算 dim>=0 的维度，未启用维度不参与 max。
            bib_engine: str|None
                BibTeX/Biber 引擎名，供 compile_engine 内 schedule 决定是否调用 compile_bib。
            times_bib: int
                bib 维度需要的 LaTeX 额外次数（供调用方复用，dim 中已编码相同值）。
            index_run_cmds: list
                index 维度的实际执行命令列表，空列表表示无需执行索引编译。
            log_signature: tuple[str, ...]
                本轮 .log 命中的重编译警告签名（供 compile_engine 跨轮差分）。
        """
        bib_engine, times_bib, _name_target = self.bib_judgment(cite_counter_old)
        index_run_cmds = self.index_judgment(index_aux_content_old)
        times_toc = 1 if self.toc_changed_judgment(toc_file_old) else 0
        aux = 1 if self.aux_changed_judgment(aux_content_old) else 0
        out = 1 if self.out_changed_judgment(out_content_old) else 0
        log_signature = self.log_rerun_signature()
        log_rerun = bool(log_signature)

        # ── 按需检测：判断各维度是否被项目实际启用 ──────────────────────
        # 未启用的维度标记 -1，后续 dims 和 next_extra 都跳过它们。
        # 判断策略：
        #   bib   → .aux 存在 且 有 bibliography 引擎标记（biblatex/bibtex/thebibliography）
        #   idx   → 任一索引系统的 trigger 扩展名文件存在
        #   toc   → .toc 文件存在
        #   aux   → LaTeX 每次编译必生成 .aux，始终启用
        #   out   → .out 文件存在（hyperref 加载后才生成）
        #   log   → .log 文件存在
        aux_path = Path(f"{self.project_name}.aux")
        aux_exists = aux_path.exists()

        main_aux = ""
        bib_enabled = False
        if aux_exists:
            main_aux = _read_file_content(aux_path)
            bib_enabled = bool(
                BIBER_PATTERN.search(main_aux) or BIBTEX_PATTERN.search(main_aux) or re.search(r"\\bibcite", main_aux)
            )

        idx_enabled = any(rule.trigger(self.project_name, main_aux) for rule in _INDEX_REGISTRY)

        toc_enabled = Path(f"{self.project_name}.toc").exists()

        out_enabled = Path(f"{self.project_name}.out").exists()

        log_enabled = any(
            Path(p).exists() for p in (f"{self.project_name}.log", Path(self.auxdir) / f"{self.project_name}.log")
        )

        dims = {
            "bib": (times_bib if bib_enabled else -1),
            "idx": ((1 if len(index_run_cmds) > 0 else 0) if idx_enabled else -1),
            "toc": (times_toc if toc_enabled else -1),
            "aux": aux,  # 始终启用
            "out": (out if out_enabled else -1),
            "log": ((1 if log_rerun else 0) if log_enabled else -1),
        }
        # next_extra 只聚合启用维度的最大值，-1 不参与计算
        next_extra = max((v for v in dims.values() if v >= 0), default=0)
        return DetectionResult(
            dims=dims,
            latex_compilation_times=next_extra,
            bib_engine=bib_engine,
            index_run_cmds=index_run_cmds,
            latex_compilation_times_bib=times_bib,
            log_signature=log_signature,
        )
