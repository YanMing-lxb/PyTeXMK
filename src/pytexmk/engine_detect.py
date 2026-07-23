# -*- coding: utf-8 -*-
"""
智能引擎自动判定模块
根据文档特征、魔法注释、CLI 参数和配置文件自动选择合适的编译引擎和工具链
"""

import re
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

from rich.console import Console

from pytexmk.toolchain import ToolchainManager
from pytexmk.additional import MainFileOperation
from pytexmk.language import set_language

_ = set_language("engine_detect")

logger = logging.getLogger(__name__)
console = Console(legacy_windows=False)

MFO = MainFileOperation()

MAX_LINES_TO_SCAN = 500

CHINESE_PACKAGES = {
    "ctex",
    "xeCJK",
    "CJKutf8",
    "luatexja",
}

UNICODE_PACKAGES = {
    "fontspec",
} | CHINESE_PACKAGES

BIBLATEX_BACKEND_PATTERN = re.compile(
    r"\\usepackage\s*(\[[^\]]*backend\s*=\s*(\w+)[^\]]*\])?\s*\{\s*biblatex\s*\}",
    re.IGNORECASE,
)

BIBLATEX_PATTERN = re.compile(
    r"\\usepackage\s*(\[[^\]]*\])?\s*\{\s*biblatex\s*\}",
    re.IGNORECASE,
)

BIBTEX_PATTERNS = [
    re.compile(r"\\bibliography\s*\{", re.IGNORECASE),
    re.compile(r"\\bibdata\s*\{", re.IGNORECASE),
]

IMAKEIDX_XINDY_PATTERN = re.compile(
    r"\\usepackage\s*\[[^\]]*xindy[^\]]*\]\s*\{\s*imakeidx\s*\}",
    re.IGNORECASE,
)

IMAKEIDX_PATTERN = re.compile(
    r"\\usepackage\s*(\[[^\]]*\])?\s*\{\s*imakeidx\s*\}",
    re.IGNORECASE,
)

MAKEIDX_PATTERN = re.compile(
    r"\\usepackage\s*\{\s*makeidx\s*\}",
    re.IGNORECASE,
)

MAKEINDEX_CMD_PATTERN = re.compile(r"\\makeindex\b", re.IGNORECASE)

GLOSSARIES_XINDY_PATTERN = re.compile(
    r"\\usepackage\s*\[[^\]]*xindy[^\]]*\]\s*\{\s*glossaries(?:-extra)?\s*\}",
    re.IGNORECASE,
)

GLOSSARIES_PATTERN = re.compile(
    r"\\usepackage\s*(\[[^\]]*\])?\s*\{\s*glossaries(?:-extra)?\s*\}",
    re.IGNORECASE,
)

NOMENCL_PATTERN = re.compile(
    r"\\usepackage\s*\{\s*nomencl\s*\}",
    re.IGNORECASE,
)

USEPACKAGE_PATTERN = re.compile(r"\\usepackage(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}", re.IGNORECASE)

DOCUMENTCLASS_PATTERN = re.compile(r"\\documentclass(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}", re.IGNORECASE)

CTEX_DOCUMENTCLASSES = {"ctexart", "ctexrep", "ctexbook", "ctexbeamer"}

MAGIC_COMMENT_KEYS = [
    "program",
    "root",
    "outdir",
    "auxdir",
    "bib",
    "index",
    "options",
]


def _is_comment_line(line: str) -> bool:
    """判断一行是否是注释行（以 % 开头，忽略前导空白）"""
    stripped = line.strip()
    return stripped.startswith("%")


