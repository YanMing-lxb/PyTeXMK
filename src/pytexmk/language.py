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
Date         : 2024-08-06 16:59:49 +0800
LastEditTime : 2024-08-09 21:40:47 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language_module.py
Description  :
 -----------------------------------------------------------------------
"""

import gettext
import locale
import os
import sys
from pathlib import Path

# Windows GetLocaleInfo (LOCALE_SENGLISHNAME) → POSIX 语言前缀的映射表
# Python locale.getlocale() 在 Windows 上返回 Windows 本地化名称（如
# 'Chinese (Simplified)_China'），而非 POSIX 的 'zh_CN'。这里做归一化以便
# 后续的 startswith('zh') 判断能正确覆盖 Windows 中文系统。
_WINDOWS_LOCALE_MAP: dict[str, str] = {
    "Chinese (Simplified)": "zh_CN",
    "Chinese (Traditional)": "zh_TW",
    "Chinese (Hong Kong)": "zh_HK",
    "Chinese (Macau)": "zh_MO",
    "English": "en",
    "Japanese": "ja",
    "Korean": "ko",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Italian": "it",
    "Portuguese": "pt",
    "Arabic": "ar",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Malay": "ms",
    "Ukrainian": "uk",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Greek": "el",
    "Czech": "cs",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Bulgarian": "bg",
}


def _normalize_windows_locale(raw: str) -> str:
    """把 Windows 本地化名称（'Chinese (Simplified)_China'）归一化为 POSIX
    语言代码（'zh_CN'），无法识别时原样返回。"""
    if not raw:
        return raw
    # 形如 "Chinese (Simplified)_China" → 取第一个空格前的名称做前缀匹配
    # 优先尝试完整匹配，匹配不到再尝试去掉国家后缀后的语言名称
    name_part = raw.split("_")[0].strip()
    if name_part in _WINDOWS_LOCALE_MAP:
        return _WINDOWS_LOCALE_MAP[name_part]
    # 去掉括号内的地区限定再匹配（如 'Chinese' → 不匹配，因为需要区分简繁）
    paren_free = name_part.split("(")[0].strip()
    if paren_free in _WINDOWS_LOCALE_MAP:
        return _WINDOWS_LOCALE_MAP[paren_free]
    return raw


def _get_locale_lang() -> str:
    """获取系统 locale 的语言前缀（如 zh_CN → zh）。

    优先读取 LANGUAGE / LC_ALL / LC_CTYPE / LANG 环境变量（POSIX 标准）；
    兜底回退到 locale.getlocale() 并对 Windows 本地化名称做归一化。
    避免使用 Python 3.15 将移除的 locale.getdefaultlocale()。
    """
    for env_var in ("LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"):
        val = os.environ.get(env_var)
        if val:
            # LANGUAGE 可能是 "zh_CN:zh:en_US:en"，取第一个
            first = val.split(":")[0]
            # 去除编码后缀（zh_CN.UTF-8 → zh_CN）
            lang = first.split(".")[0]
            # 去除 @ 修饰符（ca_ES@valencia → ca_ES）
            lang = lang.split("@")[0]
            if lang and lang != "C":
                return lang
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    raw = locale.getlocale()[0] or ""
    return _normalize_windows_locale(raw)


# --------------------------------------------------------------------------------
# 定义系统语言检查函数
# --------------------------------------------------------------------------------
def set_language(lang_file):
    """根据系统区域设置动态选择翻译；源码默认中文，zh→NullTranslations，其他按优先级查找 .mo。"""
    raw = _get_locale_lang()
    if hasattr(sys, "_MEIPASS"):
        locale_path = Path(sys._MEIPASS) / "locale"
    elif getattr(sys, "frozen", False):
        locale_path = Path(sys.executable).parent / "locale"
    else:
        locale_path = Path(__file__).resolve().parent / "locale"

    if raw.startswith("zh"):
        translation = gettext.NullTranslations()
        return translation.gettext

    # 其他语言：精确 locale → 语言回退 → 最终兜底 en，按顺序生成去重 candidates
    candidates: list[str] = []
    if raw:
        candidates.append(raw)
        sep = "_" if "_" in raw else "-" if "-" in raw else None
        if sep is not None:
            candidates.append(raw.split(sep)[0])
    candidates.append("en")
    seen: set[str] = set()
    languages: list[str] = [c for c in candidates if not (c in seen or seen.add(c))]

    fallback = gettext.NullTranslations()
    try:
        translation = gettext.translation(
            lang_file,
            localedir=str(locale_path),
            languages=languages,
            fallback=fallback,
        )
    except (FileNotFoundError, OSError, ValueError):
        translation = fallback
    return translation.gettext
