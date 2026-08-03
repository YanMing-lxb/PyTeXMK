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
import sys
from pathlib import Path


# --------------------------------------------------------------------------------
# 定义系统语言检查函数
# --------------------------------------------------------------------------------
def set_language(lang_file):
    """根据系统区域设置动态选择翻译；源码默认中文，zh→NullTranslations，其他按优先级查找 .mo。"""
    current_locale = locale.getdefaultlocale()
    if hasattr(sys, "_MEIPASS"):
        locale_path = Path(sys._MEIPASS) / "locale"
    elif getattr(sys, "frozen", False):
        locale_path = Path(sys.executable).parent / "locale"
    else:
        locale_path = Path(__file__).resolve().parent / "locale"

    raw = current_locale[0] or ""
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
    except Exception:
        translation = fallback
    return translation.gettext


def get_gettext(lang_file: str):
    """set_language 的别名：返回翻译函数。"""
    return set_language(lang_file)