def detect_document_features(tex_file_path: str | Path) -> Dict[str, Any]:
    """
    检测 .tex 文件的文档特征

    参数:
        tex_file_path: .tex 文件路径

    返回:
        包含以下字段的特征字典:
        - has_chinese: bool, 是否检测到中文/CTeX 相关宏包或文档类
        - needs_unicode: bool, 是否需要 Unicode 引擎（XeLaTeX/LuaLaTeX）
        - bib_engine: str | None, "biber" / "bibtex" / None
        - index_engine: str | None, "xindy" / "makeindex" / None
        - has_glossaries: bool, 是否使用 glossaries 宏包
        - has_nomencl: bool, 是否使用 nomencl 宏包
        - detected_packages: List[str], 检测到的宏包列表
        - detected_documentclass: str | None, 检测到的文档类
    """
    tex_path = Path(tex_file_path)
    if not tex_path.exists():
        logger.warning(_("文件不存在，无法检测特征: %(path)s") % {"path": tex_path})
        return _empty_features()

    features = _empty_features()
    detected_packages_set: set[str] = set()
    needs_unicode = False
    has_chinese = False
    bib_engine: Optional[str] = None
    index_engine: Optional[str] = None
    has_glossaries = False
    has_nomencl = False
    detected_documentclass: Optional[str] = None

    try:
        with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, start=1):
                if line_num > MAX_LINES_TO_SCAN:
                    break

                if _is_comment_line(line):
                    continue

                usepackage_match = USEPACKAGE_PATTERN.search(line)
                if usepackage_match:
                    packages_str = usepackage_match.group(1)
                    for pkg in packages_str.split(","):
                        pkg_clean = pkg.strip()
                        if pkg_clean:
                            detected_packages_set.add(pkg_clean)

                docclass_match = DOCUMENTCLASS_PATTERN.search(line)
                if docclass_match and detected_documentclass is None:
                    cls = docclass_match.group(1).strip()
                    detected_documentclass = cls
                    if cls in CTEX_DOCUMENTCLASSES:
                        has_chinese = True
                        needs_unicode = True

                if bib_engine is None:
                    bib_backend_match = BIBLATEX_BACKEND_PATTERN.search(line)
                    if bib_backend_match:
                        backend = bib_backend_match.group(2)
                        if backend and backend.lower() == "bibtex":
                            bib_engine = "bibtex"
                        else:
                            bib_engine = "biber"
                    elif BIBLATEX_PATTERN.search(line):
                        bib_engine = "biber"

                if bib_engine is None:
                    for pat in BIBTEX_PATTERNS:
                        if pat.search(line):
                            bib_engine = "bibtex"
                            break

                if IMAKEIDX_XINDY_PATTERN.search(line):
                    index_engine = "xindy"
                elif IMAKEIDX_PATTERN.search(line):
                    if index_engine is None:
                        index_engine = "makeindex"
                elif MAKEIDX_PATTERN.search(line):
                    if index_engine is None:
                        index_engine = "makeindex"
                elif MAKEINDEX_CMD_PATTERN.search(line):
                    if index_engine is None:
                        index_engine = "makeindex"

                if GLOSSARIES_XINDY_PATTERN.search(line):
                    has_glossaries = True
                    index_engine = "xindy"
                elif GLOSSARIES_PATTERN.search(line):
                    has_glossaries = True
                    if index_engine is None:
                        index_engine = "makeindex"

                if NOMENCL_PATTERN.search(line):
                    has_nomencl = True
                    if index_engine is None:
                        index_engine = "makeindex"

        for pkg in detected_packages_set:
            if pkg in CHINESE_PACKAGES:
                has_chinese = True
                needs_unicode = True
            if pkg in UNICODE_PACKAGES:
                needs_unicode = True

        features["has_chinese"] = has_chinese
        features["needs_unicode"] = needs_unicode
        features["bib_engine"] = bib_engine
        features["index_engine"] = index_engine
        features["has_glossaries"] = has_glossaries
        features["has_nomencl"] = has_nomencl
        features["detected_packages"] = sorted(detected_packages_set)
        features["detected_documentclass"] = detected_documentclass

    except Exception as e:
        logger.error(_("检测文档特征时出错 (%(path)s): %(error)s") % {"path": tex_path, "error": e})
        return _empty_features()

    return features


