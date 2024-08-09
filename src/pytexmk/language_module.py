'''
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
LastEditTime : 2024-08-09 21:14:46 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language_module.py
Description  : 
 -----------------------------------------------------------------------
'''

import locale
import gettext
from pathlib import Path

# --------------------------------------------------------------------------------
# 定义系统语言检查函数
# --------------------------------------------------------------------------------
def set_language(lang_file):
    current_locale = locale.getdefaultlocale()
    if current_locale[0].startswith('zh'):
        lang = None
    else:
        lang = ['en']
    lang = ['en']

    locale_path = Path(__file__).resolve().parent / 'locale'
    translation = gettext.translation(lang_file, localedir=locale_path, languages=['en'])
    return translation.gettext
