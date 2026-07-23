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
 ···························································"Y88P"·····
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-08-06 16:59:49 +0800
LastEditTime : 2026-07-23 23:00:00 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language.py
Description  : Internationalization (i18n) support for PyTeXMK
 -----------------------------------------------------------------------
"""

import locale
import gettext
import os
from pathlib import Path


_LOCALE_DIR = Path(__file__).resolve().parent / "locale"

_LANG_CACHE: dict[str, gettext.NullTranslations] = {}

SUPPORTED_LANGUAGES = {
    "zh": "zh_CN",
    "zh_cn": "zh_CN",
    "zh-cn": "zh_CN",
    "en": "en",
    "en_us": "en",
    "en-us": "en",
}


def _detect_language() -> str:
    env_lang = os.environ.get("PYTEXMK_LANG", "").lower()
    if env_lang:
        for prefix, full in SUPPORTED_LANGUAGES.items():
            if env_lang.startswith(prefix):
                return full

    for env_var in ("LANGUAGE", "LANG", "LC_ALL", "LC_MESSAGES"):
        env_lang = os.environ.get(env_var, "").lower()
        if env_lang:
            for prefix, full in SUPPORTED_LANGUAGES.items():
                if env_lang.startswith(prefix):
                    return full

    lang_code = ""
    try:
        loc = locale.getlocale(locale.LC_MESSAGES)
        if loc and loc[0]:
            lang_code = loc[0].lower()
    except Exception:
        pass

    if not lang_code:
        try:
            loc = locale.getlocale()
            if loc and loc[0]:
                lang_code = loc[0].lower()
        except Exception:
            pass

    if not lang_code:
        try:
            enc = locale.getencoding()
            if enc:
                enc_lower = enc.lower()
                if "chinese" in enc_lower or "gbk" in enc_lower or "cp936" in enc_lower:
                    lang_code = "zh_cn"
        except Exception:
            pass

    if lang_code.startswith("zh"):
        return "zh_CN"

    return "en"


def _get_translation(domain: str) -> gettext.NullTranslations:
    if domain in _LANG_CACHE:
        return _LANG_CACHE[domain]

    lang = _detect_language()

    if lang == "zh_CN":
        translation = gettext.NullTranslations()
    else:
        try:
            translation = gettext.translation(
                domain,
                localedir=str(_LOCALE_DIR),
                languages=[lang],
                fallback=True,
            )
        except Exception:
            translation = gettext.NullTranslations()

    _LANG_CACHE[domain] = translation
    return translation


def set_language(domain: str):
    """
    Get the translation function for the given domain (module name).

    Usage:
        _ = set_language('module_name')
        print(_('Some text to translate'))

    The language is auto-detected from:
    1. PYTEXMK_LANG environment variable
    2. LANGUAGE environment variable
    3. LANG environment variable
    4. System locale
    Falls back to English if detection fails.

    Base language (msgid) is Simplified Chinese; English translations
    are provided via gettext .mo files.
    """
    translation = _get_translation(domain)
    return translation.gettext