def _empty_features() -> Dict[str, Any]:
    """返回空的特征字典"""
    return {
        "has_chinese": False,
        "needs_unicode": False,
        "bib_engine": None,
        "index_engine": None,
        "has_glossaries": False,
        "has_nomencl": False,
        "detected_packages": [],
        "detected_documentclass": None,
    }


def parse_magic_comments(file_path: str | Path) -> Dict[str, str]:
    """
    解析指定 .tex 文件的魔法注释

    参数:
        file_path: .tex 文件路径（可以带或不带 .tex 后缀）

    返回:
        魔法注释字典 {key: value}
    """
    p = Path(file_path)
    if p.suffix != ".tex":
        p = p.with_suffix(".tex")

    if not p.exists():
        logger.warning(_("魔法注释解析: 文件不存在 %(path)s") % {"path": p})
        return {}

    result: Dict[str, str] = {}

    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                if line_num > 50:
                    break
                line_stripped = line.lstrip()
                if not line_stripped.startswith("%"):
                    continue
                for magic_key in MAGIC_COMMENT_KEYS:
                    pattern = rf"%(?:\s*)!TEX {re.escape(magic_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)"
                    m = re.search(pattern, line, re.IGNORECASE)
                    if m:
                        result[magic_key] = m.group(1).strip()
                        break
    except Exception as e:
        logger.error(_("解析魔法注释时出错 (%(path)s): %(error)s") % {"path": p, "error": e})

    return result


def _normalize_engine_name(name: str) -> str:
    """将引擎名标准化为小写形式（xelatex/pdflatex/lualatex）"""
    if not name:
        return ""
    n = name.strip().lower()
    mapping = {
        "xelatex": "xelatex",
        "xetex": "xelatex",
        "xe": "xelatex",
        "pdflatex": "pdflatex",
        "pdftex": "pdflatex",
        "pdf": "pdflatex",
        "p": "pdflatex",
        "lualatex": "lualatex",
        "luatex": "lualatex",
        "lua": "lualatex",
        "l": "lualatex",
    }
    return mapping.get(n, n)


def select_engine(
    cli_engine: Optional[str] = None,
    magic_comment_engine: Optional[str] = None,
    config_default: Optional[str] = None,
    doc_features: Optional[Dict[str, Any]] = None,
    toolchain_manager: Optional[ToolchainManager] = None,
) -> Tuple[str, str]:
    """
    根据优先级选择 TeX 引擎

    优先级: CLI > 魔法注释 > 配置默认 > 智能检测 > 默认 "xelatex"

    参数:
        cli_engine: CLI 指定的引擎
        magic_comment_engine: 魔法注释指定的引擎
        config_default: 配置文件默认引擎
        doc_features: 文档特征字典
        toolchain_manager: 工具链管理器（用于降级判断）

    返回:
        (selected_engine_lowercase, reason_string)
    """
    selected: Optional[str] = None
    reason_parts: List[str] = []

    if cli_engine:
        norm = _normalize_engine_name(cli_engine)
        if norm in ("xelatex", "pdflatex", "lualatex"):
            selected = norm
            reason_parts.append(f"CLI 指定使用 {norm}")
    if selected is None and magic_comment_engine:
        norm = _normalize_engine_name(magic_comment_engine)
        if norm in ("xelatex", "pdflatex", "lualatex"):
            selected = norm
            reason_parts.append(f"魔法注释指定使用 {norm}")
    if selected is None and config_default:
        norm = _normalize_engine_name(config_default)
        if norm in ("xelatex", "pdflatex", "lualatex"):
            selected = norm
            reason_parts.append(f"配置文件默认使用 {norm}")

    auto_preference: Optional[str] = None
    auto_reason: Optional[str] = None
    if selected is None:
        features = doc_features or {}
        needs_unicode = features.get("needs_unicode", False)
        has_chinese = features.get("has_chinese", False)
        pkgs = features.get("detected_packages", [])

        if needs_unicode:
            if "luatexja" in pkgs:
                auto_preference = "lualatex"
                auto_reason = "自动选择 LuaLaTeX（检测到 luatexja 宏包）"
            elif has_chinese or "ctex" in pkgs or "xeCJK" in pkgs:
                auto_preference = "xelatex"
                pkg_desc = "ctex" if "ctex" in pkgs else ("xeCJK" if "xeCJK" in pkgs else "中文/Unicode")
                auto_reason = f"自动选择 XeLaTeX（检测到 {pkg_desc} 宏包）"
            elif "fontspec" in pkgs:
                auto_preference = "xelatex"
                auto_reason = "自动选择 XeLaTeX（检测到 fontspec 宏包）"
            else:
                auto_preference = "xelatex"
                auto_reason = "自动选择 XeLaTeX（检测到 Unicode 需求）"
        else:
            auto_preference = "xelatex"
            auto_reason = "自动选择 XeLaTeX（默认引擎，纯英文文档）"

        selected = auto_preference
        reason_parts.append(auto_reason)

    if selected is None:
        selected = "xelatex"
        reason_parts.append("使用默认引擎 xelatex")

    final_engine = selected
    features_for_fallback = doc_features or {}
    if toolchain_manager is not None:
        try:
            toolchain_manager._auto_detect_if_needed()
            pref_available = False
            pref_key = selected
            if pref_key in toolchain_manager.engines:
                pref_available = toolchain_manager.engines[pref_key].available

            if not pref_available:
                fallback_order = ["xelatex", "lualatex", "pdflatex"]
                if features_for_fallback:
                    if features_for_fallback.get("needs_unicode") and selected == "xelatex":
                        fallback_order = ["lualatex", "pdflatex"]
                    elif selected in ("pdflatex",):
                        fallback_order = ["xelatex", "lualatex"]
                for fb in fallback_order:
                    if fb != selected and toolchain_manager.engines[fb].available:
                        logger.warning(
                            _("首选引擎 %(selected)s 不可用，降级使用 %(fallback)s")
                            % {"selected": selected, "fallback": fb}
                        )
                        reason_parts.append(f"（首选 {selected} 不可用，降级为 {fb}）")
                        final_engine = fb
                        break
        except Exception as e:
            logger.debug(_("引擎可用性检查失败（可能工具未检测）: %(error)s") % {"error": e})

    reason = "；".join(reason_parts)
    return final_engine, reason


def select_bib_tool(
    cli_bib: Optional[str] = None,
    magic_bib: Optional[str] = None,
    doc_features: Optional[Dict[str, Any]] = None,
    toolchain_manager: Optional[ToolchainManager] = None,
) -> Tuple[Optional[str], str]:
    """
    选择参考文献工具

    优先级: CLI > 魔法注释 > 智能检测 > None

    参数:
        cli_bib: CLI 指定的参考文献工具 (bibtex/biber)
        magic_bib: 魔法注释指定的参考文献工具
        doc_features: 文档特征字典
        toolchain_manager: 工具链管理器

    返回:
        (selected_bib_or_None, reason)
    """
    selected: Optional[str] = None
    reason_parts: List[str] = []

    def _norm_bib(name: str) -> Optional[str]:
        n = name.strip().lower()
        if n in ("bibtex", "biber"):
            return n
        return None

    if cli_bib:
        norm = _norm_bib(cli_bib)
        if norm:
            selected = norm
            reason_parts.append(f"CLI 指定使用 {norm}")
    if selected is None and magic_bib:
        norm = _norm_bib(magic_bib)
        if norm:
            selected = norm
            reason_parts.append(f"魔法注释指定使用 {norm}")
    if selected is None and doc_features:
        detected = doc_features.get("bib_engine")
        if detected:
            selected = detected
            reason_parts.append(f"根据文档特征自动选择 {detected}")

    if selected is None:
        reason_parts.append("未检测到参考文献需求")
        return None, "；".join(reason_parts)

    if toolchain_manager is not None:
        try:
            toolchain_manager._auto_detect_if_needed()
            if selected in toolchain_manager.bib_tools:
                if not toolchain_manager.bib_tools[selected].available:
                    other = "biber" if selected == "bibtex" else "bibtex"
                    if toolchain_manager.bib_tools[other].available:
                        logger.warning(
                            _("%(selected)s 不可用，尝试使用 %(other)s") % {"selected": selected, "other": other}
                        )
                        reason_parts.append(f"（{selected} 不可用，回退为 {other}）")
                        selected = other
        except Exception as e:
            logger.debug(_("Bib 工具可用性检查失败: %(error)s") % {"error": e})

    reason = "；".join(reason_parts)
    return selected, reason


def select_index_tool(
    cli_index: Optional[str] = None,
    magic_index: Optional[str] = None,
    doc_features: Optional[Dict[str, Any]] = None,
    toolchain_manager: Optional[ToolchainManager] = None,
) -> Tuple[str, str]:
    """
    选择索引工具

    优先级: CLI > 魔法注释 > 智能检测 > 默认 "makeindex"

    参数:
        cli_index: CLI 指定的索引工具 (makeindex/xindy)
        magic_index: 魔法注释指定的索引工具
        doc_features: 文档特征字典
        toolchain_manager: 工具链管理器

    返回:
        (selected_index, reason)
    """
    selected: Optional[str] = None
    reason_parts: List[str] = []

    def _norm_idx(name: str) -> Optional[str]:
        n = name.strip().lower()
        if n in ("makeindex", "xindy"):
            return n
        return None

    if cli_index:
        norm = _norm_idx(cli_index)
        if norm:
            selected = norm
            reason_parts.append(f"CLI 指定使用 {norm}")
    if selected is None and magic_index:
        norm = _norm_idx(magic_index)
        if norm:
            selected = norm
            reason_parts.append(f"魔法注释指定使用 {norm}")
    if selected is None and doc_features:
        detected = doc_features.get("index_engine")
        if detected:
            selected = detected
            reason_parts.append(f"根据文档特征自动选择 {detected}")
    if selected is None:
        selected = "makeindex"
        reason_parts.append("使用默认索引工具 makeindex")

    if toolchain_manager is not None:
        try:
            toolchain_manager._auto_detect_if_needed()
            if selected == "xindy":
                if not toolchain_manager.index_tools["xindy"].available:
                    if toolchain_manager.index_tools["makeindex"].available:
                        logger.warning(_("xindy 不可用，回退使用 makeindex"))
                        reason_parts.append("（xindy 不可用，回退为 makeindex）")
                        selected = "makeindex"
        except Exception as e:
            logger.debug(_("Index 工具可用性检查失败: %(error)s") % {"error": e})

    reason = "；".join(reason_parts)
    return selected, reason


def _extract_cli_engine(args_dict: Dict[str, Any]) -> Optional[str]:
    """从 CLI 参数字典中提取用户指定的引擎"""
    if args_dict.get("XeLaTeX") or args_dict.get("xelatex"):
        return "xelatex"
    if args_dict.get("PdfLaTeX") or args_dict.get("pdflatex") or args_dict.get("p"):
        return "pdflatex"
    if args_dict.get("LuaLaTeX") or args_dict.get("lualatex") or args_dict.get("l"):
        return "lualatex"
    program = args_dict.get("program")
    if program:
        return program
    return None


def _standardize_display_name(engine_lower: str) -> str:
    """将小写引擎名转换为显示名称（XeLaTeX/PdfLaTeX/LuaLaTeX）"""
    mapping = {
        "xelatex": "XeLaTeX",
        "pdflatex": "PdfLaTeX",
        "lualatex": "LuaLaTeX",
    }
    return mapping.get(engine_lower, engine_lower)


def auto_configure(
    project_name: str,
    cli_args: Dict[str, Any],
    config: Dict[str, Any],
    toolchain_manager: ToolchainManager,
    magic_comments: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    自动配置引擎和工具链

    参数:
        project_name: 主文件名（不带后缀）
        cli_args: CLI 参数字典（由 argparse 解析得到或兼容的 dict）
        config: 配置字典（来自 ConfigParser.init_config_file()）
        toolchain_manager: 已初始化并调用过 detect_all() 的 ToolchainManager 实例
        magic_comments: 已解析的魔法注释字典（若为 None 则自动解析主文件）

    返回:
        完整配置字典，包含:
        - engine: str, 引擎名（小写）
        - engine_display: str, 引擎显示名
        - bib_tool: str | None
        - index_tool: str
        - engine_reason: str
        - bib_reason: str
        - index_reason: str
        - magic_comments: dict
        - doc_features: dict
        - outdir: str
        - auxdir: str
        - extra_options: str | None
    """
    tex_file = Path(project_name).with_suffix(".tex")

    if magic_comments is None:
        magic_comments = parse_magic_comments(project_name)

    doc_features = detect_document_features(tex_file)

    cli_engine = _extract_cli_engine(cli_args)
    magic_engine = magic_comments.get("program")
    config_engine = config.get("compiled_program") if config else None

    engine, engine_reason = select_engine(
        cli_engine=cli_engine,
        magic_comment_engine=magic_engine,
        config_default=config_engine,
        doc_features=doc_features,
        toolchain_manager=toolchain_manager,
    )

    cli_bib = cli_args.get("bib") if cli_args else None
    magic_bib = magic_comments.get("bib")
    bib_tool, bib_reason = select_bib_tool(
        cli_bib=cli_bib,
        magic_bib=magic_bib,
        doc_features=doc_features,
        toolchain_manager=toolchain_manager,
    )

    cli_index = cli_args.get("index") if cli_args else None
    magic_index = magic_comments.get("index")
    index_tool, index_reason = select_index_tool(
        cli_index=cli_index,
        magic_index=magic_index,
        doc_features=doc_features,
        toolchain_manager=toolchain_manager,
    )

    outdir = (
        magic_comments.get("outdir")
        or (config.get("folder", {}).get("outdir") if config and config.get("folder") else None)
        or "./Build/"
    )
    auxdir = (
        magic_comments.get("auxdir")
        or (config.get("folder", {}).get("auxdir") if config and config.get("folder") else None)
        or "./Auxiliary/"
    )
    extra_options = magic_comments.get("options")

    engine_display = _standardize_display_name(engine)

    console.print(_("[bold green]引擎选择: %(engine)s[/bold green]") % {"engine": engine_display})
    console.print(_("[dim]  理由: %(reason)s[/dim]") % {"reason": engine_reason})

    if bib_tool:
        bib_display = "BibTeX" if bib_tool == "bibtex" else "Biber"
        console.print(_("[bold green]参考文献工具: %(tool)s[/bold green]") % {"tool": bib_display})
        console.print(_("[dim]  理由: %(reason)s[/dim]") % {"reason": bib_reason})
    else:
        console.print(_("[yellow]参考文献工具: 未检测到需求[/yellow]"))

    index_display = "MakeIndex" if index_tool == "makeindex" else "Xindy"
    console.print(_("[bold green]索引工具: %(tool)s[/bold green]") % {"tool": index_display})
    console.print(_("[dim]  理由: %(reason)s[/dim]") % {"reason": index_reason})

    if doc_features.get("has_chinese"):
        console.print(_("[cyan]检测到中文/CTeX 文档，已为您选择合适的 Unicode 引擎[/cyan]"))

    return {
        "engine": engine,
        "engine_display": engine_display,
        "bib_tool": bib_tool,
        "index_tool": index_tool,
        "engine_reason": engine_reason,
        "bib_reason": bib_reason,
        "index_reason": index_reason,
        "magic_comments": magic_comments,
        "doc_features": doc_features,
        "outdir": outdir,
        "auxdir": auxdir,
        "extra_options": extra_options,
    }
